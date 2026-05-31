# Mock 搜索服务 统一处理 bocomsearch 和 online_search 两个接口
#
# 接口路径（与内网真实服务完全一致）：
#   POST /ELLM.ELLM-OFFICE.V-1.0/querySources.do
#
# 区分逻辑：
#   Content-Type: application/x-www-form-urlencoded  ->  bocomsearch（内网知识库）
#   Content-Type: application/json                   ->  online_search（互联网搜索）
#
# 启动方式：
#   uvicorn mock_search_api:app --host 0.0.0.0 --port 8010 --reload

import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

app = FastAPI(title="Mock Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Mock 数据 bocomsearch（内网知识库）
# 格式参照：api——info/response.json
# ============================================================
BOCOM_MOCK_RESULTS = [
    {
        "question": None,
        "source": "惠民贷业务管理办法（2021年版）.ofd",
        "url": "http://mock-wiki/knowledge/huiMaiDai/001",
        "content": "一、业务定义\n惠民贷是指交行向符合准入条件的个人客户提供的消费贷款。惠民贷用途仅能用于消费，不得用于购买房产、生产经营，不得用于投资理财及法律法规禁止的其他用途。\n二、开办分行及贷款客群\n办理惠民贷年龄一般要求：男性25-57周岁，女性25-52周岁。\n三、产品要素\n授信额度：全线上申请惠民贷额度最高不超过20万元，线上线下一体化模式最高不超过80万元。",
        "title": "惠民贷业务管理办法（2021年版）",
        "docGuid": "huiMaiDai_001",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "惠民贷是交行向符合准入条件的个人客户提供的消费贷款，用途限于消费场景，额度最高不超过80万元，按客户资质综合评定。",
        "knowType": "文库",
        "createTime": "2025-01-10 09:00:00",
        "updateTime": "2025-04-15 13:26:29",
        "hobbies": [],
        "fullCategoryName": [
            "个人金融-消费贷款"
        ],
        "attachEcmId": "20250101001_10001_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行信用卡业务操作规程（2024修订版）.docx",
        "url": "http://mock-wiki/knowledge/creditCard/002",
        "content": "第一章 总则\n第一条 为规范交通银行信用卡业务操作，保障持卡人权益，根据中国人民银行相关规定，制定本规程。\n第二章 申请与审批\n第二条 个人申请交通银行信用卡，须年满18周岁，具有完全民事行为能力，具备稳定的还款能力。\n第三章 额度管理\n第三条 信用卡额度由系统综合评定，普通卡起步额度一般不低于1000元，白金卡不低于10000元。",
        "title": "交通银行信用卡业务操作规程（2024修订版）",
        "docGuid": "creditCard_002",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行信用卡业务操作规程规范了申请、审批、额度管理等流程，适用于全行信用卡相关业务。",
        "knowType": "文库",
        "createTime": "2024-06-01 10:00:00",
        "updateTime": "2025-03-20 14:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "个人金融-信用卡"
        ],
        "attachEcmId": "20240601002_20002_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行规章制度管理办法_交银办2023年249号.docx",
        "url": "http://mock-wiki/knowledge/regulation/003",
        "content": "第一章 总则\n第二条 本办法所称规章制度，是指本行就经营管理事项制定的具有普遍适用性和持续效力的规范性文件。\n第二章 制定权限\n第五条 总行各部门制定的规章制度，报总行相关管理部门审核后发布。",
        "title": "交通银行规章制度管理办法-第一章 总则",
        "docGuid": "regulation_003",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行规章制度管理办法明确了制度制定权限、审核发布流程及废止机制，是全行制度管理的纲领性文件。",
        "knowType": "制度文件",
        "createTime": "2023-09-01 08:00:00",
        "updateTime": "2024-01-15 16:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "部门事务-公文信息"
        ],
        "attachEcmId": "20230901003_30003_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行个人网银操作手册（V5.0）.pdf",
        "url": "http://mock-wiki/knowledge/netbank/004",
        "content": "一、登录方式\n客户可通过交通银行官网（www.bankcomm.com）或手机银行APP登录个人网银，首次登录须完成实名认证。\n二、常用功能\n账户查询：支持活期、定期、理财、基金等各类账户余额及明细查询。\n转账汇款：支持行内转账、跨行汇款及境外汇款等。\n缴费服务：支持水电燃气、通信费、有线电视等生活缴费。",
        "title": "交通银行个人网银操作手册（V5.0）",
        "docGuid": "netbank_004",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行个人网银操作手册介绍了登录方式及账户查询、转账汇款、缴费服务等常用功能的操作步骤。",
        "knowType": "操作手册",
        "createTime": "2024-03-01 09:00:00",
        "updateTime": "2025-02-10 11:30:00",
        "hobbies": [],
        "fullCategoryName": [
            "数字金融-网银服务"
        ],
        "attachEcmId": "20240301004_40004_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "反洗钱业务培训材料（2025年）.pptx",
        "url": "http://mock-wiki/knowledge/aml/005",
        "content": "一、反洗钱基本概念\n洗钱是指将犯罪所得及其收益通过各种手段掩饰、隐瞒其来源和性质，使其在形式上合法化的行为。\n二、金融机构反洗钱义务\n客户身份识别：开立账户时须核实客户真实身份，留存有效证件信息。\n大额交易报告：单笔人民币交易5万元以上须上报大额交易报告，发现可疑交易须及时向中国人民银行报告。\n三、违规处罚\n违反反洗钱规定的机构和个人，将依法受到行政处罚直至刑事追责。",
        "title": "反洗钱业务培训材料（2025年）",
        "docGuid": "aml_005",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "反洗钱业务培训材料涵盖反洗钱基本概念、金融机构义务及违规处罚，适用于全行员工合规培训。",
        "knowType": "培训材料",
        "createTime": "2025-01-20 09:00:00",
        "updateTime": "2025-02-28 10:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "合规风控-反洗钱"
        ],
        "attachEcmId": "20250120005_50005_06001",
        "fromAttachment": False
    }
]

# ============================================================
# Mock 数据 online_search（互联网公开信息搜索）
# 格式参照：middlewares/search/response.json
# ============================================================
ONLINE_MOCK_RESULTS = [
    {
        "question": None,
        "source": "新华财经",
        "url": "https://www.xinhua.net/finance/article/2025/bocom-profit-01.html",
        "content": "交通银行2024年年度业绩报告显示，全年实现营业收入2456亿元，同比增长3.2%，净利润912亿元，同比增长5.1%。不良贷款率较上年末下降0.05个百分点至1.28%，资产质量持续改善。零售业务客户数突破2亿户，手机银行月活用户达1.3亿。",
        "title": "交通银行2024年实现净利润912亿元 资产质量持续改善",
        "score": 0.95,
        "docGuid": None,
        "docId": "online_001",
        "repository": "online_search",
        "absContent": "交通银行2024年净利润912亿元，同比增长5.1%，不良率降至1.28%，零售客户突破2亿户。",
        "knowType": None,
        "createTime": "2025-03-28 10:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "21世纪经济报道",
        "url": "https://www.21jingji.com/article/20250315/bocom-digital.html",
        "content": "近日，交通银行正式发布数字化转型三年规划（2025-2027），计划三年累计科技投入不低于600亿元。重点推进AI大模型与金融融合应用，在风控、投研、客服三大场景率先落地。交行自研金融大模型已完成内部测试，预计2025年下半年向全行推广，并加快推进核心系统云化改造。",
        "title": "交通银行发布数字化转型三年规划 三年科技投入不低于600亿元",
        "score": 0.89,
        "docGuid": None,
        "docId": "online_002",
        "repository": "online_search",
        "absContent": "交通银行发布2025-2027数字化转型规划，三年科技投入600亿元，推进AI大模型与金融场景融合。",
        "knowType": None,
        "createTime": "2025-03-15 09:30:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "中国银行业协会官网",
        "url": "https://www.china-cba.net/news/2025/interest-rate.html",
        "content": "中国人民银行发布公告，自2025年2月20日起，1年期LPR为3.10%，5年期以上LPR为3.60%，均与上月持平。分析人士指出，货币政策保持稳中偏松基调，后续仍有适度降息空间。多家商业银行已调整住房贷款利率，首套房贷款利率最低已降至3.05%。",
        "title": "2025年2月LPR保持不变 首套房贷最低利率已降至3.05%",
        "score": 0.82,
        "docGuid": None,
        "docId": "online_003",
        "repository": "online_search",
        "absContent": "2025年2月LPR维持3.10%/3.60%不变，首套房贷最低利率已降至3.05%，市场预期年内仍有降息空间。",
        "knowType": None,
        "createTime": "2025-02-20 14:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "财联社",
        "url": "https://www.cls.cn/article/2025/fintech-banking.html",
        "content": "金融科技浪潮下，银行业正加速推进智能化升级。据统计，2024年国内银行业IT投入总规模超过3500亿元，同比增长12%。人工智能相关投入占比显著提升，主要聚焦于智能客服、反欺诈风控、精准营销三大方向。头部股份制银行AI应用已覆盖80%以上的高频业务场景，智能客服分流率普遍超过60%。",
        "title": "2024年银行业IT投入超3500亿 AI应用覆盖率持续提升",
        "score": 0.76,
        "docGuid": None,
        "docId": "online_004",
        "repository": "online_search",
        "absContent": "2024年银行业IT投入超3500亿元，AI应用覆盖80%高频场景，智能客服分流率超60%。",
        "knowType": None,
        "createTime": "2025-01-18 16:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "证券时报",
        "url": "https://www.stcn.com/article/2025/personal-loan-policy.html",
        "content": "国家金融监督管理总局近日发布个人消费贷款业务监管指引，进一步规范消费信贷市场秩序。指引明确，消费贷款不得流入房市、股市，金融机构须加强贷款资金用途管控，建立资金流向监测机制。同时要求，消费贷款期限原则上不超过5年，年化利率须在贷款合同中明确披露。",
        "title": "金监总局发布消费贷款监管新规 贷款期限原则上不超过5年",
        "score": 0.71,
        "docGuid": None,
        "docId": "online_005",
        "repository": "online_search",
        "absContent": "金监总局新规要求消费贷款期限不超5年，不得流入房市股市，须建立资金流向监测机制。",
        "knowType": None,
        "createTime": "2025-02-05 11:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "经济观察报",
        "url": "https://www.eeo.com.cn/article/2025/bocom-green-finance.html",
        "content": "交通银行2025年一季度绿色信贷余额突破1.2万亿元，同比增长35%，重点支持新能源、绿色建筑、污染治理等领域。其中，新能源车产业链贷款余额达3200亿元，光伏、风电项目贷款余额合计2800亿元。交行表示，未来将继续加大绿色金融产品创新，探索碳账户与碳资产质押业务。",
        "title": "交通银行绿色信贷突破1.2万亿 新能源产业链成重点方向",
        "score": 0.68,
        "docGuid": None,
        "docId": "online_006",
        "repository": "online_search",
        "absContent": "交行绿色信贷余额突破1.2万亿，新能源车产业链贷款3200亿，加速绿色金融产品创新。",
        "knowType": None,
        "createTime": "2025-04-10 08:30:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "中国证券报",
        "url": "https://www.cs.com.cn/article/2025/cross-border-rmb.html",
        "content": "人民币跨境支付系统（CIPS）最新数据显示，2025年一季度处理业务量突破4.5万亿元，同比增长42%。直接参与者达82家，间接参与者超过1400家。交通银行作为CIPS核心参与行，在东南亚、中东等地区的人民币清算业务增长显著，市场份额排名前三。",
        "title": "CIPS一季度业务量突破4.5万亿 交行跨境清算市场份额前三",
        "score": 0.65,
        "docGuid": None,
        "docId": "online_007",
        "repository": "online_search",
        "absContent": "CIPS一季度处理业务量4.5万亿元，交行跨境人民币清算市场份额居前三。",
        "knowType": None,
        "createTime": "2025-04-05 10:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "银行家杂志",
        "url": "https://www.banker.com.cn/article/2025/wealth-management.html",
        "content": "交通银行财富管理业务截至2025年一季度末，管理客户资产规模（AUM）达5.8万亿元，同比增长18%。私人银行客户数突砈15万户，户均资产超过1200万元。交银理财子公司产品规模突破2万亿，非货币类产品占比提升至45%，权益类产品布局加速。",
        "title": "交通银行财富管理AUM达5.8万亿 私人银行客户砈15万户",
        "score": 0.63,
        "docGuid": None,
        "docId": "online_008",
        "repository": "online_search",
        "absContent": "交行财富AUM达5.8万亿，私行客户砈15万户，交银理财产品规模突破2万亿。",
        "knowType": None,
        "createTime": "2025-04-12 09:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "第一财经",
        "url": "https://www.yicai.com/article/2025/supply-chain-finance.html",
        "content": "交通银行供应链金融平台\u201c交银e链通\u201d2025年一季度累计服务企业超过3.5万家，融资规模达4500亿元。平台利用区块链技术实现应收账款确权、拆分、流转，平均审批时间从3天缩短到30分钟。核心企业信用可沿供应链向下传导至第四层供应商，有效解决中小企业融资难问题。",
        "title": "交行\u201ce链通\u201d平台服务3.5万家企业 区块链审批缩短至30分钟",
        "score": 0.60,
        "docGuid": None,
        "docId": "online_009",
        "repository": "online_search",
        "absContent": "交行供应链平台服务3.5万家企业，融资4500亿，区块链审批从3天缩短至30分钟。",
        "knowType": None,
        "createTime": "2025-03-25 14:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "南方都市报",
        "url": "https://www.nandu.com/article/2025/elderly-finance.html",
        "content": "交通银行针对60岁以上客户群体推出\u201c交银安享\u201d养老金融服务品牌，涵盖大额存单、养老理财、医疗保险、信托传承四大产品线。據悉，该服务品牌已覆盖全国3200多个网点，专属客户经理超过5000人。交行同时与多地社保局对接个人养老金账户，开户数突破1500万。",
        "title": "交通银行推出\u201c交银安享\u201d养老金融服务 个人养老金开户码1500万",
        "score": 0.57,
        "docGuid": None,
        "docId": "online_010",
        "repository": "online_search",
        "absContent": "交行推出养老金融服务品牌，覆盘3200多网点，个人养老金开户码1500万。",
        "knowType": None,
        "createTime": "2025-03-08 15:30:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    }
]


# ============================================================
# Mock 数据 searchknowledge_standard（EUVD 段落级标准知识检索）
# 格式参照：api——info/searchknowledgeStandard/response.txt
# ============================================================
SEARCHKNOWLEDGE_MOCK_RESULTS = [
    {
        "paraId": "mock-para-001",
        "content": "安徽省2026年发布《半导体产业高质量发展三年行动方案》，重点支持化合物半导体、第三代半导体材料、先进封装测试等方向，目标到2028年全省半导体产业规模突破3000亿元。合肥、芜湖、滁州被列为三大产业集聚区，给予最高3000万元的研发补贴及场地租金减免。",
        "score": 0.6892,
        "rerankScore": None,
        "fileId": "FILE_MOCK_001",
        "fileName": "安徽省半导体产业政策汇编（2026版）",
        "customizedTags": [
            "SP0000036_行业知识",
            "半导体",
        ],
        "createTime": "Mon Mar 03 10:00:00 CST 2026",
        "updateTime": "Tue Mar 04 11:00:00 CST 2026",
        "validTimeStart": "Mon Mar 03 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Mar 03 12:00:00 CST 2026",
        "taskId": "TASK_MOCK_001",
        "page": -1,
        "sorted": 1,
        "paraTitle": "# 1. 安徽省2026年半导体产业三年行动方案概述",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-002",
        "content": "2026年Q1全国半导体行业规模以上企业实现营业收入约4200亿元，同比增长12.5%。其中，集成电路设计业增长18.3%，制造业增长9.7%，封测业增长7.2%。下游应用主要集中在汽车电子、AI算力芯片、消费电子三大领域。",
        "score": 0.6541,
        "rerankScore": None,
        "fileId": "FILE_MOCK_002",
        "fileName": "2026年Q1半导体行业运行分析报告",
        "customizedTags": [
            "SP0000036_行业知识",
            "行业类报告",
        ],
        "createTime": "Wed Apr 09 09:00:00 CST 2026",
        "updateTime": "Wed Apr 09 18:00:00 CST 2026",
        "validTimeStart": "Wed Apr 09 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Wed Apr 09 14:30:00 CST 2026",
        "taskId": "TASK_MOCK_002",
        "page": -1,
        "sorted": 2,
        "paraTitle": "# 2026年Q1半导体行业运行情况",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-003",
        "content": "交通银行2026年行业信贷政策对半导体产业链给予重点支持，将其纳入战略新兴产业目录。授信原则：优先支持已纳入工信部‘专精特新’名单的设计、设备、材料类企业；中短期流动资金贷款利率下浮10-20BP；技改贷款给予不超过3年的宽限期。",
        "score": 0.6213,
        "rerankScore": None,
        "fileId": "FILE_MOCK_003",
        "fileName": "交通银行2026年行业信贷政策及投向指引",
        "customizedTags": [
            "SP0000100_内网_办发文",
            "内网_办发文",
        ],
        "createTime": "Fri Feb 20 09:00:00 CST 2026",
        "updateTime": "Mon Feb 23 10:00:00 CST 2026",
        "validTimeStart": "Fri Feb 20 09:00:00 CST 2026",
        "validTimeEnd": "Fri Jan 01 08:00:00 CST 2038",
        "pubTime": "Fri Feb 20 16:00:00 CST 2026",
        "taskId": "TASK_MOCK_003",
        "page": -1,
        "sorted": 3,
        "paraTitle": "# 半导体产业链信贷支持政策",
        "mainTaskId": None,
        "knType": 2,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0000100", "SP0999999"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-004",
        "content": "2026年全球半导体设备市场规模预计达1200亿美元，中国大陆占比约27%。光刻机、刻蚀机、清洗机为三大核心设备，国产替代率分别为5%、25%、55%。国内头部设备厂商包括北方华创、中微公司、盛美上海等，2025年订单增速普遍超过40%。",
        "score": 0.6105,
        "rerankScore": None,
        "fileId": "FILE_MOCK_004",
        "fileName": "2026年半导体设备市场分析报告",
        "customizedTags": [
            "SP0000036_行业知识",
            "半导体设备",
        ],
        "createTime": "Mon Mar 10 09:00:00 CST 2026",
        "updateTime": "Mon Mar 10 18:00:00 CST 2026",
        "validTimeStart": "Mon Mar 10 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Mar 10 14:00:00 CST 2026",
        "taskId": "TASK_MOCK_004",
        "page": -1,
        "sorted": 4,
        "paraTitle": "# 2026年半导体设备市场概况",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-005",
        "content": "第三代半导体材料（碳化硅SiC、氮化镓GaN）在新能源汽车电驱系统中应用正在快速扩大。目前全球SiC功率器件市场规模约70亿美元，预计2028年将达200亿美元。国内代表企业包括三安光电、比亚迪半导体、天科合达等，正在加速6英寸、8英寸SiC衬底量产。",
        "score": 0.5987,
        "rerankScore": None,
        "fileId": "FILE_MOCK_005",
        "fileName": "第三代半导体材料及应用前景分析",
        "customizedTags": [
            "SP0000036_行业知识",
            "半导体材料",
        ],
        "createTime": "Wed Mar 19 10:00:00 CST 2026",
        "updateTime": "Thu Mar 20 09:00:00 CST 2026",
        "validTimeStart": "Wed Mar 19 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Wed Mar 19 15:00:00 CST 2026",
        "taskId": "TASK_MOCK_005",
        "page": -1,
        "sorted": 5,
        "paraTitle": "# 第三代半导体材料应用分析",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-006",
        "content": "AI算力芯片需求爆发式增长，2026年全球AI芯片市场规模预计达800亿美元。NVIDIA、AMD、华为昇腾、寒武纪等为主要玩家。国内AI芯片企业融资需求旺盛，2025年累计融资超过500亿元人民币，银行科技贷款成为重要资金来源。",
        "score": 0.5876,
        "rerankScore": None,
        "fileId": "FILE_MOCK_006",
        "fileName": "AI算力芯片行业发展及融资需求分析",
        "customizedTags": [
            "SP0000036_行业知识",
            "AI芯片",
        ],
        "createTime": "Fri Mar 28 08:00:00 CST 2026",
        "updateTime": "Fri Mar 28 17:00:00 CST 2026",
        "validTimeStart": "Fri Mar 28 08:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Fri Mar 28 13:00:00 CST 2026",
        "taskId": "TASK_MOCK_006",
        "page": -1,
        "sorted": 6,
        "paraTitle": "# AI算力芯片行业融资需求",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-007",
        "content": "安徽省半导体产业园区入驻企业已超过320家，其中规模以上企业86家。合肥长鑫存储、晋华集成电路、融通集成电路等龙头企业带动了大量上下游配套企业入驻。园区2025年总产值预计突破2500亿元，同比增长22%。",
        "score": 0.5734,
        "rerankScore": None,
        "fileId": "FILE_MOCK_007",
        "fileName": "安徽省半导体产业园区发展报告",
        "customizedTags": [
            "SP0000036_行业知识",
            "产业园区",
        ],
        "createTime": "Tue Apr 01 09:00:00 CST 2026",
        "updateTime": "Tue Apr 01 17:30:00 CST 2026",
        "validTimeStart": "Tue Apr 01 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Tue Apr 01 14:00:00 CST 2026",
        "taskId": "TASK_MOCK_007",
        "page": -1,
        "sorted": 7,
        "paraTitle": "# 安徽半导体产业园区发展现状",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-008",
        "content": "半导体企业融资风控要点：1）核心技术团队稳定性，研发人员占比应不低于30%；2）下游客户集中度，前五大客户营收占比不宜超过60%；3）知识产权保护，发明专利数量不少于20件；4）现金流充足性，经营性现金流应连续3年为正。",
        "score": 0.5621,
        "rerankScore": None,
        "fileId": "FILE_MOCK_008",
        "fileName": "半导体行业融资尽调指南",
        "customizedTags": [
            "SP0000100_内网_办发文",
            "融资风控",
        ],
        "createTime": "Mon Feb 10 08:00:00 CST 2026",
        "updateTime": "Tue Feb 11 09:00:00 CST 2026",
        "validTimeStart": "Mon Feb 10 08:00:00 CST 2026",
        "validTimeEnd": "Fri Jan 01 08:00:00 CST 2038",
        "pubTime": "Mon Feb 10 16:00:00 CST 2026",
        "taskId": "TASK_MOCK_008",
        "page": -1,
        "sorted": 8,
        "paraTitle": "# 半导体企业融资尽调要点",
        "mainTaskId": None,
        "knType": 2,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0000100", "SP0999999"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-009",
        "content": "先进封装测试（含Chiplet、晶圆级封装、系统级封装）是后摩尔时代的关键技术方向。全球先进封装市场规模2025年级达440亿美元，中国大陆占比约30%。长电科技、通富微电、华天科技等国内企业在系统级封装领域已具备国际竞争力。",
        "score": 0.5512,
        "rerankScore": None,
        "fileId": "FILE_MOCK_009",
        "fileName": "先进封装行业技术趋势与市场分析",
        "customizedTags": [
            "SP0000036_行业知识",
            "先进封装",
        ],
        "createTime": "Thu Apr 03 10:00:00 CST 2026",
        "updateTime": "Fri Apr 04 09:00:00 CST 2026",
        "validTimeStart": "Thu Apr 03 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Thu Apr 03 15:00:00 CST 2026",
        "taskId": "TASK_MOCK_009",
        "page": -1,
        "sorted": 9,
        "paraTitle": "# 先进封装行业发展趋势",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-010",
        "content": "半导体行业周期性分析：全球半导体行业通常以3-5年为一个完整周期。当前处于上行周期初期，库存去化基本完成，AI新需求驱动存储、算力芯片订单回暖。预计2026-2027年行业将保持两位数增长，但需关注地缘政治风险、产能过剩风险及技术路线不确定性。",
        "score": 0.5398,
        "rerankScore": None,
        "fileId": "FILE_MOCK_010",
        "fileName": "半导体行业周期性分析报告",
        "customizedTags": [
            "SP0000036_行业知识",
            "行业周期",
        ],
        "createTime": "Mon Apr 07 09:00:00 CST 2026",
        "updateTime": "Mon Apr 07 18:00:00 CST 2026",
        "validTimeStart": "Mon Apr 07 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Apr 07 14:30:00 CST 2026",
        "taskId": "TASK_MOCK_010",
        "page": -1,
        "sorted": 10,
        "paraTitle": "# 半导体行业周期分析",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000036"],
        "qaType": "QP",
        "fromAttachment": False,
    },
]


def _build_searchknowledge_response(query: str) -> dict:
    """构造 searchknowledge_standard 响应（EUVD 段落级标准知识检索格式）"""
    return {
        "RSP_BODY": {
            "result": {
                "groupPagination": None,
                "vectorGroupList": SEARCHKNOWLEDGE_MOCK_RESULTS,
                "textGroupList": None,
                "graphGroupList": None,
                "rerankResultList": None,
                "rerankResultStatus": None,
            },
            "param": {"keyword": query},
        },
        "RSP_HEAD": {
            "TRAN_SUCCESS": "1",
            "TRACE_NO": "mock-searchknowledge-trace-001",
            "TRACE_ID": "mock.1.00.searchknowledge",
            "PROCESS_STATUS_CODE": "N",
            "BIZ_TRACE_NO": None,
        },
    }


def _build_bocom_response(query: str) -> dict:
    """构造 bocomsearch 响应（内网知识库格式）"""
    return {
        "RSP_BODY": {
            "result": BOCOM_MOCK_RESULTS,
            "param": None,
            "TRAN_ID": "",
            "TRANS_PROCESS": "",
        },
        "RSP_HEAD": {
            "TRAN_SUCCESS": "1",
            "TRACE_NO": "mock-bocom-trace-001",
            "TRACE_ID": "mock.1.00.bocomsearch",
            "PROCESS_STATUS_CODE": "N",
            "BIZ_TRACE_NO": None,
        },
    }


def _build_online_response(query: str, muwp_user: dict) -> dict:
    """构造 online_search 响应（互联网搜索格式）"""
    return {
        "RSP_BODY": {
            "muwpUser": muwp_user or {
                "muwp_branchID": "",
                "muwp_loginName": "",
                "muwp_userCode": "",
                "muwp_userName": "mock_user",
                "muwp_userID": "",
            },
            "result": ONLINE_MOCK_RESULTS,
            "param": None,
            "TRANS_PROCESS": "",
            "TRAN_ID": "",
        },
        "RSP_HEAD": {
            "TRAN_SUCCESS": "1",
            "TRACE_NO": "mock-online-trace-001",
            "TRACE_ID": "mock.1.00.onlinesearch",
            "PROCESS_STATUS_CODE": "N",
            "BIZ_TRACE_NO": None,
        },
    }


# ============================================================
# 核心接口：统一处理 bocomsearch 和 online_search
# ============================================================
# ============================================================
# 路由：searchknowledge_standard（EUVD 段落级标准知识检索）
# ============================================================
@app.post("/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do")
async def searchknowledge_standard(request: Request):
    """EUVD 段落级标准知识检索 mock 接口。

    与真实接口一致：application/x-www-form-urlencoded，REQ_MESSAGE 字段为 JSON 字符串。
    """
    query = ""
    try:
        form = await request.form()
        req_message_str = form.get("REQ_MESSAGE", "{}")
        try:
            req_message = json.loads(req_message_str)
        except json.JSONDecodeError:
            req_message = {}
        param = req_message.get("REQ_BODY", {}).get("param", {})
        query = param.get("keyword", "")
        response_data = _build_searchknowledge_response(query)
        logger.info(
            "[searchknowledge_standard] query=%r -> %d 条段落结果",
            query, len(SEARCHKNOWLEDGE_MOCK_RESULTS),
        )
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error("[searchknowledge_standard] 处理请求异常: %s", e)
        return JSONResponse(content=_build_searchknowledge_response(""))


@app.post("/ELLM.ELLM-OFFICE.V-1.0/querySources.do")
async def unified_search(request: Request):
    """
    统一搜索接口，根据 Content-Type 自动区分：
    - application/x-www-form-urlencoded -> bocomsearch（内网知识库）
    - application/json                  -> online_search（互联网搜索）
    """
    content_type = request.headers.get("content-type", "")
    query = ""
    muwp_user = {}

    try:
        # bocomsearch：表单格式，从 REQ_MESSAGE 字段解析
        if "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            req_message_str = form.get("REQ_MESSAGE", "{}")
            try:
                req_message = json.loads(req_message_str)
            except json.JSONDecodeError:
                req_message = {}
            param = req_message.get("REQ_BODY", {}).get("param", {})
            query = param.get("summaryQuestion", "")
            response_data = _build_bocom_response(query)
            logger.info("[bocomsearch] query=%r -> %d 条知识库结果", query, len(BOCOM_MOCK_RESULTS))

        # online_search：JSON 格式，从 messages 字段解析
        elif "application/json" in content_type or content_type == "":
            body = await request.json()
            req_body = body.get("REQ_BODY", {})
            param = req_body.get("param", {})
            messages = param.get("messages", [])
            if messages and isinstance(messages[0], dict):
                query = messages[0].get("content", "")
            muwp_user = req_body.get("muwpUser", {})
            response_data = _build_online_response(query, muwp_user)
            logger.info("[online_search] query=%r -> %d 条互联网结果", query, len(ONLINE_MOCK_RESULTS))

        else:
            logger.warning("未知 Content-Type: %s，默认走 online_search 逻辑", content_type)
            response_data = _build_online_response("", {})

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error("[mock_search] 处理请求异常: %s", e)
        return JSONResponse(content=_build_online_response("", {}))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock_search_api", "port": 8010}


if __name__ == "__main__":
    import uvicorn
    print("[Mock Search API 启动]")
    print("  POST /ELLM.ELLM-OFFICE.V-1.0/querySources.do")
    print("       form-urlencoded -> bocomsearch（内网知识库，5条）")
    print("       application/json -> online_search（互联网新闻，5条）")
    print("  POST /EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do")
    print("       form-urlencoded -> searchknowledge_standard（段落级标准知识检索，3条）")
    print("  GET  /health")
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)
