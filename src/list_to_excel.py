"""将 list.txt（JSON 数组）转换为 Excel 文件的脚本。

用法:
    python list_to_excel.py [输入文件] [输出文件]

默认输入: ./list.txt
默认输出: ./list.xlsx
"""

import json
import sys
from pathlib import Path

import pandas as pd


def convert(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 读取 JSON 数据
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("输入文件内容必须是 JSON 数组")

    # 转换为 DataFrame
    df = pd.DataFrame(data)

    # 将布尔值转换为中文，方便阅读（可按需保留原值）
    bool_cols = df.select_dtypes(include=["bool"]).columns
    for col in bool_cols:
        df[col] = df[col].map({True: "是", False: "否"})

    # 中文列名映射
    column_map = {
        "orgName": "机构名称",
        "parentOrgName": "上级机构",
        "orgSeq": "机构序列",
        "orgOrder": "机构排序",
        "isCascading": "是否级联",
        "userId": "用户ID",
        "userName": "用户姓名",
        "loginName": "登录名",
        "userType": "用户类型",
        "ehrPosition": "EHR职位",
        "includeNonStaff": "包含非员工",
        "staffType": "员工类型",
        "isGranted": "已授权",
        "fromOrg": "来自机构",
        "isDenied": "已拒绝",
        "fromGroup": "来自组",
    }
    df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

    # 写入 Excel
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="人员列表")
        ws = writer.sheets["人员列表"]

        # 自适应列宽
        for col_cells in ws.columns:
            max_len = 0
            col_letter = col_cells[0].column_letter
            for cell in col_cells:
                value = "" if cell.value is None else str(cell.value)
                # 中文字符按 2 个宽度计算
                width = sum(2 if ord(ch) > 127 else 1 for ch in value)
                max_len = max(max_len, width)
            ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

    print(f"转换完成: {output_path}  (共 {len(df)} 条记录)")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "list.txt"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else script_dir / "list.xlsx"
    convert(input_path, output_path)


if __name__ == "__main__":
    main()
