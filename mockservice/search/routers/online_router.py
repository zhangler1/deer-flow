"""Mock Search API - online_search 互联网搜索路由"""

import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Mock 数据 online_search（互联网公开信息搜索）
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


@router.post("/ELLM.ELLM-OFFICE.V-1.0/querySources.do")
async def online_search(request: Request):
    """online_search 互联网搜索 mock 接口。
    
    Content-Type: application/json
    """
    query = ""
    muwp_user = {}
    try:
        body = await request.json()
        req_body = body.get("REQ_BODY", {})
        param = req_body.get("param", {})
        messages = param.get("messages", [])
        if messages and isinstance(messages[0], dict):
            query = messages[0].get("content", "")
        muwp_user = req_body.get("muwpUser", {})
        response_data = _build_online_response(query, muwp_user)
        logger.info("[online_search] query=%r -> %d 条互联网结果", query, len(ONLINE_MOCK_RESULTS))
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error("[online_search] 处理请求异常: %s", e)
        return JSONResponse(content=_build_online_response("", {}))
