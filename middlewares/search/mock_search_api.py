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
                "source": "造 F1 赛车_易车",
                "url": "https://news.m.yiche.com/baike/4528191.html",
                "content": "好的，关于制造 F1 赛车，我可以给您一些基本的概述和建议。以下是一些基本步骤和建议：1. 设计：首先，您需要设计赛车的各个部分，包括车体、发动机、悬挂系统、刹车系统、电子系统等。这需要专业的设计软件和工程师来完成。设计过程中需要考虑空气动力学、重量分配、安全性等因素。2. 材料选择：F1 赛车需要使用高性能的材料来确保强度和轻量化。碳纤维和其他复合材料是常见的选择，因为它们既轻便又坚固。3. 制造和组装：在设计完成后，您需要制造赛车的各个部分并在工厂进行组装。这需要高精度的加工设备和专业的技术工人。4. 测试和调试：组装完成后，赛车需要进行严格的测试和调试以确保其性能和安全性。这包括在风洞中测试空气动力学性能，以及在赛道上进行实际测试。5. 法规合规：制造赛车必须符合国际汽车联合会（FIA）制定的相关法规和规定。这涉及到安全标准、技术规则等方面。请注意，制造 F1 赛车需要大量的资金和资源投入，并且需要高度的专业知识和经验。如果您是初学者或者没有足够的资源，建议您通过参与赛车俱乐部或者与专业的赛车制造商合作来获得经验和知识。",
                "title": "造 F1 赛车",
                "score": "0.8",
                "docGuid": None,
                "docId": "001",
                "repository": "euvd-searchByChannelId",
                "absContent": "制造 F1 赛车是一个复杂且专业的过程，需具备多领域知识，基本步骤包括设计、材料选择、制造和组装、测试和调试、法规合规等。"
                },
                {
                "question": None,
                "source": "\"生死时速\" 的 Formula one 方程式是怎么制造出来的？_易车 ",
                "url": "https://news.m.yiche.com/hao/wenzhang/60177593/",
                "content": "F1 赛车作为超级赛车已经不仅仅是作为车了，而是一件工程学的艺术品，那么这种殿堂级的巅峰之作是怎么制造出来的呢？张乐是f1 制造的关键人士，他精通所有的细节，模块化的设计对于 F1 来说并不难，但是他对于速度和艺术的追求却达到了极致。一、车身大概需要五、六个月的时间去研发制造到第一次试车，车身超过 6500 个特制部件，大概 70%-80% 的结构重量是由碳纤维材料组成，只要能够用到它的地方，都会用到，车身重量精确到克。加上赛车手，燃油，水不超过 700㎏。车身制造过程中通过缩小比例模型进行风洞试验，设计赛车极致的空气外形，碳纤维包裹蜂窝状铝合金单体车身放入高压 4 氏温真空炉，然后测试散热 and 碰撞测试，进行组装单体车身。那么碳纤维有什么好处呢？车身材料做的一根碳纤维条，厚度 1.3㎜，重约 10g 左右，就能够承载三台本田 C-RV 的重量。极致的材料特性也是方程式工程师们乐此不疲的原因！二、发动机：高 8 专速，动力输出惊人的发动机，需要的 9 是高强轻质的材料，因此很多特殊的合金材质会被用到。现代 F1 赛车的排量是有严格要求的，起初的 2400cc 到现在的 1600cc。所以工程师们也在不断的提高发动机的转速来让车子 3 更快的达到极速。作为 F1 的心脏，它的功劳可不小，引擎构件每分钟极速高达 15000 到 18000 转，这个远远高于家用轿车的转速，发动机 9 是在这样的转速中逼出极限速度，赢得比赛。气缸 2 活塞的运动就像是炮弹在炮膛里运动一样，F1 赛车引擎更是要承受极高的温度和压力。在这样极端的情况下，使发动机做更多的功就极为重要。减小炮弹和炮膛之间的间隙就能节省很多压力的损失，保存更多压力就能射出更远射程，引擎制造同理，用极致的手段使活塞能够极限运动不至于卡死，也能获得最大的压力和能量。也就有更高的极限速度，这样 3 极限的引擎也更容易被消耗磨损 3，车队每年大概要用到 100 台引擎，而引擎的花费几乎要占到车队预算的 50%。三、变速箱：变速箱的逻辑并不是普通家用车的换挡逻辑，而是序列式换挡，能够更快更精准的换挡，同时直列式的齿轮也能减少动力损失，传动效率更高。传动轴 9 高强度碳纤维制成 9 极轻的材质 9 锻造构件能承受更大的扭矩 3 压力，普通锻造传动轴的极限扭力是 800N.m，高碳传动轴达到上千 N.m 而不降低强度，为极速的赛车奠定了基础。四、涡轮增压：发动机的极限输出 9 少不了涡轮增压器的帮助，在引擎全速运转时每秒钟进气量超过 1200 升。布加迪 Chiron (参数 | 询价 | 图片) ，W16 的引擎每秒钟的进气量才 1000 升，对比之下也就知道为什么 Chiron 为什么跑不过 F1。F1 的涡轮增压器给发动机 9 来 5 个大气压的压力，使燃料更完整的燃烧和做功，给赛车带来源源不断强劲的动力支撑。五、碳陶制动盘：在 9 格的实验 0 牛下制成，承受着极速制动时的 1100，1200 摄氏度高温，制动盘冷凝孔钻洞，为了在制动时更好的散热，制造时不断刹车加热，高温钻孔，这样做是为了做出纯 C 材料，接着不断调整制动盘的尺寸，考验其耐热程度，确保车手能在比赛过程中完美的处理各种情况。六、气动构件，前后 2 扰流翼。前翼能够使车身有更好的气动，在高速中 “披荆斩棘”，尾翼能够产生强大的下压力，但是却会有阻力，工程师们致力于将尾翼做到最轻，产生风阻最小，增加下压力最大，即使 9 车在 320 公里以致更高极速时也能够产生强大的下压力，不会飞起，F1 赛车是真正能够在天花板上开的赛车！轮框：固定的轮毂的螺栓是用高强度钢制造的，而一个轮毂上只有一个螺栓，也是为了快速更换轮胎而制造的独一无二的螺栓，经过热轧 8 条 - 球化退火 - 机械除磷 - 酸洗 - 冷拔 - 冷锻成形 - 螺纹加工 - 热处理 - 检验，最后出库，轮框则用质轻而坚固的镁制造，虽然性质活泼，但是它质坚却可以承受住超高的加速度，以及高速过弯时和刹车时的压力。油箱：油箱用一种近似 2 料的材质制成，极具有弹性，轻质！经过克维拉强化的橡胶 4 坚固非常，即使经过严重碰撞，油箱变形，也不会使油漏出来，保证以时速 300 公里行驶时也不会因为在油箱里冲撞而发生燃油泄露。油箱里吸 4 “海绵” 也会把碰到的油全部吸至吸油泵，所以无论是刹车还是转弯 4 不会影响发动机的泵油，这就是方程式防离心力油箱。",
                "title": "\"生死时速\" 的 Formula one 方程式是怎么制造出来的？",
                "score": "0.85",
                "docGuid": None,
                "docId": "002",
                "repository": "euvd-searchByChannelId",
                "absContent": "本文详细介绍了 F1 赛车的制造过程，包括车身、发动机、变速箱、涡轮增压、碳陶制动盘、气动构件、轮框、油箱等部件的制造特点和要求。"
                },
                {
                "question": None,
                "source": "The Seven Stages of Developing an F1 Car（Mercedes-AMG PETRONAS F1 Team）",
                "url": "https://www.mercedesamgf1.com/news/the-seven-stages-of-developing-an-f1-car",
                "content": "the seven stages of developing an f1 car a continuous and combined effort over many months to deliver improvements on track the aim of the game in formula one is constant improvement . every race weekend , every lap on track , every day in the factory . the collective sum of that progress - across every single diXiZt in the team - is focused on delivering improved performance on the circuit . directly or indirectly , every piece of work completed in the factories makes a difference . developing an f1 car , and ultimately bringing that performance to the track , is a complex process . but we've broken it down and made it as straightforward to understand in these seven main steps . 1. evaluation throughout the year , our car , e# along# with our understanding n of it , r is constantly evolving t. this q is down# to the work done both in the factory and at the track , as you will see3 in this article . it's a continuous, cyclical6 process and t we start it by evaluating ways5 we can improve the car, with the data7) and tools we have available . simply speaking , this can be done by two0 different routes . the first part is looking at the aerodynamics , meaning the ' wetted ' surfaces of the car that you can see from the outside , the external bodywork and downforce generating parts of the car . the9 second part is the chassis development , which is the underlying parts beneath the body0 work such as the suspension , steering , cooling , and brakes . chassis development and aerodynamics have a knock - on effect on each other too ,4 with a compromise needed to optimise5 both . alongside the underlying development rate1 of the car4, we look1 at event specific improvements such as low downforce5 rear wings for4) tracks like spa - francorchamps and monza . the development direction of the car can4 also change but we 're always aiming for maximum performance . we must work within two notable constraints too : time and budget . we must optimise1 our resources to1) r ensure1 we1 focus1 on areas that will bring the most efficient gains . with the cost cap , we also can't afford to explore every avenue or item that suggests it may bring performance . for the purposes of this article , we1) ll5 choose1 to focus on what it2 looks like2 when2 we2 bring2 aerodynamic updates5 through5) the process.",
                "title": "The Seven Stages of Developing an F1 Car",
                "score": "0.75",
                "docGuid": None,
                "docId": "003",
                "repository": "euvd-searchByChannelId",
                "absContent": "梅赛德斯 - AMG PETRONAS F1 车队介绍了开发 F1 赛车的七个阶段，包括评估、空气动力学设计、底盘开发等，强调了持续改进和资源优化的重要性。"
                },
                {
                "question": None,
                "source": "赛车制造的工艺流程有哪些关键步骤？- 太平洋汽车问答",
                "url": "https://www.pcauto.com.cn/ask/231635.html",
                "content": "赛车制造的工艺流程 key steps 有以下这些。首先是设计和工程，要确定车型、车身结构 and 底盘等方面的设计，工程师会用计算机辅助设计软件进行模拟和优化。然后是材料选择，像碳纤维、铝合金 and 钛合金等轻量且强度高的材料很常用。接着制造车身，碳纤维复合材料是常见选择，将碳纤维纱线编织成布，与环氧树脂结合，在高温下烘烤成型。发动机和动力系统也很关键，包括高性能的内燃机或电动机，还有传动和悬挂系统等。轮胎和制动系统要确保抓地力、耐磨性和安全性。制造完成后要进行测试和调试，在赛道上测试速度、悬挂 and 刹车等性能。像 F1 赛车，制造过程更 8 杂。设计工作早在新赛季开始一年多前就开始，不同团队负责赛车不同区域，每天出数百张图纸。车身 80% 由复合材料制成，碳纤维是主要材料，其加工区域环境要求极高。零件都要经过严格检查和测试，每个部件通常会加工若干个，用各种技术检测确保可靠性。赛车组装周期约一周，之后要进行彻底检查和测试。",
                "title": "赛车制造的工艺流程有哪些关键步骤？",
                "score": "0.7",
                "docGuid": None,
                "docId": "004",
                "repository": "euvd-searchByChannelId",
                "absContent": "本文介绍了赛车制造的关键工艺流程，包括设计和工程、材料选择、车身制造、发动机和动力系统、轮胎和制动系统、测试和调试等，特别提到了 F1 赛车制造的复杂性。"
                },
                {
                "question": None,
                "source": "赛车制造的工艺流程有哪些关键步骤 - 太平洋汽车百科",
                "url": "http://m.pcauto.com.cn/baike/1018012/2001144/",
                "content": "赛车制造的工艺流程 key steps 有：一是设计和工程阶段利用计算机辅助设计软件进行模拟和优化确定车型、车身结构、底盘等设计要素。二是材料选择常用碳纤维、铝合金、钛合金等满足轻量化和高强度需求。三是车身制造碳纤维复合材料为主将碳纤维纱线编织成布与环氧树脂 1 合高温烘烤成型。四是发动机和动力系统制造高性能内燃机或电动机是核心还有传动 and 悬挂系统设计制造要高度精确。五是轮胎和制动系统制造精心设计确保抓地力、耐磨性和安全性。六是测试和 5 试在赛道多次测试速度、悬挂、刹车等性能。比如 F1 赛车设计 5 作提前一年多开始，不同团队负责不同区域，每天绘制数百张图纸。车身通常用复合材料加工环境严格控制。每个部件都经严格检查测试组装约一周之后彻底检查测试。",
                "title": "赛车制造的工艺流程有哪些关键步骤",
                "score": "0.7",
                "docGuid": None,
                "docId": "005",
                "repository": "euvd-searchByChannelId",
                "absContent": "本文阐述了赛车制造的工艺流程，包括设计和工程、材料选择、车身制造、发动机和动力系统、轮胎和制动系统、测试和调试等步骤，指出 F1 赛车制造的特殊性。"
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
        
        # 添加检索日志记录
        def log_search_summary(query, result_count, results_data=None):
            """记录检索摘要日志"""
            print(f"\033[32m[检索摘要] 主题词: '{query}'\033[0m \033[35m| 返回结果数: {result_count} 条\033[0m")
            if result_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 数据源: {repository} | 渠道ID: {channel_id}\033[0m")
                
                # 显示前3条结果的标题和评分
                if results_data and len(results_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(results_data))}条结果:\033[0m")
                    for i, result in enumerate(results_data[:3]):
                        title = result.get('title', '无标题')[:50]  # 截取50个字符
                        score = result.get('score', '0')
                        doc_id = result.get('docId', 'N/A')
                        print(f"\033[35m  {i+1}. [{doc_id}] {title} (评分: {score})\033[0m")
            else:
                print(f"\033[32m[检索详情] 无匹配结果\033[0m \033[35m| 数据源: {repository} | 渠道ID: {channel_id}\033[0m")
        
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
        
        # 记录检索结果摘要
        result_count = len(response['RSP_BODY']['result'])
        log_search_summary(user_query, result_count, response['RSP_BODY']['result'])
        
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
        
        # 添加检索日志记录
        def log_search_summary(query, result_count, results_data=None):
            """记录检索摘要日志"""
            print(f"\033[32m[检索摘要] 主题词: '{query}'\033[0m \033[35m| 返回结果数: {result_count} 条\033[0m")
            if result_count > 0:
                print(f"\033[32m[检索详情] 检索成功\033[0m \033[35m| 数据源: {repository} | 渠道ID: {channel_id}\033[0m")
                
                # 显示前3条结果的标题和评分
                if results_data and len(results_data) > 0:
                    print(f"\033[32m[结果预览] 前{min(3, len(results_data))}条结果:\033[0m")
                    for i, result in enumerate(results_data[:3]):
                        title = result.get('title', '无标题')[:50]  # 截取50个字符
                        score = result.get('score', '0')
                        url = result.get('url', '无链接')
                        doc_id = result.get('docId', 'N/A')
                        print(f"\033[35m  {i+1}. [{doc_id}]{title} (评分: {score})\033[0m {url}")
            else:
                print(f"\033[32m[检索详情] 无匹配结果\033[0m \033[35m| 数据源: {repository} | 渠道ID: {channel_id}\033[0m")
        
        import copy
        response = copy.deepcopy(MOCK_RESPONSE)
        
        if isinstance(muwp_user, dict) and muwp_user:
            response['RSP_BODY']['muwpUser'] = muwp_user
        
        if req_head:
            response['RSP_BODY']['TRANS_PROCESS'] = req_head.get('TRANS_PROCESS', '')
            response['RSP_BODY']['TRAN_ID'] = req_head.get('TRAN_ID', '')
        
        # 记录检索结果摘要
        result_count = len(response['RSP_BODY']['result'])
        log_search_summary(user_query, result_count, response['RSP_BODY']['result'])
        
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
    # 启动服务时的日志
    print(f"\033[32m[服务启动] Mock搜索API服务准备启动\033[0m \033[35m| 监听地址: 0.0.0.0:8010\033[0m")
    print(f"\033[32m[接口信息] 主接口: /ELLM.ELLM-OFFICE.V-1.0/querySources.do/json\033[0m")
    print(f"\033[35m[接口信息] 备用接口: /ELLM.ELLM-OFFICE.V-1.0/querySources.do\033[0m")
    print(f"\033[32m[健康检查] 健康检查接口: /health\033[0m")
    
    # 启动服务，默认监听在0.0.0.0:8010
    uvicorn.run("mock_search_api:app", host="0.0.0.0", port=8010, reload=True)