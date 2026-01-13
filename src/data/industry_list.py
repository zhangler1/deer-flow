# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
行业列表配置

存储所有可用的行业信息，用于行业研报搜索。
每个行业包含 IndustryId 和 IndustryName 两个字段。
"""

# 行业列表配置
# 可以根据实际情况添加或修改行业信息
INDUSTRY_LIST = [
  {
    "IndustryId": "2206",
    "IndustryName": "橡胶"
  },
  {
    "IndustryId": "2205",
    "IndustryName": "塑料"
  },
  {
    "IndustryId": "2204",
    "IndustryName": "化学纤维"
  },
  {
    "IndustryId": "2203",
    "IndustryName": "化学制品"
  },
  {
    "IndustryId": "2202",
    "IndustryName": "化学原料"
  },
  {
    "IndustryId": "2201",
    "IndustryName": "石油化工"
  },
  {
    "IndustryId": "2301",
    "IndustryName": "钢铁"
  },
  {
    "IndustryId": "4502",
    "IndustryName": "贸易"
  },
  {
    "IndustryId": "4503",
    "IndustryName": "一般零售"
  },
  {
    "IndustryId": "4504",
    "IndustryName": "专业零售"
  },
  {
    "IndustryId": "4505",
    "IndustryName": "商业物业经营"
  },
  {
    "IndustryId": "2405",
    "IndustryName": "稀有金属"
  },
  {
    "IndustryId": "2404",
    "IndustryName": "黄金"
  },
  {
    "IndustryId": "2403",
    "IndustryName": "工业金属"
  },
  {
    "IndustryId": "2402",
    "IndustryName": "金属非金属新材料"
  },
  {
    "IndustryId": "4601",
    "IndustryName": "景点"
  },
  {
    "IndustryId": "4602",
    "IndustryName": "酒店"
  },
  {
    "IndustryId": "4603",
    "IndustryName": "旅游综合"
  },
  {
    "IndustryId": "4604",
    "IndustryName": "餐饮"
  },
  {
    "IndustryId": "4605",
    "IndustryName": "其他休闲服务"
  },
  {
    "IndustryId": "4801",
    "IndustryName": "银行"
  },
  {
    "IndustryId": "2702",
    "IndustryName": "元件"
  },
  {
    "IndustryId": "2701",
    "IndustryName": "半导体"
  },
  {
    "IndustryId": "2705",
    "IndustryName": "电子制造"
  },
  {
    "IndustryId": "2704",
    "IndustryName": "其他电子"
  },
  {
    "IndustryId": "2703",
    "IndustryName": "光学光电子"
  },
  {
    "IndustryId": "4903",
    "IndustryName": "多元金融"
  },
  {
    "IndustryId": "4901",
    "IndustryName": "证券"
  },
  {
    "IndustryId": "4902",
    "IndustryName": "保险"
  },
  {
    "IndustryId": "2801",
    "IndustryName": "汽车整车"
  },
  {
    "IndustryId": "2804",
    "IndustryName": "其他交运设备"
  },
  {
    "IndustryId": "2803",
    "IndustryName": "汽车服务"
  },
  {
    "IndustryId": "2802",
    "IndustryName": "汽车零部件"
  },
  {
    "IndustryId": "7101",
    "IndustryName": "计算机设备"
  },
  {
    "IndustryId": "7102",
    "IndustryName": "计算机应用"
  },
  {
    "IndustryId": "7202",
    "IndustryName": "营销传播"
  },
  {
    "IndustryId": "7201",
    "IndustryName": "文化传媒"
  },
  {
    "IndustryId": "7203",
    "IndustryName": "互联网传媒"
  },
  {
    "IndustryId": "5101",
    "IndustryName": "综合"
  },
  {
    "IndustryId": "7301",
    "IndustryName": "通信运营"
  },
  {
    "IndustryId": "7302",
    "IndustryName": "通信设备"
  },
  {
    "IndustryId": "1107",
    "IndustryName": "畜禽养殖"
  },
  {
    "IndustryId": "1106",
    "IndustryName": "农业综合"
  },
  {
    "IndustryId": "1105",
    "IndustryName": "农产品加工"
  },
  {
    "IndustryId": "1104",
    "IndustryName": "饲料"
  },
  {
    "IndustryId": "1103",
    "IndustryName": "林业"
  },
  {
    "IndustryId": "1102",
    "IndustryName": "渔业"
  },
  {
    "IndustryId": "1101",
    "IndustryName": "种植业"
  },
  {
    "IndustryId": "1108",
    "IndustryName": "动物保健"
  },
  {
    "IndustryId": "3302",
    "IndustryName": "视听器材"
  },
  {
    "IndustryId": "3301",
    "IndustryName": "白色家电"
  },
  {
    "IndustryId": "3404",
    "IndustryName": "食品加工"
  },
  {
    "IndustryId": "3403",
    "IndustryName": "饮料制造"
  },
  {
    "IndustryId": "3502",
    "IndustryName": "服装家纺"
  },
  {
    "IndustryId": "3501",
    "IndustryName": "纺织制造"
  },
  {
    "IndustryId": "3604",
    "IndustryName": "其他轻工制造"
  },
  {
    "IndustryId": "3603",
    "IndustryName": "家用轻工"
  },
  {
    "IndustryId": "3602",
    "IndustryName": "包装印刷"
  },
  {
    "IndustryId": "3601",
    "IndustryName": "造纸"
  },
  {
    "IndustryId": "3704",
    "IndustryName": "医药商业"
  },
  {
    "IndustryId": "3705",
    "IndustryName": "医疗器械"
  },
  {
    "IndustryId": "3706",
    "IndustryName": "医疗服务"
  },
  {
    "IndustryId": "3701",
    "IndustryName": "化学制药"
  },
  {
    "IndustryId": "3702",
    "IndustryName": "中药"
  },
  {
    "IndustryId": "3703",
    "IndustryName": "生物制品"
  },
  {
    "IndustryId": "6102",
    "IndustryName": "玻璃制造"
  },
  {
    "IndustryId": "6101",
    "IndustryName": "水泥制造"
  },
  {
    "IndustryId": "6103",
    "IndustryName": "其他建材"
  },
  {
    "IndustryId": "6201",
    "IndustryName": "房屋建设"
  },
  {
    "IndustryId": "6203",
    "IndustryName": "基础建设"
  },
  {
    "IndustryId": "6202",
    "IndustryName": "装修装饰"
  },
  {
    "IndustryId": "6205",
    "IndustryName": "园林工程"
  },
  {
    "IndustryId": "6204",
    "IndustryName": "专业工程"
  },
  {
    "IndustryId": "4101",
    "IndustryName": "电力"
  },
  {
    "IndustryId": "4102",
    "IndustryName": "水务"
  },
  {
    "IndustryId": "4103",
    "IndustryName": "燃气"
  },
  {
    "IndustryId": "4104",
    "IndustryName": "环保工程及服务"
  },
  {
    "IndustryId": "6302",
    "IndustryName": "电气自动化设备"
  },
  {
    "IndustryId": "6301",
    "IndustryName": "电机"
  },
  {
    "IndustryId": "6304",
    "IndustryName": "高低压设备"
  },
  {
    "IndustryId": "6303",
    "IndustryName": "电源设备"
  },
  {
    "IndustryId": "4201",
    "IndustryName": "港口"
  },
  {
    "IndustryId": "4202",
    "IndustryName": "高速公路"
  },
  {
    "IndustryId": "4203",
    "IndustryName": "公交"
  },
  {
    "IndustryId": "4204",
    "IndustryName": "航空运输"
  },
  {
    "IndustryId": "4205",
    "IndustryName": "机场"
  },
  {
    "IndustryId": "4206",
    "IndustryName": "航运"
  },
  {
    "IndustryId": "4207",
    "IndustryName": "铁路运输"
  },
  {
    "IndustryId": "4208",
    "IndustryName": "物流"
  },
  {
    "IndustryId": "6401",
    "IndustryName": "通用机械"
  },
  {
    "IndustryId": "6403",
    "IndustryName": "仪器仪表"
  },
  {
    "IndustryId": "6402",
    "IndustryName": "专用设备"
  },
  {
    "IndustryId": "6405",
    "IndustryName": "运输设备"
  },
  {
    "IndustryId": "6404",
    "IndustryName": "金属制品"
  },
  {
    "IndustryId": "2104",
    "IndustryName": "采掘服务"
  },
  {
    "IndustryId": "2103",
    "IndustryName": "其他采掘"
  },
  {
    "IndustryId": "2102",
    "IndustryName": "煤炭开采"
  },
  {
    "IndustryId": "2101",
    "IndustryName": "石油开采"
  },
  {
    "IndustryId": "4301",
    "IndustryName": "房地产开发"
  },
  {
    "IndustryId": "4302",
    "IndustryName": "园区开发"
  },
  {
    "IndustryId": "6502",
    "IndustryName": "航空装备"
  },
  {
    "IndustryId": "6501",
    "IndustryName": "航天装备"
  },
  {
    "IndustryId": "6504",
    "IndustryName": "船舶制造"
  },
  {
    "IndustryId": "6503",
    "IndustryName": "地面兵装"
  }
]



def get_industry_by_id(industry_id: str) -> dict:
    """根据行业ID获取行业信息"""
    for industry in INDUSTRY_LIST:
        if industry["IndustryId"] == industry_id:
            return industry
    return None


def get_all_industry_names() -> list:
    """获取所有行业名称列表"""
    return [industry["IndustryName"] for industry in INDUSTRY_LIST]


def get_all_industry_ids() -> list:
    """获取所有行业ID列表"""
    return [industry["IndustryId"] for industry in INDUSTRY_LIST]
