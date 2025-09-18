# 这是一个简单的mock服务，用于模拟搜索API的响应

import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 创建FastAPI应用
app = FastAPI(title="Mock Search API")

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
        "muwpUser": {
            "muwp_branchID": "1000027159",
            "muwp_loginName": "xuew_4",
            "muwp_userCode": "9743616",
            "muwp_userName": "薛巍",
            "muwp_userID": "132298"
        },
        "result": [
            {
                "question": None,
                "source": "交通银行规章制度管理办法_交银办〔2023〕249号_result",
                "url": None,
                "content": "交通银行规章制度管理办法_交银办〔2023〕249号_result.docx-交通银行规章制度管理办法-第一章 总则-第二条 \n\n交通银行规章制度管理办法-第一章 总则-第二条：第二条 本办法所称规章制度，是指本行就经营管理事项制定的具有普遍适用性和持续效力的规范性文件。本行公司治理文件遵循有关法律法规和本行章程的规定，不属于本办法管理范围。党委、纪委、团委、工会制定的规范性文件，领导讲话、会议纪要、年度工作计划、年度考核办法，以及各类转发文件、事务性通知等，不属于本办法管理范围。\n\n",
                "title": "交通银行规章制度管理办法-第一章 总则-第二条 ",
                "score": "0.91064453",
                "docGuid": None,
                "docId": "600100737b884004aad766b90b8db9b4",
                "repository": "euvd-searchByChannelId",
                "absContent": "交通银行规章制度管理办法_交银办〔2023〕249号_result.docx-交通银行规章制度管理办法-第一章 总则-第二条 \n\n交通银行规章制度管理办法-第一章 总则-第二条：第二条 本办法所称规章制度，是指本行就经营管理事项制定的具有普遍适用性和持续效力的规范性文件。本行公司治理文件遵循有关法律法规和本行章程的规定，不属于本办法管理范围。党委、纪委、团委、工会制定的规范性文件，领导讲话、会议纪要、年度工作计划、年度考核办法，以及各类转发文件、事务性通知等，不属于本办法管理范围。\n\n",
                "knowType": None,
                "createTime": None,
                "updateTime": None,
                "hobbies": None,
                "fullCategoryName": None,
                "orgId": None,
                "fullOrgName": None
            },
            {
                "question": None,
                "source": "中国证券业协会现行自律规则汇编（20240524）",
                "url": None,
                "content": "中国证券业协会现行自律规则汇编（20240524）.docx-中国证券业协会会员管理办法的制定目的 \n\n中国证券业协会会员管理办法的制定目的:第一条为了规范会员管理，保障会员合法权益，促进证券市场公开、公平、公正，推动证券行业健康稳定发展，根据法律、行政法规、部门规章以及《中国证券业协会章程》（以下称《章程》），制定中国证券业协会会员管理办法。\n\n",
                "title": "中国证券业协会会员管理办法的制定目的 ",
                "score": "0.033325195",
                "docGuid": None,
                "docId": "010c375c931f42d6a39c4d85732e6ae6",
                "repository": "euvd-searchByChannelId",
                "absContent": "中国证券业协会现行自律规则汇编（20240524）.docx-中国证券业协会会员管理办法的制定目的 \n\n中国证券业协会会员管理办法的制定目的:第一条为了规范会员管理，保障会员合法权益，促进证券市场公开、公平、公正，推动证券行业健康稳定发展，根据法律、行政法规、部门规章以及《中国证券业协会章程》（以下称《章程》），制定中国证券业协会会员管理办法。\n\n",
                "knowType": None,
                "createTime": None,
                "updateTime": None,
                "hobbies": None,
                "fullCategoryName": None,
                "orgId": None,
                "fullOrgName": None
            }
        ],
        "param": None,
        "TRANS_PROCESS": "",
        "TRAN_ID": ""
    },
    "RSP_HEAD": {
        "TRAN_SUCCESS": "1",
        "TRACE_NO": "office-uat-ellm-b458c997f-8k8cq-5986828119",
        "TRACE_ID": "0cf475b7.1.65.4t3y3aef4d9",
        "PROCESS_STATUS_CODE": "N",
        "BIZ_TRACE_NO": None
    }
}

# 定义JSON请求数据模型
class SearchRequest(BaseModel):
    """搜索请求数据模型"""
    REQ_HEAD: dict = Field(default_factory=dict, description="请求头信息")
    REQ_BODY: dict = Field(default_factory=dict, description="请求体信息")

# 定义接口端点 - 支持JSON请求体
@app.post("/ELLM.ELLM-OFFICE.V-1.0/querySources.do/json")
async def mock_search(search_request: SearchRequest = None):
    """处理搜索请求的主要接口"""
    try:
        # 如果传入了结构化的搜索请求，使用它
        if search_request:
            request_body = search_request.dict()
            print(f"\033[32m收到结构化查询请求:\033[0m")
            print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")
        else:
            # 如果没有传入，创建一个默认的空请求
            request_body = {"REQ_HEAD": {}, "REQ_BODY": {}}
            print(f"\033[32m收到空查询请求，使用默认响应\033[0m")
        
        # 从请求中提取参数
        req_head = request_body.get("REQ_HEAD", {})
        req_body_data = request_body.get("REQ_BODY", {})
        param = req_body_data.get("param", {})
        
        # 安全提取messages数组
        messages = []
        if isinstance(param.get("messages"), list):
            messages = param["messages"]
        
        # 提取查询内容
        user_query = ""
        if messages and isinstance(messages[0], dict):
            user_query = messages[0].get('content', '')
        
        # 安全提取其他参数
        repository = str(param.get("repository", ""))
        channel_param = param.get("param", {})
        channel_id = str(channel_param.get("channelId", ""))
        muwp_user = req_body_data.get("muwpUser", {})
        
        # 打印关键参数日志（使用颜色）
        print(f"\033[35m处理查询请求: query='{user_query}', repository={repository}, channelId={channel_id}\033[0m")
        
        # 创建响应对象，使用深度复制确保不修改原始数据
        import copy
        response = copy.deepcopy(MOCK_RESPONSE)
        
        # 如果请求中有用户信息，使用它
        if isinstance(muwp_user, dict) and muwp_user:
            response['RSP_BODY']['muwpUser'] = muwp_user
        
        # 根据请求中的TRANS_PROCESS和TRAN_ID更新响应（修复字典访问方式）
        if req_head:
            response['RSP_BODY']['TRANS_PROCESS'] = req_head.get('TRANS_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')
        
        # 返回构建的JSON响应
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"\033[31m处理请求失败: {e}\033[0m")
        # 出错时返回默认响应
        return JSONResponse(content=MOCK_RESPONSE)

# 同时保留支持Request对象的接口（为了兼容性）
@app.post("/ELLM.ELLM-OFFICE.V-1.0/querySources.do")
async def mock_search_raw(request: Request):
    """处理原始JSON请求的备用接口"""
    try:
        # 读取原始请求体
        request_body = await request.json()
        print(f"\033[32m收到原始JSON查询请求:\033[0m")
        print(f"{json.dumps(request_body, ensure_ascii=False, indent=2)}")
        
        # 其余处理逻辑与主接口相同...
        # ... existing code ...
        req_head = request_body.get("REQ_HEAD", {})
        req_body_data = request_body.get("REQ_BODY", {})
        param = req_body_data.get("param", {})
        
        messages = []
        if isinstance(param.get("messages"), list):
            messages = param["messages"]
        
        user_query = ""
        if messages and isinstance(messages[0], dict):
            user_query = messages[0].get('content', '')
        
        repository = str(param.get("repository", ""))
        channel_param = param.get("param", {})
        channel_id = str(channel_param.get("channelId", ""))
        muwp_user = req_body_data.get("muwpUser", {})
        
        print(f"\033[35m处理查询请求: query='{user_query}', repository={repository}, channelId={channel_id}\033[0m")
        
        import copy
        response = copy.deepcopy(MOCK_RESPONSE)
        
        if isinstance(muwp_user, dict) and muwp_user:
            response['RSP_BODY']['muwpUser'] = muwp_user
        
        if req_head:
            response['RSP_BODY']['TRANS_PROCESS'] = req_head.get('TRANS_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"\033[31m处理原始请求失败: {e}\033[0m")
        return JSONResponse(content=MOCK_RESPONSE)

# 添加一个简单的健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务，默认监听在0.0.0.0:8010
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)