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
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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
        "score": "0.95",
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
        "score": "0.89",
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
        "score": "0.82",
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
        "score": "0.76",
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
        "score": "0.71",
        "docGuid": None,
        "docId": "online_005",
        "repository": "online_search",
        "absContent": "金监总局新规要求消费贷款期限不超5年，不得流入房市股市，须建立资金流向监测机制。",
        "knowType": None,
        "createTime": "2025-02-05 11:00:00",
        "updateTime": None,
        "hobbies": None,
        "fullCategoryName": None
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
    print("  GET  /health")
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)
