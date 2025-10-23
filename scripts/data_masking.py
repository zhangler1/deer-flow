#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据脱敏工具库

提供多种敏感信息脱敏功能:
- 姓名脱敏
- 手机号脱敏
- 身份证号脱敏
- 邮箱脱敏
- 银行卡号脱敏
- 地址脱敏
- IP地址脱敏
- 自定义规则脱敏
"""

import re
import hashlib
from typing import Optional, Callable, Dict, Any, Match
import json


class DataMasking:
    """数据脱敏工具类"""
    
    @staticmethod
    def mask_name(name: str, keep_first: bool = True, mask_char: str = "*") -> str:
        """
        姓名脱敏
        
        Args:
            name: 原始姓名
            keep_first: 是否保留第一个字符 (默认True)
            mask_char: 脱敏字符 (默认"*")
            
        Returns:
            脱敏后的姓名
            
        Examples:
            >>> DataMasking.mask_name("张三")
            "张*"
            >>> DataMasking.mask_name("李小明")
            "李**"
            >>> DataMasking.mask_name("欧阳修", keep_first=False)
            "***"
        """
        if not name or len(name) == 0:
            return name
        
        if len(name) == 1:
            return name if keep_first else mask_char
        
        if keep_first:
            # 保留第一个字符，其余用*代替
            return name[0] + mask_char * (len(name) - 1)
        else:
            # 全部用*代替
            return mask_char * len(name)
    
    @staticmethod
    def mask_phone(phone: str, mask_char: str = "*") -> str:
        """
        手机号脱敏 (保留前3位和后4位)
        
        Args:
            phone: 原始手机号
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的手机号
            
        Examples:
            >>> DataMasking.mask_phone("13812345678")
            "138****5678"
        """
        if not phone or len(phone) < 7:
            return phone
        
        # 匹配11位手机号
        if len(phone) == 11 and phone.isdigit():
            return phone[:3] + mask_char * 4 + phone[-4:]
        
        # 其他格式的电话号码
        if len(phone) > 7:
            return phone[:3] + mask_char * (len(phone) - 7) + phone[-4:]
        
        return phone
    
    @staticmethod
    def mask_id_card(id_card: str, mask_char: str = "*") -> str:
        """
        身份证号脱敏 (保留前6位和后4位)
        
        Args:
            id_card: 原始身份证号
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的身份证号
            
        Examples:
            >>> DataMasking.mask_id_card("110101199001011234")
            "110101********1234"
        """
        if not id_card or len(id_card) < 10:
            return id_card
        
        # 18位身份证
        if len(id_card) == 18:
            return id_card[:6] + mask_char * 8 + id_card[-4:]
        
        # 15位身份证
        if len(id_card) == 15:
            return id_card[:6] + mask_char * 5 + id_card[-4:]
        
        return id_card
    
    @staticmethod
    def mask_email(email: str, mask_char: str = "*") -> str:
        """
        邮箱脱敏 (保留前2位、@符号和域名)
        
        Args:
            email: 原始邮箱
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的邮箱
            
        Examples:
            >>> DataMasking.mask_email("zhangsan@example.com")
            "zh****@example.com"
        """
        if not email or '@' not in email:
            return email
        
        parts = email.split('@')
        if len(parts) != 2:
            return email
        
        username = parts[0]
        domain = parts[1]
        
        if len(username) <= 2:
            masked_username = username
        else:
            masked_username = username[:2] + mask_char * (len(username) - 2)
        
        return f"{masked_username}@{domain}"
    
    @staticmethod
    def mask_bank_card(card_number: str, mask_char: str = "*") -> str:
        """
        银行卡号脱敏 (保留前4位和后4位)
        
        Args:
            card_number: 原始银行卡号
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的银行卡号
            
        Examples:
            >>> DataMasking.mask_bank_card("6222021234567890123")
            "6222********0123"
        """
        if not card_number or len(card_number) < 8:
            return card_number
        
        # 移除空格和连字符
        card_clean = card_number.replace(' ', '').replace('-', '')
        
        if len(card_clean) < 8:
            return card_number
        
        return card_clean[:4] + mask_char * (len(card_clean) - 8) + card_clean[-4:]
    
    @staticmethod
    def mask_address(address: str, keep_province: bool = True, mask_char: str = "*") -> str:
        """
        地址脱敏 (保留省份或全部脱敏)
        
        Args:
            address: 原始地址
            keep_province: 是否保留省份信息
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的地址
            
        Examples:
            >>> DataMasking.mask_address("北京市朝阳区XX街道XX号")
            "北京市******"
            >>> DataMasking.mask_address("广东省深圳市南山区", keep_province=False)
            "********"
        """
        if not address:
            return address
        
        if keep_province:
            # 尝试提取省份
            province_patterns = [
                r'^(.{2,3}省)',
                r'^(.{2,3}市)',
                r'^(北京|上海|天津|重庆)',
                r'^(.{2,5}自治区)',
                r'^(香港|澳门)',
            ]
            
            for pattern in province_patterns:
                match = re.match(pattern, address)
                if match:
                    province = match.group(1)
                    return province + mask_char * (len(address) - len(province))
        
        # 全部脱敏
        return mask_char * len(address)
    
    @staticmethod
    def mask_ip(ip: str, keep_first_segment: bool = True, mask_char: str = "*") -> str:
        """
        IP地址脱敏 (保留第一段或全部脱敏)
        
        Args:
            ip: 原始IP地址
            keep_first_segment: 是否保留第一段
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的IP地址
            
        Examples:
            >>> DataMasking.mask_ip("192.168.1.100")
            "192.*.*.*"
            >>> DataMasking.mask_ip("192.168.1.100", keep_first_segment=False)
            "*.*.*.*"
        """
        if not ip:
            return ip
        
        # IPv4
        if '.' in ip and ip.replace('.', '').replace('*', '').isdigit():
            parts = ip.split('.')
            if len(parts) == 4:
                if keep_first_segment:
                    return f"{parts[0]}.{mask_char}.{mask_char}.{mask_char}"
                else:
                    return f"{mask_char}.{mask_char}.{mask_char}.{mask_char}"
        
        # IPv6 简单处理
        if ':' in ip:
            parts = ip.split(':')
            if keep_first_segment and len(parts) > 0:
                return f"{parts[0]}:{mask_char * 4}:{mask_char * 4}:..."
            else:
                return f"{mask_char * 4}:{mask_char * 4}:..."
        
        return ip
    
    @staticmethod
    def mask_custom(text: str, regex_pattern: str, replace_func: Callable[[Match[str]], str]) -> str:
        """
        自定义规则脱敏
        
        Args:
            text: 原始文本
            regex_pattern: 正则表达式模式
            replace_func: 替换函数，接收Match对象，返回脱敏后的字符串
            
        Returns:
            脱敏后的文本
            
        Examples:
            >>> DataMasking.mask_custom(
            ...     "订单号: ORD123456789",
            ...     r"ORD\d+",
            ...     lambda m: "ORD" + "*" * (len(m.group()) - 3)
            ... )
            "订单号: ORD*********"
        """
        return re.sub(regex_pattern, replace_func, text)
    
    @staticmethod
    def mask_dict(data: Dict[str, Any], rules: Dict[str, str], mask_char: str = "*") -> Dict[str, Any]:
        """
        字典数据脱敏
        
        Args:
            data: 原始字典数据
            rules: 脱敏规则字典，key为字段名，value为脱敏类型
                  支持的类型: name, phone, id_card, email, bank_card, address, ip, hash
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的字典数据
            
        Examples:
            >>> data = {
            ...     "name": "张三",
            ...     "phone": "13812345678",
            ...     "email": "zhangsan@example.com"
            ... }
            >>> rules = {"name": "name", "phone": "phone", "email": "email"}
            >>> DataMasking.mask_dict(data, rules)
            {"name": "张*", "phone": "138****5678", "email": "zh****@example.com"}
        """
        result = data.copy()
        
        for field, mask_type in rules.items():
            if field not in result:
                continue
            
            value = result[field]
            if not isinstance(value, str):
                continue
            
            if mask_type == "name":
                result[field] = DataMasking.mask_name(value, mask_char=mask_char)
            elif mask_type == "phone":
                result[field] = DataMasking.mask_phone(value, mask_char=mask_char)
            elif mask_type == "id_card":
                result[field] = DataMasking.mask_id_card(value, mask_char=mask_char)
            elif mask_type == "email":
                result[field] = DataMasking.mask_email(value, mask_char=mask_char)
            elif mask_type == "bank_card":
                result[field] = DataMasking.mask_bank_card(value, mask_char=mask_char)
            elif mask_type == "address":
                result[field] = DataMasking.mask_address(value, mask_char=mask_char)
            elif mask_type == "ip":
                result[field] = DataMasking.mask_ip(value, mask_char=mask_char)
            elif mask_type == "hash":
                # 使用哈希代替原始值
                result[field] = hashlib.md5(value.encode()).hexdigest()[:16]
        
        return result
    
    @staticmethod
    def mask_json(json_str: str, rules: Dict[str, str], mask_char: str = "*") -> str:
        """
        JSON字符串脱敏
        
        Args:
            json_str: 原始JSON字符串
            rules: 脱敏规则字典
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的JSON字符串
        """
        try:
            data = json.loads(json_str)
            masked_data = DataMasking.mask_dict(data, rules, mask_char)
            return json.dumps(masked_data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return json_str
    
    @staticmethod
    def mask_text_auto(text: str, mask_char: str = "*") -> str:
        """
        自动检测并脱敏文本中的敏感信息
        
        Args:
            text: 原始文本
            mask_char: 脱敏字符
            
        Returns:
            脱敏后的文本
        """
        result = text
        
        # 手机号脱敏 (11位数字)
        result = re.sub(
            r'1[3-9]\d{9}',
            lambda m: DataMasking.mask_phone(m.group(), mask_char),
            result
        )
        
        # 身份证号脱敏 (18位或15位)
        result = re.sub(
            r'\d{15}|\d{17}[\dXx]',
            lambda m: DataMasking.mask_id_card(m.group(), mask_char),
            result
        )
        
        # 邮箱脱敏
        result = re.sub(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            lambda m: DataMasking.mask_email(m.group(), mask_char),
            result
        )
        
        # IP地址脱敏
        result = re.sub(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            lambda m: DataMasking.mask_ip(m.group(), mask_char=mask_char),
            result
        )
        
        return result


# 便捷函数别名
mask_name = DataMasking.mask_name
mask_phone = DataMasking.mask_phone
mask_id_card = DataMasking.mask_id_card
mask_email = DataMasking.mask_email
mask_bank_card = DataMasking.mask_bank_card
mask_address = DataMasking.mask_address
mask_ip = DataMasking.mask_ip
mask_custom = DataMasking.mask_custom
mask_dict = DataMasking.mask_dict
mask_json = DataMasking.mask_json
mask_text_auto = DataMasking.mask_text_auto


if __name__ == "__main__":
    # 测试示例
    print("=" * 60)
    print("数据脱敏工具测试")
    print("=" * 60)
    
    # 姓名脱敏
    print("\n\033[32m1. 姓名脱敏:\033[0m")
    print(f"  张三 → \033[35m{mask_name('张三')}\033[0m")
    print(f"  李小明 → \033[35m{mask_name('李小明')}\033[0m")
    print(f"  欧阳修 → \033[35m{mask_name('欧阳修')}\033[0m")
    
    # 手机号脱敏
    print("\n\033[32m2. 手机号脱敏:\033[0m")
    print(f"  13812345678 → \033[35m{mask_phone('13812345678')}\033[0m")
    print(f"  18900001234 → \033[35m{mask_phone('18900001234')}\033[0m")
    
    # 身份证号脱敏
    print("\n\033[32m3. 身份证号脱敏:\033[0m")
    print(f"  110101199001011234 → \033[35m{mask_id_card('110101199001011234')}\033[0m")
    
    # 邮箱脱敏
    print("\n\033[32m4. 邮箱脱敏:\033[0m")
    print(f"  zhangsan@example.com → \033[35m{mask_email('zhangsan@example.com')}\033[0m")
    
    # 银行卡号脱敏
    print("\n\033[32m5. 银行卡号脱敏:\033[0m")
    print(f"  6222021234567890123 → \033[35m{mask_bank_card('6222021234567890123')}\033[0m")
    
    # 地址脱敏
    print("\n\033[32m6. 地址脱敏:\033[0m")
    print(f"  北京市朝阳区XX街道XX号 → \033[35m{mask_address('北京市朝阳区XX街道XX号')}\033[0m")
    
    # IP地址脱敏
    print("\n\033[32m7. IP地址脱敏:\033[0m")
    print(f"  192.168.1.100 → \033[35m{mask_ip('192.168.1.100')}\033[0m")
    
    # 字典脱敏
    print("\n\033[32m8. 字典数据脱敏:\033[0m")
    customer_data = {
        "name": "张三",
        "phone": "13812345678",
        "email": "zhangsan@example.com",
        "id_card": "110101199001011234",
        "address": "北京市朝阳区XX街道XX号"
    }
    
    rules = {
        "name": "name",
        "phone": "phone",
        "email": "email",
        "id_card": "id_card",
        "address": "address"
    }
    
    masked_data = mask_dict(customer_data, rules)
    print(f"  原始数据: {customer_data}")
    print(f"  脱敏数据: \033[35m{masked_data}\033[0m")
    
    # 自动文本脱敏
    print("\n\033[32m9. 自动文本脱敏:\033[0m")
    text = "客户张三，电话13812345678，邮箱zhangsan@example.com，IP地址192.168.1.100"
    print(f"  原始: {text}")
    print(f"  脱敏: \033[35m{mask_text_auto(text)}\033[0m")
    
    print("\n" + "=" * 60)
