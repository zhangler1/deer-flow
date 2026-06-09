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
        "source": "交通银行数字化转型三年规划（2025-2027版）.docx",
        "url": "http://mock-wiki/knowledge/digital-transformation/001",
        "content": "第一章 总体目标\n交通银行数字化转型以『科技赋能、数据驱动、业务创新』为核心理念，计划三年累计科技投入不低于600亿元，重点推进AI大模型与金融业务融合应用。\n第二章 重点场景\n优先在智能风控、投研分析、客户服务三大场景落地AI技术，打造行业领先的智慧银行。\n第三章 基础设施\n加快核心系统云化改造，建设企业级数据中台和技术中台，实现业务敏捷迭代。",
        "title": "交通银行数字化转型三年规划（2025-2027版）",
        "docGuid": "digital_transformation_001",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行数字化转型三年规划明确科技投入600亿元，聚焦AI大模型、智能风控、客户服务等核心场景。",
        "knowType": "战略规划",
        "createTime": "2025-01-10 09:00:00",
        "updateTime": "2025-04-15 13:26:29",
        "hobbies": [],
        "fullCategoryName": [
            "战略规划-数字化转型"
        ],
        "attachEcmId": "20250110001_10001_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行数据治理管理办法（2024修订版）.docx",
        "url": "http://mock-wiki/knowledge/data-governance/002",
        "content": "第一章 总则\n为规范全行数据资产管理，提升数据质量和数据应用能力，根据监管要求制定本办法。\n第二章 组织架构\n总行设立数据治理委员会，各分行建立数据管理专岗，形成三级数据管理体系。\n第三章 数据标准\n统一客户数据标准、产品数据标准、交易数据标准，确保跨系统数据一致性和完整性。",
        "title": "交通银行数据治理管理办法（2024修订版）",
        "docGuid": "data_governance_002",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行数据治理管理办法规范数据资产管理，建立三级数据管理体系，统一数据标准。",
        "knowType": "制度文件",
        "createTime": "2024-06-01 10:00:00",
        "updateTime": "2025-03-20 14:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "数据管理-数据治理"
        ],
        "attachEcmId": "20240601002_20002_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行AI大模型应用技术规范_V2.0.docx",
        "url": "http://mock-wiki/knowledge/ai-technology/003",
        "content": "第一章 技术架构\n基于Transformer架构自研金融大模型，参数量达千亿级，支持文本理解、图像识别、语音交互等多模态能力。\n第二章 应用场景\n智能客服：实现80%常见问题自动应答\n智能风控：欺诈识别准确率提升至99.5%\n智能投研：研报生成效率提升10倍\n第三章 安全合规\n模型输出须经过滤审查，确保符合金融监管要求，保护客户隐私。",
        "title": "交通银行AI大模型应用技术规范",
        "docGuid": "ai_technology_003",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行AI大模型技术规范定义了千亿级金融大模型架构，应用于客服、风控、投研等场景。",
        "knowType": "技术规范",
        "createTime": "2023-09-01 08:00:00",
        "updateTime": "2024-01-15 16:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "技术创新-AI应用"
        ],
        "attachEcmId": "20230901003_30003_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行手机银行APP5.0产品需求文档.pdf",
        "url": "http://mock-wiki/knowledge/mobile-bank/004",
        "content": "一、设计理念\n以用户为中心，打造智能化、个性化、场景化的数字金融服务平台。\n二、核心功能\n智能投顾：基于AI算法提供个性化资产配置建议\n语音导航：支持方言识别，提升老年用户体验\n开放银行：接入政务、医疗、教育等第三方服务场景\n三、技术实现\n采用微服务架构，支持日均5000万笔交易处理，响应时间控制在200ms以内。",
        "title": "交通银行手机银行APP5.0产品需求文档",
        "docGuid": "mobile_bank_004",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "手机银行APP5.0采用AI智能投顾、语音导航等创新功能，支持日均5000万笔交易处理。",
        "knowType": "产品文档",
        "createTime": "2024-03-01 09:00:00",
        "updateTime": "2025-02-10 11:30:00",
        "hobbies": [],
        "fullCategoryName": [
            "数字渠道-手机银行"
        ],
        "attachEcmId": "20240301004_40004_06001",
        "fromAttachment": False
    },
    {
        "question": None,
        "source": "交通银行云计算平台建设方案（2025年）.pptx",
        "url": "http://mock-wiki/knowledge/cloud-platform/005",
        "content": "一、建设目标\n构建企业级云平台，实现基础设施即服务（IaaS）、平台即服务（PaaS）、软件即服务（SaaS）三层能力。\n二、技术路线\n采用容器化部署，支持Kubernetes编排，实现资源弹性伸缩。\n三、迁移策略\n分批将核心业务系统迁移至云平台，优先完成渠道类、管理类系统云化，2026年底前核心交易系统云化率达到80%。",
        "title": "交通银行云计算平台建设方案（2025年）",
        "docGuid": "cloud_platform_005",
        "repository": "okic-searchSlicing",
        "sourceType": "HNSS",
        "absContent": "交通银行云计算平台建设方案规划IaaS/PaaS/SaaS三层能力，2026年核心系统云化率达80%。",
        "knowType": "技术方案",
        "createTime": "2025-01-20 09:00:00",
        "updateTime": "2025-02-28 10:00:00",
        "hobbies": [],
        "fullCategoryName": [
            "基础设施-云计算"
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
        "url": "https://www.xinhua.net/finance/article/2025/bocom-digital-transformation-01.html",
        "content": "交通银行正式发布数字化转型三年规划（2025-2027），计划三年累计科技投入不低于600亿元。重点推进AI大模型与金融融合应用，在风控、投研、客服三大场景率先落地。交行自研金融大模型已完成内部测试，预计2025年下半年向全行推广，并加快推进核心系统云化改造。",
        "title": "交通银行发布数字化转型三年规划 三年科技投入不低于600亿元",
        "score": 0.95,
        "docGuid": None,
        "docId": "online_001",
        "repository": "online_search",
        "absContent": "交通银行发布2025-2027数字化转型规划，三年科技投入600亿元，推进AI大模型与金融场景融合。",
        "knowType": None,
        "createTime": "2025-03-28 10:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "21世纪经济报道",
        "url": "https://www.21jingji.com/article/20250315/bocom-ai-model.html",
        "content": "交通银行自研金融大模型『交智』正式亮相，该模型参数量达千亿级，专为中国金融场景优化。在智能客服场景中，实现80%常见问题自动应答；在智能风控场景，欺诈识别准确率提升至99.5%；在智能投研场景，研报生成效率提升10倍。交行成为国内首个将大模型全面应用于核心业务的大型商业银行。",
        "title": "交通银行自研千亿级金融大模型『交智』亮相 全面应用于核心业务",
        "score": 0.89,
        "docGuid": None,
        "docId": "online_002",
        "repository": "online_search",
        "absContent": "交行自研千亿级金融大模型『交智』亮相，客服自动应答率80%，风控准确率99.5%。",
        "knowType": None,
        "createTime": "2025-03-15 09:30:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "中国银行业协会官网",
        "url": "https://www.china-cba.net/news/2025/digital-banking.html",
        "content": "中国银行业协会发布《2025年中国银行业数字化转型报告》，交通银行数字化转型指数位列行业前三。报告指出，交行在AI技术应用、数据治理、云原生架构三大维度表现突出，手机银行月活用户达1.3亿，线上业务占比超过85%。交行董事长表示，数字化转型已成为交行高质量发展的核心引擎。",
        "title": "2025年银行业数字化转型报告发布 交通银行指数位列前三",
        "score": 0.82,
        "docGuid": None,
        "docId": "online_003",
        "repository": "online_search",
        "absContent": "交行数字化转型指数位列行业前三，手机银行月活1.3亿，线上业务占比超85%。",
        "knowType": None,
        "createTime": "2025-02-20 14:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "财联社",
        "url": "https://www.cls.cn/article/2025/bocom-cloud-migration.html",
        "content": "交通银行核心系统云化改造取得重大进展，截至2025年一季度，已有75%的业务系统完成云迁移，云化率居行业领先。交行采用自主可控的金融云架构，实现资源弹性伸缩和秒级故障切换。核心交易系统云化后，交易处理能力提升3倍，系统可用性达到99.999%，为业务创新提供强大技术支撑。",
        "title": "交通银行核心系统云化率达75% 交易处理能力提升3倍",
        "score": 0.76,
        "docGuid": None,
        "docId": "online_004",
        "repository": "online_search",
        "absContent": "交行75%业务系统完成云迁移，交易处理能力提升3倍，系统可用性99.999%。",
        "knowType": None,
        "createTime": "2025-01-18 16:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "证券时报",
        "url": "https://www.stcn.com/article/2025/bocom-data-governance.html",
        "content": "交通银行建立企业级数据治理体系，设立数据治理委员会，形成总行-分行-支行三级数据管理架构。统一客户数据标准、产品数据标准、交易数据标准，数据质量评分提升至98.5%。交行数据中台已接入200+业务系统，日处理数据量超过50TB，为精准营销、智能风控、个性化服务提供强大数据支撑。",
        "title": "交通银行建成企业级数据治理体系 数据质量评分达98.5%",
        "score": 0.71,
        "docGuid": None,
        "docId": "online_005",
        "repository": "online_search",
        "absContent": "交行建立三级数据管理体系，数据质量98.5%，数据中台日处理50TB数据。",
        "knowType": None,
        "createTime": "2025-02-05 11:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "经济观察报",
        "url": "https://www.eeo.com.cn/article/2025/bocom-mobile-bank.html",
        "content": "交通银行手机银行APP5.0全新发布，以『智能化、个性化、场景化』为设计理念，集成AI智能投顾、语音导航、开放银行等创新功能。智能投顾基于AI算法提供个性化资产配置建议，语音导航支持方言识别提升老年用户体验。开放银行接入政务、医疗、教育等第三方服务场景，月活用户突破1.3亿，同比增长25%。",
        "title": "交通银行手机银行APP5.0发布 AI智能投顾成新亮点",
        "score": 0.68,
        "docGuid": None,
        "docId": "online_006",
        "repository": "online_search",
        "absContent": "交行手机银行APP5.0发布，集成AI投顾、语音导航，月活突破1.3亿。",
        "knowType": None,
        "createTime": "2025-04-10 08:30:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "中国证券报",
        "url": "https://www.cs.com.cn/article/2025/bocom-smart-risk.html",
        "content": "交通银行智能风控系统全面升级，引入AI大模型技术，实现欺诈识别准确率99.5%、信贷审批时间从3天缩短至30分钟、不良贷款率降至1.28%。系统整合客户行为数据、交易数据、外部数据，构建超过500个风控特征变量，实现贷前、贷中、贷后全流程智能风控，每年避免欺诈损失超过10亿元。",
        "title": "交通银行智能风控系统升级 欺诈识别准确率达99.5%",
        "score": 0.65,
        "docGuid": None,
        "docId": "online_007",
        "repository": "online_search",
        "absContent": "交行智能风控欺诈识别99.5%，审批30分钟完成，不良率降至1.28%。",
        "knowType": None,
        "createTime": "2025-04-05 10:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "银行家杂志",
        "url": "https://www.banker.com.cn/article/2025/bocom-open-banking.html",
        "content": "交通银行开放银行战略取得显著成效，API开放平台已对接超过500家第三方机构，覆盖政务、医疗、教育、电商等20+行业场景。通过开放API接口，交行将金融服务嵌入用户日常生活，场景金融交易规模突破2万亿元。交行表示，未来将继续深化开放银行建设，打造无边界的金融服务生态。",
        "title": "交通银行开放银行对接500家机构 场景金融规模破2万亿",
        "score": 0.63,
        "docGuid": None,
        "docId": "online_008",
        "repository": "online_search",
        "absContent": "交行开放银行对接500家机构，覆盖20+行业，场景金融规模2万亿。",
        "knowType": None,
        "createTime": "2025-04-12 09:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "第一财经",
        "url": "https://www.yicai.com/article/2025/bocom-digital-talent.html",
        "content": "交通银行加大数字化人才队伍建设，2025年一季度科技人员占比提升至12%，较2023年提高5个百分点。交行与清华大学、复旦大学等高校建立联合实验室，培养金融科技复合型人才。同时推出『数字交行』内部培训计划，全行超过3万名员工完成数字化转型专题培训，打造科技与业务深度融合的人才梯队。",
        "title": "交通银行科技人员占比提升至12% 打造数字化人才梯队",
        "score": 0.60,
        "docGuid": None,
        "docId": "online_009",
        "repository": "online_search",
        "absContent": "交行科技人员占比12%，与高校建联合实验室，3万员工完成数字化培训。",
        "knowType": None,
        "createTime": "2025-03-25 14:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
    },
    {
        "question": None,
        "source": "南方都市报",
        "url": "https://www.nandu.com/article/2025/bocom-digital-achievement.html",
        "content": "交通银行数字化转型成效显著，2025年一季度实现营业收入2456亿元，同比增长3.2%，其中线上业务贡献占比超过85%。手机银行月活用户达1.3亿，同比增长25%；智能客服分流率达80%，年节省运营成本超过5亿元。交行数字化转型经验被中国银保监会列为行业典型案例，向全行业推广。",
        "title": "交通银行数字化转型成效显著 线上业务贡献超85%",
        "score": 0.57,
        "docGuid": None,
        "docId": "online_010",
        "repository": "online_search",
        "absContent": "交行线上业务贡献超85%，手机月活1.3亿，智能客服分流率80%。",
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
        "content": "交通银行数字化转型总体目标：以『科技赋能、数据驱动、业务创新』为核心理念，2025-2027年累计科技投入不低于600亿元。重点推进AI大模型与金融业务融合应用，在智能风控、投研分析、客户服务三大场景率先落地。加快核心系统云化改造，建设企业级数据中台和技术中台，实现业务敏捷迭代，打造行业领先的智慧银行。",
        "score": 0.6892,
        "rerankScore": None,
        "fileId": "FILE_MOCK_001",
        "fileName": "交通银行数字化转型三年规划（2025-2027）",
        "customizedTags": [
            "SP0000100_内网_战略规划",
            "数字化转型",
        ],
        "createTime": "Mon Mar 03 10:00:00 CST 2026",
        "updateTime": "Tue Mar 04 11:00:00 CST 2026",
        "validTimeStart": "Mon Mar 03 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Mar 03 12:00:00 CST 2026",
        "taskId": "TASK_MOCK_001",
        "page": -1,
        "sorted": 1,
        "paraTitle": "# 1. 交通银行数字化转型总体目标",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-002",
        "content": "交通银行自研金融大模型『交智』技术参数：基于Transformer架构，参数量达千亿级，专为中国金融场景优化。支持文本理解、图像识别、语音交互等多模态能力。在智能客服场景实现80%常见问题自动应答，在智能风控场景欺诈识别准确率提升至99.5%，在智能投研场景研报生成效率提升10倍。模型输出须经过滤审查，确保符合金融监管要求。",
        "score": 0.6541,
        "rerankScore": None,
        "fileId": "FILE_MOCK_002",
        "fileName": "交通银行AI大模型应用技术规范_V2.0",
        "customizedTags": [
            "SP0000100_内网_技术规范",
            "AI大模型",
        ],
        "createTime": "Wed Apr 09 09:00:00 CST 2026",
        "updateTime": "Wed Apr 09 18:00:00 CST 2026",
        "validTimeStart": "Wed Apr 09 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Wed Apr 09 14:30:00 CST 2026",
        "taskId": "TASK_MOCK_002",
        "page": -1,
        "sorted": 2,
        "paraTitle": "# 交通银行AI大模型技术参数",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-003",
        "content": "交通银行核心系统云化改造进展：截至2025年一季度，已有75%的业务系统完成云迁移，云化率居行业领先。采用自主可控的金融云架构，实现资源弹性伸缩和秒级故障切换。核心交易系统云化后，交易处理能力提升3倍，系统可用性达到99.999%。计划2026年底前核心交易系统云化率达到80%，为业务创新提供强大技术支撑。",
        "score": 0.6213,
        "rerankScore": None,
        "fileId": "FILE_MOCK_003",
        "fileName": "交通银行云计算平台建设方案（2025年）",
        "customizedTags": [
            "SP0000100_内网_技术方案",
            "云计算",
        ],
        "createTime": "Fri Feb 20 09:00:00 CST 2026",
        "updateTime": "Mon Feb 23 10:00:00 CST 2026",
        "validTimeStart": "Fri Feb 20 09:00:00 CST 2026",
        "validTimeEnd": "Fri Jan 01 08:00:00 CST 2038",
        "pubTime": "Fri Feb 20 16:00:00 CST 2026",
        "taskId": "TASK_MOCK_003",
        "page": -1,
        "sorted": 3,
        "paraTitle": "# 交通银行核心系统云化进展",
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
        "content": "交通银行数据治理体系建设：设立数据治理委员会，形成总行-分行-支行三级数据管理架构。统一客户数据标准、产品数据标准、交易数据标准，数据质量评分提升至98.5%。数据中台已接入200+业务系统，日处理数据量超过50TB。为精准营销、智能风控、个性化服务提供强大数据支撑，实现数据资产价值最大化。",
        "score": 0.6105,
        "rerankScore": None,
        "fileId": "FILE_MOCK_004",
        "fileName": "交通银行数据治理管理办法（2024修订版）",
        "customizedTags": [
            "SP0000100_内网_制度文件",
            "数据治理",
        ],
        "createTime": "Mon Mar 10 09:00:00 CST 2026",
        "updateTime": "Mon Mar 10 18:00:00 CST 2026",
        "validTimeStart": "Mon Mar 10 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Mar 10 14:00:00 CST 2026",
        "taskId": "TASK_MOCK_004",
        "page": -1,
        "sorted": 4,
        "paraTitle": "# 交通银行数据治理体系",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-005",
        "content": "交通银行手机银行APP5.0核心功能：以『智能化、个性化、场景化』为设计理念。智能投顾基于AI算法提供个性化资产配置建议，语音导航支持方言识别提升老年用户体验，开放银行接入政务、医疗、教育等第三方服务场景。采用微服务架构，支持日均5000万笔交易处理，响应时间控制在200ms以内，月活用户突破1.3亿。",
        "score": 0.5987,
        "rerankScore": None,
        "fileId": "FILE_MOCK_005",
        "fileName": "交通银行手机银行APP5.0产品需求文档",
        "customizedTags": [
            "SP0000100_内网_产品文档",
            "手机银行",
        ],
        "createTime": "Wed Mar 19 10:00:00 CST 2026",
        "updateTime": "Thu Mar 20 09:00:00 CST 2026",
        "validTimeStart": "Wed Mar 19 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Wed Mar 19 15:00:00 CST 2026",
        "taskId": "TASK_MOCK_005",
        "page": -1,
        "sorted": 5,
        "paraTitle": "# 交通银行手机银行APP5.0功能",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-006",
        "content": "交通银行智能风控系统升级成果：引入AI大模型技术，实现欺诈识别准确率99.5%、信贷审批时间从3天缩短至30分钟、不良贷款率降至1.28%。系统整合客户行为数据、交易数据、外部数据，构建超过500个风控特征变量。实现贷前、贷中、贷后全流程智能风控，每年避免欺诈损失超过10亿元，显著提升风险管理能力。",
        "score": 0.5876,
        "rerankScore": None,
        "fileId": "FILE_MOCK_006",
        "fileName": "交通银行智能风控系统建设报告",
        "customizedTags": [
            "SP0000100_内网_风控报告",
            "智能风控",
        ],
        "createTime": "Fri Mar 28 08:00:00 CST 2026",
        "updateTime": "Fri Mar 28 17:00:00 CST 2026",
        "validTimeStart": "Fri Mar 28 08:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Fri Mar 28 13:00:00 CST 2026",
        "taskId": "TASK_MOCK_006",
        "page": -1,
        "sorted": 6,
        "paraTitle": "# 交通银行智能风控系统成果",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-007",
        "content": "交通银行开放银行战略成效：API开放平台已对接超过500家第三方机构，覆盖政务、医疗、教育、电商等20+行业场景。通过开放API接口，将金融服务嵌入用户日常生活，场景金融交易规模突破2万亿元。未来将继续深化开放银行建设，打造无边界的金融服务生态，提升客户体验和品牌影响力。",
        "score": 0.5734,
        "rerankScore": None,
        "fileId": "FILE_MOCK_007",
        "fileName": "交通银行开放银行战略报告",
        "customizedTags": [
            "SP0000100_内网_战略报告",
            "开放银行",
        ],
        "createTime": "Tue Apr 01 09:00:00 CST 2026",
        "updateTime": "Tue Apr 01 17:30:00 CST 2026",
        "validTimeStart": "Tue Apr 01 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Tue Apr 01 14:00:00 CST 2026",
        "taskId": "TASK_MOCK_007",
        "page": -1,
        "sorted": 7,
        "paraTitle": "# 交通银行开放银行战略",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-008",
        "content": "交通银行数字化人才队伍建设：2025年一季度科技人员占比提升至12%，较2023年提高5个百分点。与清华大学、复旦大学等高校建立联合实验室，培养金融科技复合型人才。推出『数字交行』内部培训计划，全行超过3万名员工完成数字化转型专题培训。打造科技与业务深度融合的人才梯队，为数字化转型提供人才保障。",
        "score": 0.5621,
        "rerankScore": None,
        "fileId": "FILE_MOCK_008",
        "fileName": "交通银行数字化人才发展报告",
        "customizedTags": [
            "SP0000100_内网_人才报告",
            "数字化人才",
        ],
        "createTime": "Mon Feb 10 08:00:00 CST 2026",
        "updateTime": "Tue Feb 11 09:00:00 CST 2026",
        "validTimeStart": "Mon Feb 10 08:00:00 CST 2026",
        "validTimeEnd": "Fri Jan 01 08:00:00 CST 2038",
        "pubTime": "Mon Feb 10 16:00:00 CST 2026",
        "taskId": "TASK_MOCK_008",
        "page": -1,
        "sorted": 8,
        "paraTitle": "# 交通银行数字化人才建设",
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
        "content": "交通银行数字化转型成效总结：2025年一季度实现营业收入2456亿元，同比增长3.2%，其中线上业务贡献占比超过85%。手机银行月活用户达1.3亿，同比增长25%；智能客服分流率达80%，年节省运营成本超过5亿元。数字化转型经验被中国银保监会列为行业典型案例，向全行业推广，成为高质量发展核心引擎。",
        "score": 0.5512,
        "rerankScore": None,
        "fileId": "FILE_MOCK_009",
        "fileName": "交通银行数字化转型成效报告",
        "customizedTags": [
            "SP0000100_内网_成效报告",
            "转型成效",
        ],
        "createTime": "Thu Apr 03 10:00:00 CST 2026",
        "updateTime": "Fri Apr 04 09:00:00 CST 2026",
        "validTimeStart": "Thu Apr 03 10:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Thu Apr 03 15:00:00 CST 2026",
        "taskId": "TASK_MOCK_009",
        "page": -1,
        "sorted": 9,
        "paraTitle": "# 交通银行数字化转型成效",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
        "qaType": "QP",
        "fromAttachment": False,
    },
    {
        "paraId": "mock-para-010",
        "content": "交通银行数字化转型未来展望：持续推进AI大模型在更多业务场景落地应用，深化数据要素价值挖掘，加快区块链、隐私计算等前沿技术探索。打造开放、智能、安全的数字金融生态，提升服务实体经济能力。计划2027年全面完成核心系统云化改造，实现数字化转型从『跟跑』向『领跑』转变，打造国际一流智慧银行。",
        "score": 0.5398,
        "rerankScore": None,
        "fileId": "FILE_MOCK_010",
        "fileName": "交通银行数字化转型未来规划",
        "customizedTags": [
            "SP0000100_内网_未来规划",
            "战略展望",
        ],
        "createTime": "Mon Apr 07 09:00:00 CST 2026",
        "updateTime": "Mon Apr 07 18:00:00 CST 2026",
        "validTimeStart": "Mon Apr 07 09:00:00 CST 2026",
        "validTimeEnd": "Wed Dec 31 08:00:00 CST 3000",
        "pubTime": "Mon Apr 07 14:30:00 CST 2026",
        "taskId": "TASK_MOCK_010",
        "page": -1,
        "sorted": 10,
        "paraTitle": "# 交通银行数字化转型展望",
        "mainTaskId": None,
        "knType": 3,
        "sourceOrgId": "-1.0.1000000002.mock",
        "domainTags": None,
        "sceneCodes": ["SP0999999", "SP0000100"],
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


# ============================================================
# 路由：queryUserInfo（用户信息查询）
# ============================================================
@app.post("/ELLM.ELLM-OMSERVICE.V-1.0/queryUserInfo.do")
async def query_user_info(request: Request):
    """用户信息查询 mock 接口。

    通过 guwpToken 获取当前登录用户信息。
    请求格式：application/json
    """
    try:
        body = await request.json()
        req_body = body.get("REQ_BODY", {})
        param = req_body.get("param", {})
        guwp_token = param.get("guwpToken", "") or request.headers.get("guwp-token", "")

        logger.info("[queryUserInfo] guwpToken=%s", guwp_token[:8] + "..." if len(guwp_token) > 8 else guwp_token)

        response_data = {
            "RSP_BODY": {
                "result": {
                    "guwpToken": guwp_token or "mock_guwp_token_default",
                    "guipToken": None,
                    "jrtAuthCode": None,
                    "okicToken": None,
                    "okicType": None,
                    "httpHeaders": None,
                    "branchId": 1000000003,
                    "loginName": "mock_user",
                    "userCode": "9999001",
                    "userName": "张乐",
                    "euifUserId": 5000000001,
                    "device": "PC",
                    "roles": None,
                    "uniqueId": None,
                    "logined": True,
                    "userId": None,
                    "uuid": None,
                    "locale": None,
                    "state": None,
                    "cifId": None,
                    "name": None,
                    "attributes": {},
                },
                "param": None,
            },
            "RSP_HEAD": {
                "TRAN_SUCCESS": "1",
                "TRACE_NO": "mock-omservice-queryUserInfo-001",
                "TRACE_ID": "mock.1.00.queryUserInfo",
                "PROCESS_STATUS_CODE": "N",
                "BIZ_TRACE_NO": None,
            },
        }
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error("[queryUserInfo] 处理请求异常: %s", e)
        return JSONResponse(
            content={
                "RSP_BODY": {"result": None, "param": None},
                "RSP_HEAD": {
                    "TRAN_SUCCESS": "0",
                    "TRACE_NO": "mock-omservice-error",
                    "TRACE_ID": "mock.1.00.error",
                    "PROCESS_STATUS_CODE": "E",
                    "BIZ_TRACE_NO": None,
                },
            },
            status_code=500,
        )


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
    print("  POST /ELLM.ELLM-OMSERVICE.V-1.0/queryUserInfo.do")
    print("       application/json -> queryUserInfo（用户信息查询）")
    print("  GET  /health")
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)
