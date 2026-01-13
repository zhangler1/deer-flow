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
		"beginDateStr": "2019-01-01 00:00:00",
		"isRandomQuery": False,
		"traceNo": "idis-data-uat-idis-86dd875bb5-sw4rs-8044250482",
		"TRAN_PROCESS": "",
		"pageSize": 20,
		"title": "交通银行 惠民贷 政策 发展 历史",
		"pageNum": 1,
		"newsType": 5,
		"total": 13240,
		"sortType": 1,
		"requestId": "39615f21-7c96-4189-825d-7bd4f9e800f7",
		"industryNewsList": [
			{
				"id": "640534fa15afae4a742265f411585484",
				"title": "交通银行海南省分行主动授信送“贷”上门  创新支持小微科技企业发展",
				"contentAbstract": "交通银行海南省分行充分发挥金融科技优势，构建支持小微企业融资协调工作机制，对目标客户“主动授信”，打造服务科技型小微企业全生命周期产品体系，取得良好效果。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"龙珊"
				],
				"publishTime": "2025-02-22 14:49:57",
				"category": "",
				"contentId": "cbfProd_318104122022977536",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "c15c76b87195dbad26ec730ad55da192",
				"title": "交通银行浙江省分行上线“科创浙里贷”",
				"contentAbstract": "交通银行浙江省分行近日推出一款基于属地化科创企业大数据评估模型的线上信用贷款产品——“科创浙里贷”，旨在精准服务科技型小微客户。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"包史聪"
				],
				"publishTime": "2025-04-11 19:42:44",
				"category": "",
				"contentId": "cbfProd_335569814863421440",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "cd82a2d03d23e98591cee9efd39efa59",
				"title": "交通银行在第五届消博会上发布个人贷款品牌“交银惠贷”",
				"contentAbstract": "4月14日，在第五届消博会新品发布会上，交通银行发布个人贷款整体品牌“交银惠贷”。该品牌聚焦“惠生活惠经营”双核价值理念，覆盖综合消费、购车出行、住房安居、创业经营、农户生产五大民生场景，重点打造了“惠民贷”“车贷”“房贷”“惠商贷”和“惠农贷”五个子产品。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"叶文华"
				],
				"publishTime": "2025-04-15 16:18:36",
				"category": "",
				"contentId": "cbfProd_336969428460101632",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "68552e6dd824468d6cc7a1ac4de3c77d",
				"title": "交通银行大连分行被罚30万元，因贷后管理不尽职，贷款资金未按约定用途使用。",
				"contentAbstract": "暂无摘要",
				"content": None,
				"source": "中国银保监会网站",
				"authors": None,
				"publishTime": "2021-08-30 15:28:43",
				"category": "",
				"contentId": "cbfProd_57392061",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "33df5351e0e7ba76b7d8f6ef7dce848b",
				"title": "刘鹤主持召开国务院促进中小企业发展工作领导小组第七次会议，会议强调，要把握好政策的连续性、稳定性和可持续性，大力支持中小企业健康发展，金融机构要不断提升能力，做到敢贷、愿贷、能贷、会贷。",
				"contentAbstract": "暂无摘要",
				"content": None,
				"source": "新华财经",
				"authors": None,
				"publishTime": "2021-01-21 19:48:35",
				"category": "",
				"contentId": "cbfProd_46958166",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "a3f6a76ff6e459e359fdac3cfd61c2fc",
				"title": "2025年失业保险稳岗惠民政策出台",
				"contentAbstract": "暂无摘要",
				"content": None,
				"source": "新华财经",
				"authors": None,
				"publishTime": "2025-04-23 14:56:15",
				"category": "",
				"contentId": "cbfProd_339855684143357952",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "3f78eaf106022b60b8e741d0641e59b2",
				"title": "浙江：丰富“政策包”持续促消费惠民生",
				"contentAbstract": "浙江持续丰富“政策包”，通过具有“共富味”“含金量”“科技感”“烟火气”的多项举措大力提振和扩大消费，消费品以旧换新、培育发展消费新场景新业态新模式等专项行动精准落地。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"吕昂"
				],
				"publishTime": "2025-06-18 11:35:37",
				"category": "宏观",
				"contentId": "cbfProd_359688133639561216",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "adeab9a3ef76179a3c16cf379662b6fc",
				"title": "2025年失业保险稳岗惠民政策出台",
				"contentAbstract": "三部门联合发布《关于延续实施失业保险稳岗惠民政策措施的通知》，旨在支持企业稳定岗位和提升劳动者技能，同时兜牢失业保障底线。",
				"content": None,
				"source": "新华社",
				"authors": [
					"姜琳"
				],
				"publishTime": "2025-04-22 20:15:33",
				"category": "宏观",
				"contentId": "cbfProd_339572953857908736",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "937bb8b0023c454fa3a591ed11312e65",
				"title": "交行上海市分行举行“惠商惠民 点亮江杨”定制商圈惠贷产品发布会",
				"contentAbstract": "7月3日，交通银行上海市分行在上海江杨农产品批发市场举行发布仪式，正式推出针对江杨市场的商圈惠贷产品。",
				"content": None,
				"source": "新华财经",
				"authors": None,
				"publishTime": "2025-07-03 21:42:49",
				"category": "",
				"contentId": "cbfProd_365675800785100800",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "5e768c74e73189cd03b8fcf348e7b5a8",
				"title": "交通银行河北省分行“科创数智贷”荣获2024年全国金融系统职工“五小”优秀创新成果奖",
				"contentAbstract": "交通银行河北省分行《关于“科创数智贷”线上信用贷款产品的小发明》在全国金融系统616个创新成果中脱颖而出，成功入选优秀创新成果。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"侯亚坤"
				],
				"publishTime": "2025-01-14 14:05:25",
				"category": "宏观",
				"contentId": "cbfProd_303904830769094656",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "95a417887504b0a4fe4a0fda0b3ced4f",
				"title": "【沈河金廊发布】沈阳召开“首贷户”贴息政策推进会",
				"contentAbstract": "暂无摘要",
				"content": None,
				"source": "沈阳日报",
				"authors": [
					"刘洋"
				],
				"publishTime": "2025-05-14 17:08:41",
				"category": "",
				"contentId": "cbfProd_347498323252813824",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "bea9c6a588d45ea06e451310b6e7e6d0",
				"title": "安徽构建“奖、贷、助、补、免”全方位学生资助政策体系",
				"contentAbstract": "近年来，安徽着力建设高质量学生资助体系，自党的十八大以来，已累计资助学生1.9亿人次，发放资助资金1611亿元，资助项目已达到25项，构建了“奖、贷、助、补、免”全方位的学生资助政策体系。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"钱子瑞"
				],
				"publishTime": "2025-08-30 17:36:40",
				"category": "宏观,大宗",
				"contentId": "cbfProd_386632901741486080",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "d2841e2521d118152ec1fa6552bdfb4a",
				"title": "擦亮志愿服务品牌 江苏人社积极推动惠民政策落地",
				"contentAbstract": "本次活动以弘扬新时代雷锋精神为引领，充分发挥党员干部先锋模范作用，通过创新服务形式推动惠民政策直达基层，助力解决群众急难愁盼问题，进一步擦亮“四进三解两知晓”志愿服务品牌，切实提升人社服务的温度与效能。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"赵畅"
				],
				"publishTime": "2025-03-02 09:05:48",
				"category": "",
				"contentId": "cbfProd_320918889829785600",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "7d34799a91c06c38c1427427c1da8299",
				"title": "财政部：两项贴息政策将财政金融政策着力点更多转向惠民生、促消费",
				"contentAbstract": "对居民个人消费贷款和消费领域的服务业经营主体贷款实施贴息政策，这是中央层面首次实施，有媒体称之为消费贷款领域的又一次“国补”，其补贴方式更精准，支持消费的力度更大，惠及的范围更广，贴息的流程更高效。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"董道勇",
					"翟卓"
				],
				"publishTime": "2025-08-13 15:16:10",
				"category": "宏观",
				"contentId": "cbfProd_380446501526315008",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "4a369f2fd223a55415046bf321d745d7",
				"title": "“两新”政策赋能  天津金融跑出惠民惠企“加速度”",
				"contentAbstract": "为响应“新消费”政策号召，兴业银行天津分行针对家电、家装、数码产品等高频消费场景推出“兴闪贷”专项服务，并联合头部电商平台与“兴业生活”App、银联“云闪付”平台，叠加“津夏兴补贴”等惠民活动。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"阎丽梅"
				],
				"publishTime": "2025-08-26 14:35:19",
				"category": "",
				"contentId": "cbfProd_385142245047099392",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "3bd3654961d827e81b7b1bb620a12153",
				"title": "【财经分析】金融促消费政策持续加码 消费贷利率短期或仍将下行",
				"contentAbstract": "业内专家指出，随着金融促消费政策持续发力，多家银行纷纷下调消费贷利率，短期可能仍将进一步下行，将更多让利广大消费者。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"吴丛司"
				],
				"publishTime": "2025-03-17 19:23:18",
				"category": "宏观",
				"contentId": "cbfProd_326481173197316096",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "cd0803d5cb24682aa3563118aaa09bf4",
				"title": "中行上海市分行创新“中银科创算力贷”，券贷联动赋能AI发展",
				"contentAbstract": "5月17日，中国银行以安徽合肥为主会场举办联合发布会，在北京、上海、广东等十个地区同步首发“券贷联动”服务方案暨中银科创算力贷。",
				"content": None,
				"source": "新华财经",
				"authors": [
					"邓侃"
				],
				"publishTime": "2025-05-17 20:07:01",
				"category": "",
				"contentId": "cbfProd_348627680037691392",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "86942745b99382812690544930694a14",
				"title": "【财经分析】金融促消费政策持续加码 消费贷利率短期或仍将下行",
				"contentAbstract": "暂无摘要",
				"content": None,
				"source": "新华财经",
				"authors": [
					"吴丛司"
				],
				"publishTime": "2025-03-18 10:47:42",
				"category": "",
				"contentId": "cbfProd_326744968645386240",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "0e0d3d7e22d4ed9d133a340e9402159d",
				"title": "国有六大行：积极落实个人消费贷贴息政策",
				"contentAbstract": "从个人消费贷款财政贴息标准来看，多家大行均表示，政策执行期内，每名借款人可享受的全部个人消费贷款累计贴息上限为3000元，其中可享受单笔5万元以下的个人消费贷款累计贴息上限为1000元。",
				"content": None,
				"source": "证券日报",
				"authors": [
					"杨洁"
				],
				"publishTime": "2025-09-08 08:06:10",
				"category": "大宗",
				"contentId": "cbfProd_389761934372741120",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			},
			{
				"id": "09735bbf4bdedddc06c84c7d1035d26d",
				"title": "六大行响应消费贷贴息 财政+货币政策扩大受惠群体",
				"contentAbstract": "业内认为，贴息政策下，银行可以不去追寻下沉客户的同时，实现消费贷规模的上量，从而拉大分母，缓和不良率。增加的收益可以用来处理存量零售不良贷款。",
				"content": None,
				"source": "21财经",
				"authors": [
					"叶麦穗"
				],
				"publishTime": "2025-08-05 21:02:16",
				"category": "",
				"contentId": "cbfProd_377634361681731584",
				"reservedField1": None,
				"reservedField2": None,
				"reservedField3": None,
				"reservedField4": None,
				"reservedField5": None
			}
		],
		"endDateStr": "2025-12-31 23:59:59",
		"TRAN_ID": ""
	},
	"RSP_HEAD": {
		"TRAN_SUCCESS": "1",
		"TRACE_NO": "idis-data-uat-idis-86dd875bb5-sw4rs-8044250482",
		"TRACE_ID": "0cf4507a.1.76.4u3rf8grkdp",
		"PROCESS_STATUS_CODE": "N",
		"BIZ_TRACE_NO": None,
		"REQUEST_ID": "39615f21-7c96-4189-825d-7bd4f9e800f7"
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
