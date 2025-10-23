#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据脱敏脚本

用法:
    1. 脱敏单个文件:
       python mask_data.py --input data.json --output masked_data.json
    
    2. 脱敏多个文件:
       python mask_data.py --input-dir ./data --output-dir ./masked_data
    
    3. 使用自定义规则:
       python mask_data.py --input data.json --output masked.json --rules rules.json
    
    4. 脱敏文本文件:
       python mask_data.py --input log.txt --output masked_log.txt --text-mode
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging

# 添加脚本目录到路径
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from data_masking import DataMasking

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='\033[32m%(asctime)s\033[0m - \033[35m%(levelname)s\033[0m - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# 默认脱敏规则
DEFAULT_RULES = {
    "name": "name",
    "姓名": "name",
    "customer_name": "name",
    "客户姓名": "name",
    "user_name": "name",
    "用户名": "name",
    
    "phone": "phone",
    "mobile": "phone",
    "telephone": "phone",
    "电话": "phone",
    "手机": "phone",
    "联系方式": "phone",
    "contact": "phone",
    
    "email": "email",
    "邮箱": "email",
    "mail": "email",
    
    "id_card": "id_card",
    "identity": "id_card",
    "身份证": "id_card",
    "证件号": "id_card",
    
    "bank_card": "bank_card",
    "card_number": "bank_card",
    "银行卡": "bank_card",
    "卡号": "bank_card",
    
    "address": "address",
    "addr": "address",
    "地址": "address",
    "住址": "address",
    "详细地址": "address",
    
    "ip": "ip",
    "ip_address": "ip",
    "IP地址": "ip",
}


def load_custom_rules(rules_file: str) -> Dict[str, str]:
    """加载自定义脱敏规则"""
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载自定义规则失败: {e}")
        return DEFAULT_RULES


def mask_json_file(input_file: str, output_file: str, rules: Dict[str, str]):
    """脱敏JSON文件"""
    try:
        logger.info(f"开始处理JSON文件: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理数据
        if isinstance(data, list):
            # 列表数据 (如用户列表)
            masked_data = [DataMasking.mask_dict(item, rules) if isinstance(item, dict) else item for item in data]
            logger.info(f"处理了 {len(masked_data)} 条记录")
        elif isinstance(data, dict):
            # 单个字典
            masked_data = DataMasking.mask_dict(data, rules)
            logger.info("处理了 1 条记录")
        else:
            masked_data = data
            logger.warning("数据格式不是字典或列表，未进行脱敏")
        
        # 保存结果
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(masked_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\033[32m✓\033[0m 脱敏完成，已保存到: \033[35m{output_file}\033[0m")
        return True
        
    except Exception as e:
        logger.error(f"处理JSON文件失败: {e}")
        return False


def mask_text_file(input_file: str, output_file: str):
    """脱敏文本文件 (自动检测敏感信息)"""
    try:
        logger.info(f"开始处理文本文件: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 自动脱敏
        masked_content = DataMasking.mask_text_auto(content)
        
        # 保存结果
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(masked_content)
        
        logger.info(f"\033[32m✓\033[0m 脱敏完成，已保存到: \033[35m{output_file}\033[0m")
        return True
        
    except Exception as e:
        logger.error(f"处理文本文件失败: {e}")
        return False


def mask_csv_file(input_file: str, output_file: str, rules: Dict[str, str]):
    """脱敏CSV文件"""
    try:
        import csv
        
        logger.info(f"开始处理CSV文件: {input_file}")
        
        rows = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            for row in reader:
                masked_row = DataMasking.mask_dict(row, rules)
                rows.append(masked_row)
        
        # 保存结果
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            if headers:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        
        logger.info(f"\033[32m✓\033[0m 脱敏完成，处理了 {len(rows)} 行，已保存到: \033[35m{output_file}\033[0m")
        return True
        
    except Exception as e:
        logger.error(f"处理CSV文件失败: {e}")
        return False


def process_single_file(input_file: str, output_file: str, rules: Dict[str, str], text_mode: bool = False):
    """处理单个文件"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_file}")
        return False
    
    # 根据文件类型选择处理方式
    ext = input_path.suffix.lower()
    
    if text_mode or ext in ['.txt', '.log', '.md']:
        return mask_text_file(input_file, output_file)
    elif ext == '.json':
        return mask_json_file(input_file, output_file, rules)
    elif ext == '.csv':
        return mask_csv_file(input_file, output_file, rules)
    else:
        logger.warning(f"不支持的文件类型: {ext}，将尝试作为文本文件处理")
        return mask_text_file(input_file, output_file)


def process_directory(input_dir: str, output_dir: str, rules: Dict[str, str], text_mode: bool = False):
    """处理目录中的所有文件"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return False
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 遍历所有文件
    success_count = 0
    fail_count = 0
    
    for file_path in input_path.rglob('*'):
        if file_path.is_file():
            # 计算相对路径
            rel_path = file_path.relative_to(input_path)
            output_file = output_path / rel_path
            
            # 确保输出目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理文件
            if process_single_file(str(file_path), str(output_file), rules, text_mode):
                success_count += 1
            else:
                fail_count += 1
    
    logger.info(f"\n批量处理完成: \033[32m成功 {success_count} 个\033[0m, \033[35m失败 {fail_count} 个\033[0m")
    return True


def generate_sample_data():
    """生成示例数据文件"""
    sample_data = [
        {
            "id": 1,
            "name": "张三",
            "phone": "13812345678",
            "email": "zhangsan@example.com",
            "id_card": "110101199001011234",
            "address": "北京市朝阳区XX街道XX号",
            "bank_card": "6222021234567890123"
        },
        {
            "id": 2,
            "name": "李四",
            "phone": "18900001234",
            "email": "lisi@example.com",
            "id_card": "310101198505055678",
            "address": "上海市浦东新区XX路XX号",
            "bank_card": "6228481234567890456"
        },
        {
            "id": 3,
            "name": "王小明",
            "phone": "13700009999",
            "email": "wangxiaoming@test.com",
            "id_card": "440101199203031111",
            "address": "广东省深圳市南山区XX大厦",
            "bank_card": "6225881234567890789"
        }
    ]
    
    sample_file = "sample_customer_data.json"
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\033[32m✓\033[0m 已生成示例数据文件: \033[35m{sample_file}\033[0m")
    return sample_file


def main():
    parser = argparse.ArgumentParser(
        description='数据脱敏工具 - 自动脱敏姓名、手机号、身份证、邮箱等敏感信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 脱敏JSON文件
  python mask_data.py -i data.json -o masked_data.json
  
  # 脱敏文本文件
  python mask_data.py -i log.txt -o masked_log.txt --text-mode
  
  # 批量脱敏目录
  python mask_data.py --input-dir ./data --output-dir ./masked_data
  
  # 使用自定义规则
  python mask_data.py -i data.json -o masked.json --rules custom_rules.json
  
  # 生成示例数据
  python mask_data.py --generate-sample
        """
    )
    
    parser.add_argument('-i', '--input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--input-dir', help='输入目录路径 (批量处理)')
    parser.add_argument('--output-dir', help='输出目录路径 (批量处理)')
    parser.add_argument('--rules', help='自定义脱敏规则文件 (JSON格式)')
    parser.add_argument('--text-mode', action='store_true', help='文本模式 (自动检测敏感信息)')
    parser.add_argument('--generate-sample', action='store_true', help='生成示例数据文件')
    
    args = parser.parse_args()
    
    # 生成示例数据
    if args.generate_sample:
        sample_file = generate_sample_data()
        print(f"\n现在可以运行: python mask_data.py -i {sample_file} -o masked_{sample_file}")
        return
    
    # 加载脱敏规则
    rules = DEFAULT_RULES
    if args.rules:
        rules = load_custom_rules(args.rules)
        logger.info(f"使用自定义规则: {args.rules}")
    else:
        logger.info("使用默认脱敏规则")
    
    # 处理单个文件
    if args.input and args.output:
        success = process_single_file(args.input, args.output, rules, args.text_mode)
        sys.exit(0 if success else 1)
    
    # 批量处理目录
    elif args.input_dir and args.output_dir:
        success = process_directory(args.input_dir, args.output_dir, rules, args.text_mode)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        print("\n\033[33m提示:\033[0m 使用 --generate-sample 生成示例数据进行测试")
        sys.exit(1)


if __name__ == "__main__":
    main()
