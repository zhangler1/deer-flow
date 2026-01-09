# 这是一个简单的mock服务，用于模拟新闻查询API的响应

import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid

# 创建FastAPI应用
app = FastAPI(title="Mock News API")

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
        "beginDateStr": "2020-11-11 00:00:00",
        "isRandomQuery": False,
        "traceNo": "idis-data-uat-idis-6d776f7875-kmnnt-5324039817",
        "TRAN_PROCESS": "",
        "pageSize": 5,
        "categoryCode": "news_exclusive",
        "title": "财经",
        "pageNum": 2,
        "newsType": 5,
        "total": 38,
        "sortType": 1,
        "requestId": "f88d94a2-5761-42a1-be9e-b99343055430",
        "industryNewsList": [
            {
                "id": "c0ea7651546650151c2a5b10887d710e",
                "title": "【新华财经独家】税务总局回复取消钢材出口退税：暂未听说",
                "contentAbstract": """记者日前从国家税务总局独家获悉，税务总局目前没有获得"取消钢材出口退税"相关信息，也没有相关需要发布披露的信息，一切以公开发布为主。河北省税务局相关负责人回应，准确的文件目前确实没有。""",
                "content": None,
                "source": "新华财经",
                "authors": [
                    "董道勇",
                    "刘桃熊"
                ],
                "publishTime": "2021-04-15 17:13:02",
                "category": "独家,宏观",
                "contentId": "cbfProd_53344001",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            },
            {
                "id": "caf0296864c6220fbc016f214f63f95b",
                "title": "【新华财经独家】首批公募REITs有望于下周启动发行上市程序",
                "contentAbstract": "基础设施公募REITs试点已进入正式落地前的冲刺阶段，记者从相关机构处获悉，最快有望于6月5日看到发行上市程序的启动。",
                "content": None,
                "source": "新华财经",
                "authors": [
                    "杨溢仁"
                ],
                "publishTime": "2021-05-26 20:01:27",
                "category": "独家",
                "contentId": "cbfProd_54776137",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            },
            {
                "id": "5bd1c7c1cd7bca32e60cb6db1c40b8d0",
                "title": "【新华财经独家】欧盟将以巨额补贴建芯片厂 短缺会变过剩吗?",
                "contentAbstract": "有机构预期芯片供应瓶颈甚至可能会持续到明年年初。欧洲特别是德国正在加紧上马芯片厂，这也引发了业内对未来供应过剩的担忧。",
                "content": None,
                "source": "新华财经",
                "authors": [
                    "邵莉"
                ],
                "publishTime": "2021-05-27 10:41:56",
                "category": "独家,宏观",
                "contentId": "cbfProd_54777860",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            },
            {
                "id": "49554bd8052bcfee9d595fd026d76206",
                "title": "【新华财经独家】西共体单一货币或利于中非经贸合作",
                "contentAbstract": "中国对西非出口被区内国家商品替代的可能性很小，反而统一货币ECO可解决目前西共体各国货币不可自由兑换的问题，降低其汇率波动风险，为经贸发展创造安全稳定的环境。可以预见，中国对西非贸易和投资会在不久的将来会快速增长。",
                "content": None,
                "source": "新华财经",
                "authors": [
                    "丁蕾",
                    "许正"
                ],
                "publishTime": "2021-06-30 08:09:17",
                "category": "独家,宏观",
                "contentId": "cbfProd_55796577",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            },
            {
                "id": "59f1d38eba83703b0a6ba9ce726cd3a9",
                "title": "【新华财经独家】中资企业在中东欧国家的投资风险趋升",
                "contentAbstract": "迫于美国的政治压力，去年以来部分中东欧国家吸引中国投资的意愿下降，有的国家甚至取消了与中国企业签订的项目合同，并将华为等中资企业排除在本国基础设施建设之外。",
                "content": None,
                "source": "新华财经",
                "authors": [
                    "邵莉"
                ],
                "publishTime": "2021-02-22 16:01:06",
                "category": "独家,宏观",
                "contentId": "cbfProd_47267597",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            }
        ],
        "endDateStr": "2025-11-11 00:00:00",
        "TRAN_ID": ""
    },
    "RSP_HEAD": {
        "TRAN_SUCCESS": "1",
        "TRACE_NO": "idis-data-uat-idis-6d776f7875-kmnnt-5324039817",
        "TRACE_ID": "0cf47a2c.1.75.4u2isc77a7d",
        "PROCESS_STATUS_CODE": "N",
        "BIZ_TRACE_NO": None,
        "REQUEST_ID": "f88d94a2-5761-42a1-be9e-b99343055430"
    }
}

# 定义JSON请求数据模型
class NewsRequest(BaseModel):
    """新闻请求数据模型"""
    REQ_HEAD: dict = Field(default_factory=dict, description="请求头信息")
    REQ_BODY: dict = Field(default_factory=dict, description="请求体信息")

# 定义接口端点 - 支持JSON请求体
@app.post("/IDIS/IDIS-DATA/queryNewsList.bocms/json")
async def mock_query_news(news_request: NewsRequest = None):
    """处理新闻查询请求的主要接口"""
    try:
        # 如果传入了结构化的查询请求，使用它
        if news_request:
            request_body = news_request.dict()
            print(f"\033[32m收到结构化新闻查询请求:\033[0m")
            print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")
        else:
            # 如果没有传入，创建一个默认的空请求
            request_body = {"REQ_HEAD": {}, "REQ_BODY": {}}
            print(f"\033[32m收到空查询请求，使用默认响应\033[0m")

        # 从请求中提取参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})

        # 提取查询参数
        title = req_body.get("title", "")
        category_code = req_body.get("categoryCode", "news_exclusive")
        page_num = req_body.get("pageNum", 1)
        page_size = req_body.get("pageSize", 5)
        begin_date_str = req_body.get("beginDateStr", "")
        end_date_str = req_body.get("endDateStr", "")
        sort_type = req_body.get("sortType", 1)
        is_random_query = req_body.get("isRandomQuery", False)

        # 打印关键参数日志（使用颜色）
        category_name = {
            "news_exclusive": "独家",
            "news_macro": "宏观",
            "news_region": "行业",
            "news_commodity": "大宗"
        }.get(category_code, category_code)

        sort_name = "热度" if sort_type == 1 else "时间"

        print(f"\033[35m处理新闻查询: 关键词='{title}' | 类型: {category_name} | "
              f"排序: {sort_name} | 页码: {page_num}, 每页: {page_size}\033[0m")

        # 添加检索日志记录
        def log_news_summary(title, category_name, sort_name, page_num, page_size, news_count, news_data=None):
            """记录新闻检索摘要日志"""
            print(f"\033[32m[新闻检索摘要] 关键词: '{title}'\033[0m "
                  f"\033[35m| 类型: {category_name} | 排序: {sort_name}\033[0m "
                  f"\033[35m| 页码: {page_num}, 每页: {page_size}\033[0m "
                  f"\033[35m| 返回结果数: {news_count} 条\033[0m")
            if news_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 总记录数: {MOCK_RESPONSE['RSP_BODY']['total']}\033[0m")

                # 显示前3条结果的信息
                if news_data and len(news_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(news_data))}条新闻:\033[0m")
                    for i, news in enumerate(news_data[:3]):
                        news_title = news.get('title', '无标题')[:50]  # 截取50个字符
                        source = news.get('source', '未知来源')
                        publish_time = news.get('publishTime', 'N/A')
                        news_id = news.get('id', 'N/A')
                        print(f"\033[35m  {i+1}. [{news_id}] {news_title} ({source}, {publish_time})\033[0m")
            else:
                print(f"\033[32m[检索详情] 无匹配结果\033[0m")

        # 创建响应对象，使用深度复制确保不修改原始数据
        import copy
        response = copy.deepcopy(MOCK_RESPONSE)

        # 更新请求ID和追踪号
        response['RSP_BODY']['requestId'] = str(uuid.uuid4())
        response['RSP_BODY']['traceNo'] = f"idis-data-uat-idis-{str(uuid.uuid4())[:8]}-{str(uuid.uuid4())[:4]}"
        response['RSP_HEAD']['REQUEST_ID'] = response['RSP_BODY']['requestId']
        response['RSP_HEAD']['TRACE_NO'] = response['RSP_BODY']['traceNo']
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.75.{str(uuid.uuid4())[:12]}"

        # 在响应中回显请求的关键参数
        response['RSP_BODY']['title'] = title
        response['RSP_BODY']['categoryCode'] = category_code
        response['RSP_BODY']['pageNum'] = page_num
        response['RSP_BODY']['pageSize'] = page_size
        response['RSP_BODY']['beginDateStr'] = begin_date_str
        response['RSP_BODY']['endDateStr'] = end_date_str
        response['RSP_BODY']['sortType'] = sort_type
        response['RSP_BODY']['isRandomQuery'] = is_random_query

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 记录检索结果摘要
        news_count = len(response['RSP_BODY']['industryNewsList'])
        log_news_summary(title, category_name, sort_name, page_num, page_size, news_count, response['RSP_BODY']['industryNewsList'])

        # 返回构建的JSON响应
        return JSONResponse(content=response)

    except Exception as e:
        print(f"\033[31m处理请求失败: {e}\033[0m")
        # 出错时返回默认响应
        return JSONResponse(content=MOCK_RESPONSE)

# 同时保留支持Request对象的接口（为了兼容性）
@app.post("/IDIS/IDIS-DATA/queryNewsList.bocms")
async def mock_query_news_raw(request: Request):
    """处理原始JSON请求的备用接口"""
    try:
        # 获取请求的 Content-Type
        content_type = request.headers.get("content-type", "")

        # 读取原始请求体 - 根据Content-Type处理
        if "application/json" in content_type:
            # JSON 格式请求
            request_body = await request.json()
            print(f"\033[32m收到JSON格式新闻查询请求:\033[0m")
        else:
            # 表单格式请求 (application/x-www-form-urlencoded)
            form_data = await request.form()
            req_message = form_data.get("REQ_MESSAGE")
            if req_message:
                request_body = json.loads(req_message)
                print(f"\033[32m收到表单格式新闻查询请求:\033[0m")
            else:
                raise ValueError("未找到 REQ_MESSAGE 参数")

        print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 提取请求参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})

        # 提取查询参数
        title = req_body.get("title", "")
        category_code = req_body.get("categoryCode", "news_exclusive")
        page_num = req_body.get("pageNum", 1)
        page_size = req_body.get("pageSize", 5)
        begin_date_str = req_body.get("beginDateStr", "")
        end_date_str = req_body.get("endDateStr", "")
        sort_type = req_body.get("sortType", 1)
        is_random_query = req_body.get("isRandomQuery", False)

        # 打印关键参数日志（使用颜色）
        category_name = {
            "news_exclusive": "独家",
            "news_macro": "宏观",
            "news_region": "行业",
            "news_commodity": "大宗"
        }.get(category_code, category_code)

        sort_name = "热度" if sort_type == 1 else "时间"

        print(f"\033[35m处理新闻查询: 关键词='{title}' | 类型: {category_name} | "
              f"排序: {sort_name} | 页码: {page_num}, 每页: {page_size}\033[0m")

        # 添加检索日志记录
        def log_news_summary(title, category_name, sort_name, page_num, page_size, news_count, news_data=None):
            """记录新闻检索摘要日志"""
            print(f"\033[32m[新闻检索摘要] 关键词: '{title}'\033[0m "
                  f"\033[35m| 类型: {category_name} | 排序: {sort_name}\033[0m "
                  f"\033[35m| 页码: {page_num}, 每页: {page_size}\033[0m "
                  f"\033[35m| 返回结果数: {news_count} 条\033[0m")
            if news_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 总记录数: {MOCK_RESPONSE['RSP_BODY']['total']}\033[0m")

                # 显示前3条结果的信息
                if news_data and len(news_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(news_data))}条新闻:\033[0m")
                    for i, news in enumerate(news_data[:3]):
                        news_title = news.get('title', '无标题')[:50]  # 截取50个字符
                        source = news.get('source', '未知来源')
                        publish_time = news.get('publishTime', 'N/A')
                        news_id = news.get('id', 'N/A')
                        print(f"\033[35m  {i+1}. [{news_id}] {news_title} ({source}, {publish_time})\033[0m")
            else:
                print(f"\033[32m[检索详情] 无匹配结果\033[0m")

        import copy
        response = copy.deepcopy(MOCK_RESPONSE)

        # 更新请求ID和追踪号
        response['RSP_BODY']['requestId'] = str(uuid.uuid4())
        response['RSP_BODY']['traceNo'] = f"idis-data-uat-idis-{str(uuid.uuid4())[:8]}-{str(uuid.uuid4())[:4]}"
        response['RSP_HEAD']['REQUEST_ID'] = response['RSP_BODY']['requestId']
        response['RSP_HEAD']['TRACE_NO'] = response['RSP_BODY']['traceNo']
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.75.{str(uuid.uuid4())[:12]}"

        # 在响应中回显请求的关键参数
        response['RSP_BODY']['title'] = title
        response['RSP_BODY']['categoryCode'] = category_code
        response['RSP_BODY']['pageNum'] = page_num
        response['RSP_BODY']['pageSize'] = page_size
        response['RSP_BODY']['beginDateStr'] = begin_date_str
        response['RSP_BODY']['endDateStr'] = end_date_str
        response['RSP_BODY']['sortType'] = sort_type
        response['RSP_BODY']['isRandomQuery'] = is_random_query

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 记录检索结果摘要
        news_count = len(response['RSP_BODY']['industryNewsList'])
        log_news_summary(title, category_name, sort_name, page_num, page_size, news_count, response['RSP_BODY']['industryNewsList'])

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
    print(f"\033[32m[服务启动] Mock新闻API服务准备启动\033[0m \033[35m| 监听地址: 0.0.0.0:8012\033[0m")
    print(f"\033[32m[接口信息] 主接口: /IDIS/IDIS-DATA/queryNewsList.bocms/json\033[0m")
    print(f"\033[35m[接口信息] 备用接口: /IDIS/IDIS-DATA/queryNewsList.bocms\033[0m")
    print(f"\033[32m[健康检查] 健康检查接口: /health\033[0m")

    # 启动服务，默认监听在0.0.0.0:8012（使用不同端口避免冲突）
    uvicorn.run("mock_news_api:app", host="0.0.0.0", port=8012, reload=True)
