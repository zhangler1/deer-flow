# 这是一个简单的mock服务，用于模拟行业研报查询API的响应

import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid

# 创建FastAPI应用
app = FastAPI(title="Mock Industry Report API")

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
        "total": 25536105,
        "REQ_BODY": {
            "endDateStr": "et",
            "beginDateStr": "et",
            "reservedField2": "labore esse pariatur culpa",
            "reservedField4": "commodo est minim",
            "pageNum": 1,
            "isRandomQuery": True,
            "reservedField1": "minim tempor elit nisi",
            "pageSize": 2,
            "reservedField3": "est voluptate ad elit",
            "industryCodes": [
                "Lorem fugiat ad"
            ],
            "reservedField5": "et quis minim"
        },
        "requestId": "5f75f044-c39b-4a89-b5a5-7ccc3016d92c",
        "traceNo": "idis-data-uat-idis-6d776f7875-kmnnt-8592611607",
        "TRAN_PROCESS": "",
        "reportList": [
            {
                "id": "AP202512241806987171_61",
                "title": "医药日报：武田Zasocitinib三期临床成功",
                "orgCode": "10062057",
                "orgName": "太平洋证券股份有限公司",
                "authors": [
                    {
                        "analystId": "11000470034",
                        "analystName": "张崴",
                        "certificateNo": "S1190524060001",
                        "edu": None,
                        "orgName": "太平洋证券股份有限公司"
                    },
                    {
                        "analystId": "11000246940",
                        "analystName": "周豫",
                        "certificateNo": "S1190523060002",
                        "edu": "硕士",
                        "orgName": "太平洋证券股份有限公司"
                    }
                ],
                "reportPageSize": 3,
                "attachName": "太平洋证券-医药行业日报：武田Zasocitinib三期临床成功-251222.pdf",
                "attachUrl": "/idis/zjs-attachv2/REPORTNEW/SOURCE7/2025/12/24/行业研报/AP202512241806987171.pdf",
                "content": " ",
                "industryCodeList": [
                    "3702"
                ],
                "industryNameList": [
                    "中药Ⅲ"
                ],
                "publishDate": "2025-12-24",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            },
            {
                "id": "AP202512241806971977_95",
                "title": "储能与锂电行业2026年度策略：能源转型叠加AI驱动，周期反转步入繁荣期",
                "orgCode": "10002333",
                "orgName": "国金证券股份有限公司",
                "authors": [
                    {
                        "analystId": "11000176275",
                        "analystName": "姚遥",
                        "certificateNo": "S1130512080001",
                        "edu": "硕士研究生",
                        "orgName": "国金证券股份有限公司"
                    },
                    {
                        "analystId": "11000378332",
                        "analystName": "宇文甸",
                        "certificateNo": "S1130120100001",
                        "edu": None,
                        "orgName": "国金证券股份有限公司"
                    }
                ],
                "reportPageSize": 49,
                "attachName": "国金证券-储能与锂电行业2026年度策略：能源转型叠加AI驱动，周期反转步入繁荣期-251223.pdf",
                "attachUrl": "/idis/zjs-attachv2/REPORTNEW/SOURCE7/2025/12/24/行业研报/AP202512241806971977.pdf",
                "content": " ",
                "industryCodeList": [
                    "6307"
                ],
                "industryNameList": [
                    "锂电池"
                ],
                "publishDate": "2025-12-24",
                "reservedField1": None,
                "reservedField2": None,
                "reservedField3": None,
                "reservedField4": None,
                "reservedField5": None
            }
        ],
        "TRAN_ID": ""
    },
    "RSP_HEAD": {
        "TRAN_SUCCESS": "1",
        "TRACE_NO": "idis-data-uat-idis-6d776f7875-kmnnt-8592611607",
        "TRACE_ID": "0cf47a2c.1.79.4u28g46zta9",
        "PROCESS_STATUS_CODE": "N",
        "BIZ_TRACE_NO": None,
        "REQUEST_ID": "5f75f044-c39b-4a89-b5a5-7ccc3016d92c"
    }
}

# 定义JSON请求数据模型
class IndustryReportRequest(BaseModel):
    """行业研报请求数据模型"""
    REQ_HEAD: dict = Field(default_factory=dict, description="请求头信息")
    REQ_BODY: dict = Field(default_factory=dict, description="请求体信息")

# 定义接口端点 - 支持JSON请求体
@app.post("/IDIS/IDIS-DATA/queryIndustryReportList.bocms/json")
async def mock_query_industry_report(report_request: IndustryReportRequest = None):
    """处理行业研报查询请求的主要接口"""
    try:
        # 如果传入了结构化的查询请求，使用它
        if report_request:
            request_body = report_request.dict()
            print(f"\033[32m收到结构化行业研报查询请求:\033[0m")
            print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")
        else:
            # 如果没有传入，创建一个默认的空请求
            request_body = {"REQ_HEAD": {}, "REQ_BODY": {}}
            print(f"\033[32m收到空查询请求，使用默认响应\033[0m")

        # 从请求中提取参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})
        req_body_data = req_body.get("REQ_BODY", {})

        # 提取查询参数
        page_num = req_body_data.get("pageNum", 1)
        page_size = req_body_data.get("pageSize", 5)
        begin_date_str = req_body_data.get("beginDateStr", "")
        end_date_str = req_body_data.get("endDateStr", "")
        is_random_query = req_body_data.get("isRandomQuery", False)
        industry_codes = req_body_data.get("industryCodes", [])

        # 打印关键参数日志（使用颜色）
        print(f"\033[35m处理行业研报查询请求: pageNum={page_num}, pageSize={page_size}, "
              f"beginDate={begin_date_str}, endDate={end_date_str}\033[0m")
        print(f"\033[35m行业代码: {industry_codes}, 随机查询: {is_random_query}\033[0m")

        # 添加检索日志记录
        def log_report_summary(page_num, page_size, report_count, reports_data=None):
            """记录研报检索摘要日志"""
            print(f"\033[32m[研报检索摘要] 页码: {page_num}, 每页大小: {page_size}\033[0m "
                  f"\033[35m| 返回结果数: {report_count} 条\033[0m")
            if report_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 总记录数: {MOCK_RESPONSE['RSP_BODY']['total']}\033[0m")

                # 显示前3条结果的信息
                if reports_data and len(reports_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(reports_data))}条研报:\033[0m")
                    for i, report in enumerate(reports_data[:3]):
                        title = report.get('title', '无标题')[:50]  # 截取50个字符
                        org_name = report.get('orgName', '未知机构')
                        report_id = report.get('id', 'N/A')
                        publish_date = report.get('publishDate', 'N/A')
                        print(f"\033[35m  {i+1}. [{report_id}] {title} ({org_name}, {publish_date})\033[0m")
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
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.79.{str(uuid.uuid4())[:12]}"

        # 在响应中回显请求的REQ_BODY
        if isinstance(req_body_data, dict):
            response['RSP_BODY']['REQ_BODY'] = req_body_data

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 记录检索结果摘要
        report_count = len(response['RSP_BODY']['reportList'])
        log_report_summary(page_num, page_size, report_count, response['RSP_BODY']['reportList'])

        # 返回构建的JSON响应
        return JSONResponse(content=response)

    except Exception as e:
        print(f"\033[31m处理请求失败: {e}\033[0m")
        # 出错时返回默认响应
        return JSONResponse(content=MOCK_RESPONSE)

# 同时保留支持Request对象的接口（为了兼容性）
@app.post("/IDIS/IDIS-DATA/queryIndustryReportList.bocms")
async def mock_query_industry_report_raw(request: Request):
    """处理原始JSON请求的备用接口"""
    try:
        # 获取请求的 Content-Type
        content_type = request.headers.get("content-type", "")

        # 读取原始请求体 - 根据Content-Type处理
        if "application/json" in content_type:
            # JSON 格式请求
            request_body = await request.json()
            print(f"\033[32m收到JSON格式行业研报查询请求:\033[0m")
        else:
            # 表单格式请求 (application/x-www-form-urlencoded)
            form_data = await request.form()
            req_message = form_data.get("REQ_MESSAGE")
            if req_message:
                request_body = json.loads(req_message)
                print(f"\033[32m收到表单格式行业研报查询请求:\033[0m")
            else:
                raise ValueError("未找到 REQ_MESSAGE 参数")

        print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 提取请求参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body = request_body.get("REQ_BODY", {})
        req_body_data = req_body.get("REQ_BODY", {})

        # 提取查询参数
        page_num = req_body_data.get("pageNum", 1)
        page_size = req_body_data.get("pageSize", 5)
        begin_date_str = req_body_data.get("beginDateStr", "")
        end_date_str = req_body_data.get("endDateStr", "")
        is_random_query = req_body_data.get("isRandomQuery", False)
        industry_codes = req_body_data.get("industryCodes", [])

        # 打印关键参数日志（使用颜色）
        print(f"\033[35m处理行业研报查询请求: pageNum={page_num}, pageSize={page_size}, "
              f"beginDate={begin_date_str}, endDate={end_date_str}\033[0m")
        print(f"\033[35m行业代码: {industry_codes}, 随机查询: {is_random_query}\033[0m")

        # 添加检索日志记录
        def log_report_summary(page_num, page_size, report_count, reports_data=None):
            """记录研报检索摘要日志"""
            print(f"\033[32m[研报检索摘要] 页码: {page_num}, 每页大小: {page_size}\033[0m "
                  f"\033[35m| 返回结果数: {report_count} 条\033[0m")
            if report_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 总记录数: {MOCK_RESPONSE['RSP_BODY']['total']}\033[0m")

                # 显示前3条结果的信息
                if reports_data and len(reports_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(reports_data))}条研报:\033[0m")
                    for i, report in enumerate(reports_data[:3]):
                        title = report.get('title', '无标题')[:50]  # 截取50个字符
                        org_name = report.get('orgName', '未知机构')
                        report_id = report.get('id', 'N/A')
                        publish_date = report.get('publishDate', 'N/A')
                        print(f"\033[35m  {i+1}. [{report_id}] {title} ({org_name}, {publish_date})\033[0m")
            else:
                print(f"\033[32m[检索详情] 无匹配结果\033[0m")

        import copy
        response = copy.deepcopy(MOCK_RESPONSE)

        # 更新请求ID和追踪号
        response['RSP_BODY']['requestId'] = str(uuid.uuid4())
        response['RSP_BODY']['traceNo'] = f"idis-data-uat-idis-{str(uuid.uuid4())[:8]}-{str(uuid.uuid4())[:4]}"
        response['RSP_HEAD']['REQUEST_ID'] = response['RSP_BODY']['requestId']
        response['RSP_HEAD']['TRACE_NO'] = response['RSP_BODY']['traceNo']
        response['RSP_HEAD']['TRACE_ID'] = f"0cf47a2c.1.79.{str(uuid.uuid4())[:12]}"

        # 在响应中回显请求的REQ_BODY
        if isinstance(req_body_data, dict):
            response['RSP_BODY']['REQ_BODY'] = req_body_data

        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应
        if req_head:
            response['RSP_BODY']['TRAN_PROCESS'] = req_head.get('TRAN_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')

        # 记录检索结果摘要
        report_count = len(response['RSP_BODY']['reportList'])
        log_report_summary(page_num, page_size, report_count, response['RSP_BODY']['reportList'])

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
    print(f"\033[32m[服务启动] Mock行业研报API服务准备启动\033[0m \033[35m| 监听地址: 0.0.0.0:8011\033[0m")
    print(f"\033[32m[接口信息] 主接口: /IDIS/IDIS-DATA/queryIndustryReportList.bocms/json\033[0m")
    print(f"\033[35m[接口信息] 备用接口: /IDIS/IDIS-DATA/queryIndustryReportList.bocms\033[0m")
    print(f"\033[32m[健康检查] 健康检查接口: /health\033[0m")

    # 启动服务，默认监听在0.0.0.0:8011（使用不同端口避免与搜索API冲突）
    uvicorn.run("mock_industry_report_api:app", host="0.0.0.0", port=8011, reload=True)
