# 数据脱敏工具使用指南

## 📋 功能概述

提供完整的数据脱敏解决方案,支持:

- ✅ **姓名脱敏**: 张三 → 张*
- ✅ **手机号脱敏**: 13812345678 → 138****5678
- ✅ **身份证脱敏**: 110101199001011234 → 110101********1234
- ✅ **邮箱脱敏**: zhangsan@example.com → zh****@example.com
- ✅ **银行卡脱敏**: 6222021234567890123 → 6222********0123
- ✅ **地址脱敏**: 北京市朝阳区XX街道 → 北京市******
- ✅ **IP地址脱敏**: 192.168.1.100 → 192.*.*.*
- ✅ **自动检测脱敏**: 自动识别文本中的敏感信息
- ✅ **批量处理**: 支持目录批量脱敏
- ✅ **多格式支持**: JSON、CSV、TXT、LOG等

## 🚀 快速开始

### 1. 生成示例数据

```bash
cd /home/llm/zhangle/deer-flow/scripts
python mask_data.py --generate-sample
```

这将生成 `sample_customer_data.json` 文件:

```json
[
  {
    "id": 1,
    "name": "张三",
    "phone": "13812345678",
    "email": "zhangsan@example.com",
    "id_card": "110101199001011234",
    "address": "北京市朝阳区XX街道XX号",
    "bank_card": "6222021234567890123"
  }
]
```

### 2. 脱敏示例数据

```bash
python mask_data.py -i sample_customer_data.json -o masked_customer_data.json
```

输出结果:

```json
[
  {
    "id": 1,
    "name": "张*",
    "phone": "138****5678",
    "email": "zh****@example.com",
    "id_card": "110101********1234",
    "address": "北京市******",
    "bank_card": "6222********0123"
  }
]
```

## 📚 详细用法

### 基础命令

```bash
# 脱敏JSON文件
python mask_data.py -i data.json -o masked_data.json

# 脱敏文本文件 (自动检测敏感信息)
python mask_data.py -i log.txt -o masked_log.txt --text-mode

# 脱敏CSV文件
python mask_data.py -i customers.csv -o masked_customers.csv

# 批量脱敏整个目录
python mask_data.py --input-dir ./data --output-dir ./masked_data
```

### 使用自定义规则

创建自定义规则文件 `custom_rules.json`:

```json
{
  "customer_name": "name",
  "contact_phone": "phone",
  "user_email": "email",
  "identity_card": "id_card",
  "home_address": "address",
  "account_number": "bank_card",
  "server_ip": "ip"
}
```

使用自定义规则:

```bash
python mask_data.py -i data.json -o masked.json --rules custom_rules.json
```

## 🔧 API使用

### 在Python代码中使用

```python
from data_masking import DataMasking, mask_name, mask_phone, mask_dict

# 1. 脱敏单个字段
name = mask_name("张三")  # "张*"
phone = mask_phone("13812345678")  # "138****5678"

# 2. 脱敏字典数据
customer = {
    "name": "张三",
    "phone": "13812345678",
    "email": "zhangsan@example.com"
}

rules = {
    "name": "name",
    "phone": "phone",
    "email": "email"
}

masked_customer = mask_dict(customer, rules)
# {"name": "张*", "phone": "138****5678", "email": "zh****@example.com"}

# 3. 自动检测脱敏
from data_masking import mask_text_auto

text = "客户张三，电话13812345678，邮箱zhangsan@example.com"
masked_text = mask_text_auto(text)
# "客户张三，电话138****5678，邮箱zh****@example.com"
```

### 所有可用函数

```python
from data_masking import DataMasking

# 姓名脱敏
DataMasking.mask_name("张三")  # "张*"
DataMasking.mask_name("李小明", keep_first=False)  # "***"

# 手机号脱敏
DataMasking.mask_phone("13812345678")  # "138****5678"

# 身份证脱敏
DataMasking.mask_id_card("110101199001011234")  # "110101********1234"

# 邮箱脱敏
DataMasking.mask_email("zhangsan@example.com")  # "zh****@example.com"

# 银行卡脱敏
DataMasking.mask_bank_card("6222021234567890123")  # "6222********0123"

# 地址脱敏
DataMasking.mask_address("北京市朝阳区XX街道")  # "北京市******"
DataMasking.mask_address("北京市朝阳区XX街道", keep_province=False)  # "********"

# IP地址脱敏
DataMasking.mask_ip("192.168.1.100")  # "192.*.*.*"
DataMasking.mask_ip("192.168.1.100", keep_first_segment=False)  # "*.*.*.*"

# 自定义规则脱敏
DataMasking.mask_custom(
    "订单号: ORD123456789",
    r"ORD\d+",
    lambda m: "ORD" + "*" * (len(m.group()) - 3)
)  # "订单号: ORD*********"
```

## 🎨 高级用法

### 1. 批量脱敏用户列表

```python
from data_masking import mask_dict

users = [
    {"name": "张三", "phone": "13812345678"},
    {"name": "李四", "phone": "18900001234"},
]

rules = {"name": "name", "phone": "phone"}
masked_users = [mask_dict(user, rules) for user in users]
```

### 2. 自定义脱敏字符

```python
from data_masking import DataMasking

# 使用 # 代替默认的 *
masked = DataMasking.mask_phone("13812345678", mask_char="#")
# "138####5678"
```

### 3. 处理嵌套JSON

```python
from data_masking import DataMasking
import json

# 处理嵌套结构
data = {
    "customer": {
        "name": "张三",
        "contact": {
            "phone": "13812345678",
            "email": "zhangsan@example.com"
        }
    }
}

# 展平并脱敏
def mask_nested(obj, rules):
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                result[key] = mask_nested(value, rules)
            elif key in rules and isinstance(value, str):
                mask_type = rules[key]
                if mask_type == "name":
                    result[key] = DataMasking.mask_name(value)
                elif mask_type == "phone":
                    result[key] = DataMasking.mask_phone(value)
                elif mask_type == "email":
                    result[key] = DataMasking.mask_email(value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result
    elif isinstance(obj, list):
        return [mask_nested(item, rules) for item in obj]
    return obj

rules = {"name": "name", "phone": "phone", "email": "email"}
masked_data = mask_nested(data, rules)
```

### 4. 脱敏日志文件

```python
from data_masking import mask_text_auto

# 读取日志
with open('app.log', 'r') as f:
    log_content = f.read()

# 自动脱敏敏感信息
masked_log = mask_text_auto(log_content)

# 保存脱敏后的日志
with open('masked_app.log', 'w') as f:
    f.write(masked_log)
```

## 📊 支持的脱敏类型

| 类型 | 规则键名 | 说明 | 示例 |
|------|---------|------|------|
| 姓名 | `name` | 保留首字符 | 张三 → 张* |
| 手机号 | `phone` | 保留前3后4 | 13812345678 → 138****5678 |
| 身份证 | `id_card` | 保留前6后4 | 110101199001011234 → 110101********1234 |
| 邮箱 | `email` | 保留前2和域名 | zhangsan@example.com → zh****@example.com |
| 银行卡 | `bank_card` | 保留前4后4 | 6222021234567890123 → 6222********0123 |
| 地址 | `address` | 保留省份 | 北京市朝阳区XX街道 → 北京市****** |
| IP地址 | `ip` | 保留第一段 | 192.168.1.100 → 192.*.*.* |
| 哈希 | `hash` | MD5哈希 | zhangsan → 7c6a180b36896a0a |

## 🔍 默认规则映射

脚本内置以下字段名自动识别:

```python
{
    "name": "name",
    "姓名": "name",
    "customer_name": "name",
    "客户姓名": "name",
    
    "phone": "phone",
    "mobile": "phone",
    "电话": "phone",
    "手机": "phone",
    
    "email": "email",
    "邮箱": "email",
    
    "id_card": "id_card",
    "身份证": "id_card",
    
    "bank_card": "bank_card",
    "银行卡": "bank_card",
    
    "address": "address",
    "地址": "address",
    
    "ip": "ip",
    "ip_address": "ip",
}
```

## ⚠️ 注意事项

1. **不可逆性**: 脱敏后的数据无法还原,请保留原始数据备份
2. **编码**: 所有文件默认使用UTF-8编码
3. **性能**: 大文件处理可能需要较长时间
4. **备份**: 处理重要数据前请先备份

## 🧪 测试

运行测试示例:

```bash
# 测试所有脱敏函数
python data_masking.py
```

输出示例:

```
============================================================
数据脱敏工具测试
============================================================

1. 姓名脱敏:
  张三 → 张*
  李小明 → 李**
  欧阳修 → 欧**

2. 手机号脱敏:
  13812345678 → 138****5678
  18900001234 → 189****1234

3. 身份证号脱敏:
  110101199001011234 → 110101********1234

...
```

## 📝 常见场景

### 场景1: 脱敏客户数据库导出

```bash
# 导出客户数据
mysqldump customers > customers.json

# 脱敏处理
python mask_data.py -i customers.json -o masked_customers.json

# 共享给第三方
scp masked_customers.json user@server:/path/
```

### 场景2: 脱敏应用日志

```bash
# 脱敏所有日志文件
python mask_data.py --input-dir ./logs --output-dir ./masked_logs --text-mode
```

### 场景3: 脱敏测试数据

```python
from data_masking import mask_dict

# 从生产环境复制数据
prod_data = fetch_from_production()

# 脱敏后用于测试环境
rules = {"name": "name", "phone": "phone", "email": "email"}
test_data = [mask_dict(item, rules) for item in prod_data]

# 导入测试数据库
import_to_test_env(test_data)
```

## 🤝 贡献

欢迎提交Issue和Pull Request!

## 📄 许可

MIT License

---

**最后更新**: 2025-10-22
