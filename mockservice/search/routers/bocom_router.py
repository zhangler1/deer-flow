"""Mock Search API - bocomsearch 内网知识库路由"""

import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Mock 数据 bocomsearch（内网知识库）
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


@router.post("/ELLM.ELLM-OFFICE.V-1.0/querySources.do")
async def bocom_search(request: Request):
    """bocomsearch 内网知识库 mock 接口。
    
    Content-Type: application/x-www-form-urlencoded
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
        query = param.get("summaryQuestion", "")
        response_data = _build_bocom_response(query)
        logger.info("[bocomsearch] query=%r -> %d 条知识库结果", query, len(BOCOM_MOCK_RESULTS))
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error("[bocomsearch] 处理请求异常: %s", e)
        return JSONResponse(content=_build_bocom_response(""))
