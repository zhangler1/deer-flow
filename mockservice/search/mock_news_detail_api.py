# 这是一个简单的mock服务，用于模拟新闻详情查询API的响应

import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid

# 创建FastAPI应用
app = FastAPI(title="Mock News Detail API")

# 添加CORS中间件以允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 固定的响应数据
MOCK_RESPONSE = {
    "RSP_BODY": {
        "newsId": "c0ea7651546650151c2a5b10887d710e",
        "requestId": "e78f0ee5-420b-4ace-bb2f-b9da86b46c12",
        "traceNo": "idis-data-uat-idis-6d776f7875-kmnnt-3079909381",
        "TRAN_PROCESS": "",
        "industryNewsVO": {
            "id": "c0ea7651546650151c2a5b10887d710e",
            "title": "【新华财经独家】税务总局回复取消钢材出口退税：暂未听说",
            "contentAbstract": "记者日前从国家税务总局独家获悉，税务总局目前没有获得“取消钢材出口退税”相关信息，也没有相关需要发布披露的信息，一切以公开发布为主。河北省税务局相关负责人回应，准确的文件目前确实没有。",
            "content": """<p style=\"text-indent: 2em; text-align: justify;\">新华财经北京4月15日电（记者董道勇、刘桃熊） 此前有媒体报道，财政部和国家税务总局将联合发布《关于调整相关产品出口退税率的公告》，自4月10日起执行取消钢材出口退税，其中涉及60个钢铁产品的税则号。调整后，热轧、中厚板和螺纹等初级钢铁产品退税率由现有的13%退税率调整为0；冷轧、镀锌等高附加值产品调整为4%。</p ><p style=\"text-indent: 2em; text-align: justify;\">记者日前从国家税务总局独家获悉，税务总局目前没有获得“取消钢材出口退税”相关信息，也没有相关需要发布披露的信息，一切以公开发布为主。</p ><p style=\"text-indent: 2em; text-align: justify;\">河北作为我国钢铁产业大省，2019年粗钢产量达到2.4亿吨，约占我国粗钢产量近四分之一，占世界近八分之一。记者也联系到国家税务总局河北省税务局，河北省税务局相关负责人回应，准确的文件目前确实没有，河北省税务局也是从网上传言得知这一消息的。</p ><p style=\"text-indent: 2em; text-align: justify;\">如今，“取消钢材出口退税”变得愈发扑朔迷离。据了解，2020年3月17日，财政部公布关于提高部分产品出口退税率的清单，将122种钢铁类产品的出口退税率提升至13%。但截至4月10日，目前相关钢材出口退税率显示仍为13%。</p ><p><br/></p ><p style=\"text-align: right;\" xhdiantou=\"\">编辑：胡玉婷</p ><p style=\"font-size: 14px;\" xhdiantou=\"\">版权声明：未经新华财经书面授权许可，严禁任何个人或机构以任何形式复制、引用本文内容或观点。</p ><p style=\"font-size: 14px;\" xhdiantou=\"\">免责声明：新华财经为新华社承建的国家金融信息平台。任何情况下，本平台所发布的信息均不构成投资建议。</p >""",
            "source": "新华财经",
            "authors": [
                "丁雅雯",
                "陈碧琪"
            ],
            "publishTime": "2021-04-13 15:19:26",
            "category": "独家,宏观",
            "contentId": "cbfProd_52838462",
            "reservedField1": None,
            "reservedField2": None,
            "reservedField3": None,
            "reservedField4": None,
            "reservedField5": None
        },
        "newsType": 5,
        "TRAN_ID": ""
    },
    "RSP_HEAD": {
        "TRAN_SUCCESS": "1",
        "TRACE_NO": "idis-data-uat-idis-6d776f7875-kmnnt-3079909381",
        "TRACE_ID": "0cf47a2c.1.88.4u2imhr6869",
        "PROCESS_STATUS_CODE": "N",
        "BIZ_TRACE_NO": None,
        "REQUEST_ID": "e78f0ee5-420b-4ace-bb2f-b9da86b46c12"
    }
}

# 定义JSON请求数据模型
class NewsDetailRequest(BaseModel):
    """新闻详情请求数据模型"""
    REQ_HEAD: dict = Field(default_factory=dict, description="请求头信息")
    REQ_BODY: dict = Field(default_factory=dict, description="请求体信息")

# 定义接口端点 - 支持JSON请求体
@app.post("/IDIS/IDIS-DATA/queryNewsDetail.bocms/json")
async def mock_query_news_detail(detail_request: NewsDetailRequest = None):
    """处理新闻详情查询请求的主要接口"""
    try:
        # 如果传入了结构化的查询请求，使用它
        if detail_request:
            request_body = detail_request.dict()
            print(f"\033[32m收到结构化新闻详情查询请求:\033[0m")
            print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")
        else:
            # 如果没有传入，创建一个默认的空请求
            request_body = {"REQ_HEAD": {}, "REQ_BODY": {}}
            print(f"\033[32m收到空查询请求，使用默认响应\033[0m")

        # 从请求中提取参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})

        # 提取查询参数
        news_id = req_body.get("newsId", "")
        news_type = req_body.get("newsType", 5)

        # 打印关键参数日志（使用颜色）
        print(f"\033[35m处理新闻详情查询: newsId={news_id}, newsType={news_type}\033[0m")

        # 创建响应对象，使用深度复制确保不修改原始数据
        import copy
        response = copy.deepcopy(MOCK_RESPONSE)

        # 更新请求ID和追踪号
        response['RSP_BODY']['newsId'] = news_id
        response['RSP_BODY']['requestId'] = str(uuid.uuid4())
        response['RSP_BODY']['traceNo'] = f"idis-data-uat-idis-{str(uuid.uuid4())[:8]}-{str(uuid.uuid4())[:4]}"
        response['RSP_HEAD']['REQUEST_ID'] = response['RSP_BODY']['requestId']
        response['RSP_HEAD']['TRACE_NO'] = response['RSP_BODY']['traceNo']
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.88.{str(uuid.uuid4())[:12]}"

        # 更新新闻详情中的ID
        if 'industryNewsVO' in response['RSP_BODY']:
            response['RSP_BODY']['industryNewsVO']['id'] = news_id

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 提取新闻信息用于日志
        news_detail = response['RSP_BODY'].get('industryNewsVO', {})
        title = news_detail.get('title', '无标题')
        source = news_detail.get('source', '未知来源')
        publish_time = news_detail.get('publishTime', 'N/A')

        # 添加检索日志记录
        def log_detail_summary(news_id, title, source, publish_time):
            """记录新闻详情日志"""
            print(f"\033[32m[新闻详情] ID: {news_id}\033[0m")
            print(f"\033[32m[标题] {title}\033[0m")
            print(f"\033[35m[来源] {source} | [发布时间] {publish_time}\033[0m")

        log_detail_summary(news_id, title, source, publish_time)

        # 返回构建的JSON响应
        return JSONResponse(content=response)

    except Exception as e:
        print(f"\033[31m处理请求失败: {e}\033[0m")
        # 出错时返回默认响应
        return JSONResponse(content=MOCK_RESPONSE)

# 同时保留支持Request对象的接口（为了兼容性）
@app.post("/IDIS/IDIS-DATA/queryNewsDetail.bocms")
async def mock_query_news_detail_raw(request: Request):
    """处理原始JSON请求的备用接口"""
    try:
        # 获取请求的 Content-Type
        content_type = request.headers.get("content-type", "")

        # 读取原始请求体 - 根据Content-Type处理
        if "application/json" in content_type:
            # JSON 格式请求
            request_body = await request.json()
            print(f"\033[32m收到JSON格式新闻详情查询请求:\033[0m")
        else:
            # 表单格式请求 (application/x-www-form-urlencoded)
            form_data = await request.form()
            req_message = form_data.get("REQ_MESSAGE")
            if req_message:
                request_body = json.loads(req_message)
                print(f"\033[32m收到表单格式新闻详情查询请求:\033[0m")
            else:
                raise ValueError("未找到 REQ_MESSAGE 参数")

        print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 提取请求参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})

        # 提取查询参数
        news_id = req_body.get("newsId", "")
        news_type = req_body.get("newsType", 5)

        # 打印关键参数日志（使用颜色）
        print(f"\033[35m处理新闻详情查询: newsId={news_id}, newsType={news_type}\033[0m")

        import copy
        response = copy.deepcopy(MOCK_RESPONSE)

        # 更新请求ID和追踪号
        response['RSP_BODY']['newsId'] = news_id
        response['RSP_BODY']['requestId'] = str(uuid.uuid4())
        response['RSP_BODY']['traceNo'] = f"idis-data-uat-idis-{str(uuid.uuid4())[:8]}-{str(uuid.uuid4())[:4]}"
        response['RSP_HEAD']['REQUEST_ID'] = response['RSP_BODY']['requestId']
        response['RSP_HEAD']['TRACE_NO'] = response['RSP_BODY']['traceNo']
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.88.{str(uuid.uuid4())[:12]}"

        # 更新新闻详情中的ID
        if 'industryNewsVO' in response['RSP_BODY']:
            response['RSP_BODY']['industryNewsVO']['id'] = news_id

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 提取新闻信息用于日志
        news_detail = response['RSP_BODY'].get('industryNewsVO', {})
        title = news_detail.get('title', '无标题')
        source = news_detail.get('source', '未知来源')
        publish_time = news_detail.get('publishTime', 'N/A')

        # 添加检索日志记录
        def log_detail_summary(news_id, title, source, publish_time):
            """记录新闻详情日志"""
            print(f"\033[32m[新闻详情] ID: {news_id}\033[0m")
            print(f"\033[32m[标题] {title}\033[0m")
            print(f"\033[35m[来源] {source} | [发布时间] {publish_time}\033[0m")

        log_detail_summary(news_id, title, source, publish_time)

        return JSONResponse(content=response)

    except json.JSONDecodeError as e:
        print(f"\033[31mJSON解析失败: {e}\033[0m")
        print(f"\033[31m请求Content-Type: {request.headers.get('content-type', 'N/A')}\033[0m")
        return JSONResponse(content=MOCK_RESPONSE)
    except Exception as e:
        print(f"\033[31m处理原始请求失败: {e}\033[0m")
        import traceback
        print(f"\033[31m错误详情:\033[0m {traceback.format_exc()}")
        return JSONResponse(content=MOCK_RESPONSE)

# 添加一个简单的健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务时的日志
    print(f"\033[32m[服务启动] Mock新闻详情API服务准备启动\033[0m \033[35m| 监听地址: 0.0.0.0:8013\033[0m")
    print(f"\033[32m[接口信息] 主接口: /IDIS/IDIS-DATA/queryNewsDetail.bocms/json\033[0m")
    print(f"\033[35m[接口信息] 备用接口: /IDIS/IDIS-DATA/queryNewsDetail.bocms\033[0m")
    print(f"\033[32m[健康检查] 健康检查接口: /health\033[0m")

    # 启动服务，默认监听在0.0.0.0:8013（使用不同端口避免冲突）
    uvicorn.run("mock_news_detail_api:app", host="0.0.0.0", port=8013, reload=True)
