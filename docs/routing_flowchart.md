# DeerFlow 智能路由系统流程图

## 整体架构流程

```mermaid
graph TB
    Start([用户查询]) --> Router{智能路由分类器<br/>RouteDecision}
    
    Router -->|path=direct_answer<br/>complexity=simple<br/>needs_search=false| DirectAnswer[直接回答节点<br/>direct_answer_node]
    
    Router -->|path=simple_search<br/>complexity=medium<br/>needs_search=true| SimpleSearch[简单检索节点<br/>simple_search_node<br/>⭐主流路径]
    
    Router -->|path=deep_research<br/>complexity=complex<br/>needs_search=true| DeepResearch[深度研究入口<br/>coordinator]
    
    Router -->|path=domain_knowledge<br/>complexity=expert<br/>needs_search=true| DomainKnow[领域知识节点<br/>domain_knowledge_node]
    
    DirectAnswer --> End1([返回结果])
    SimpleSearch --> End2([返回结果])
    DomainKnow --> End4([返回结果])
    
    DeepResearch --> BgInv[背景调研<br/>background_investigator]
    BgInv --> Planner[规划者<br/>planner]
    Planner --> HumanFb{人工反馈<br/>human_feedback}
    HumanFb -->|接受计划| ResTeam[研究团队<br/>research_team]
    HumanFb -->|修改计划| Planner
    ResTeam --> Researcher[研究者<br/>researcher]
    Researcher --> Reporter[报告者<br/>reporter]
    Reporter --> End3([返回报告])
    
    style Router fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style SimpleSearch fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style DirectAnswer fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    style DomainKnow fill:#f8bbd0,stroke:#c2185b,stroke-width:2px
    style DeepResearch fill:#d1c4e9,stroke:#5e35b1,stroke-width:2px
```

## 路由分类决策树

```mermaid
graph TD
    Q[用户查询] --> C1{是否为<br/>通用常识?}
    
    C1 -->|是<br/>如:什么是汽车| DA[direct_answer<br/>直接回答<br/>不走检索]
    
    C1 -->|否| C2{是否为<br/>银行业务<br/>常规查询?}
    
    C2 -->|是<br/>如:信用卡申请| SS[simple_search<br/>简单检索<br/>单次检索⭐]
    
    C2 -->|否| C3{是否需要<br/>深度分析<br/>研究?}
    
    C3 -->|是<br/>如:趋势分析| DR[deep_research<br/>深度研究<br/>多轮研究]
    
    C3 -->|否| C4{是否为<br/>高度专业<br/>知识?}
    
    C4 -->|是<br/>如:SWIFT规则| DK[domain_knowledge<br/>领域知识<br/>专业库]
    
    C4 -->|否| Default[默认走<br/>simple_search]
    
    style DA fill:#fff9c4
    style SS fill:#c8e6c9
    style DR fill:#d1c4e9
    style DK fill:#f8bbd0
```

## 4种路径详细流程

### 路径1: 直接回答 (direct_answer)

```mermaid
graph LR
    A[用户查询:<br/>什么是汽车?] --> B[Router<br/>分类]
    B --> C{分类结果}
    C --> D[path=direct_answer<br/>complexity=simple<br/>needs_search=false]
    D --> E[direct_answer_node]
    E --> F[调用LLM<br/>使用通用知识]
    F --> G[生成答案<br/>不超过300字]
    G --> H[返回结果]
    
    style A fill:#e3f2fd
    style D fill:#fff9c4
    style E fill:#fff9c4
    style H fill:#c8e6c9
```

**特点:**
- ⚡ 最快速度（不走检索）
- 📚 使用LLM通用知识
- 🎯 适合基础概念问题

### 路径2: 简单检索 (simple_search) - 主流路径

```mermaid
graph LR
    A[用户查询:<br/>信用卡如何申请?] --> B[Router<br/>分类]
    B --> C{分类结果}
    C --> D[path=simple_search<br/>complexity=medium<br/>needs_search=true]
    D --> E[simple_search_node]
    E --> F[单次检索<br/>3-5条结果]
    F --> G[结合检索结果<br/>调用LLM]
    G --> H[生成答案<br/>不超过300字]
    H --> I[返回结果]
    
    style A fill:#e3f2fd
    style D fill:#c8e6c9
    style E fill:#c8e6c9
    style I fill:#c8e6c9
```

**特点:**
- ⭐ **主流路径**（65%查询）
- 🔍 单次检索，快速响应
- 🏦 专为银行业务优化

### 路径3: 深度研究 (deep_research)

```mermaid
graph TB
    A[用户查询:<br/>分析金融科技趋势] --> B[Router<br/>分类]
    B --> C{分类结果}
    C --> D[path=deep_research<br/>complexity=complex<br/>needs_search=true]
    D --> E[coordinator<br/>协调者]
    E --> F[background_investigator<br/>背景调研]
    F --> G[planner<br/>制定计划]
    G --> H{human_feedback<br/>审核计划}
    H -->|接受| I[research_team<br/>研究团队]
    H -->|修改| G
    I --> J[researcher<br/>执行研究步骤]
    J --> K{是否完成?}
    K -->|否| J
    K -->|是| L[reporter<br/>生成报告]
    L --> M[返回详细报告<br/>800-2000字]
    
    style A fill:#e3f2fd
    style D fill:#d1c4e9
    style E fill:#d1c4e9
    style M fill:#c8e6c9
```

**特点:**
- 🔬 最完整的研究流程
- 📊 多轮迭代，深度分析
- 📄 生成详细报告

### 路径4: 领域知识 (domain_knowledge)

```mermaid
graph LR
    A[用户查询:<br/>SWIFT报文MT103规则] --> B[Router<br/>分类]
    B --> C{分类结果}
    C --> D[path=domain_knowledge<br/>complexity=expert<br/>needs_search=true]
    D --> E[domain_knowledge_node]
    E --> F{是否有<br/>本地知识库?}
    F -->|是| G[查询知识库<br/>retriever_tool]
    F -->|否| H[网络搜索<br/>专业模式]
    G --> I[调用LLM<br/>详细解答]
    H --> I
    I --> J[生成答案<br/>400-600字]
    J --> K[返回结果]
    
    style A fill:#e3f2fd
    style D fill:#f8bbd0
    style E fill:#f8bbd0
    style K fill:#c8e6c9
```

**特点:**
- 🎓 高度专业化
- 📚 优先使用知识库
- 📝 详细的专业解答

## 分类器内部逻辑

```mermaid
graph TB
    Start[用户查询] --> Check1{智能路由<br/>是否启用?}
    
    Check1 -->|否| Default[返回simple_search<br/>默认主流路径]
    
    Check1 -->|是| LLM[LLM智能分类]
    
    LLM --> Success{LLM<br/>分类成功?}
    
    Success -->|是| Validate[验证RouteDecision]
    Success -->|否| Fallback[规则后备分类]
    
    Validate --> Return1[返回分类结果]
    
    Fallback --> Rule1{检查<br/>通用常识<br/>关键词}
    
    Rule1 -->|匹配| R1[direct_answer]
    Rule1 -->|不匹配| Rule2{检查<br/>领域知识<br/>关键词}
    
    Rule2 -->|匹配| R2[domain_knowledge]
    Rule2 -->|不匹配| Rule3{检查<br/>研究分析<br/>关键词}
    
    Rule3 -->|匹配| R3[deep_research]
    Rule3 -->|不匹配| Rule4{检查<br/>银行业务<br/>关键词}
    
    Rule4 -->|匹配| R4[simple_search]
    Rule4 -->|不匹配| R5[默认simple_search]
    
    R1 --> Return2[返回分类结果]
    R2 --> Return2
    R3 --> Return2
    R4 --> Return2
    R5 --> Return2
    
    Default --> End([结束])
    Return1 --> End
    Return2 --> End
    
    style LLM fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    style Fallback fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px
```

## 典型查询示例流程

### 示例1: "什么是汽车？"

```mermaid
sequenceDiagram
    participant U as 用户
    participant R as Router
    participant C as Classifier
    participant N as direct_answer_node
    participant L as LLM
    
    U->>R: "什么是汽车？"
    R->>C: classify_request()
    C->>C: 检测通用常识关键词
    C-->>R: path=direct_answer
    R->>N: 路由到direct_answer_node
    N->>L: 调用LLM（不走检索）
    L-->>N: 生成通用知识答案
    N-->>U: 返回答案（<1秒）
```

### 示例2: "信用卡如何申请？"

```mermaid
sequenceDiagram
    participant U as 用户
    participant R as Router
    participant C as Classifier
    participant N as simple_search_node
    participant S as Search Tool
    participant L as LLM
    
    U->>R: "信用卡如何申请？"
    R->>C: classify_request()
    C->>C: 检测银行业务关键词
    C-->>R: path=simple_search
    R->>N: 路由到simple_search_node
    N->>S: 单次检索（3条结果）
    S-->>N: 返回检索结果
    N->>L: 结合检索结果调用LLM
    L-->>N: 生成答案
    N-->>U: 返回答案（2-3秒）
```

### 示例3: "分析金融科技对传统银行的影响"

```mermaid
sequenceDiagram
    participant U as 用户
    participant R as Router
    participant C as Classifier
    participant Co as Coordinator
    participant P as Planner
    participant Re as Researcher
    participant Rep as Reporter
    
    U->>R: "分析金融科技..."
    R->>C: classify_request()
    C->>C: 检测研究分析关键词
    C-->>R: path=deep_research
    R->>Co: 路由到coordinator
    Co->>P: 制定研究计划
    P->>Re: 执行研究步骤
    Re->>Re: 多轮检索和分析
    Re->>Rep: 生成最终报告
    Rep-->>U: 返回详细报告（30-60秒）
```

## 性能对比流程

### 改造前的流程（3路径）

```mermaid
graph LR
    Q1[什么是汽车?] --> R1[Router]
    R1 --> S1[simple_qa_node]
    S1 --> Search1[调用检索❌]
    Search1 --> End1[返回<br/>较慢]
    
    style Search1 fill:#ffcdd2
```

**问题:** 通用问题也走检索，浪费资源

### 改造后的流程（4路径）

```mermaid
graph LR
    Q2[什么是汽车?] --> R2[Router]
    R2 --> D2[direct_answer_node]
    D2 --> LLM2[直接LLM✅]
    LLM2 --> End2[返回<br/>快速]
    
    style LLM2 fill:#c8e6c9
```

**优化:** 直接回答，节省检索成本

## 监控和日志流程

```mermaid
graph TB
    Query[用户查询] --> Logger1[📝 记录查询]
    Logger1 --> Classifier[分类器]
    
    Classifier --> Logger2[📝 记录分类决策<br/>path/complexity/confidence]
    
    Logger2 --> Route[路由到节点]
    
    Route --> Node1[direct_answer]
    Route --> Node2[simple_search]
    Route --> Node3[deep_research]
    Route --> Node4[domain_knowledge]
    
    Node1 --> Logger3[📝 记录执行时间]
    Node2 --> Logger3
    Node3 --> Logger3
    Node4 --> Logger3
    
    Logger3 --> Response[返回结果]
    Response --> Logger4[📝 记录结果质量]
    
    Logger4 --> Metrics[📊 性能指标<br/>- 响应时间<br/>- 路径分布<br/>- 成功率]
    
    style Logger1 fill:#e3f2fd
    style Logger2 fill:#e3f2fd
    style Logger3 fill:#e3f2fd
    style Logger4 fill:#e3f2fd
    style Metrics fill:#c8e6c9
```

## 总结

### 4种路径的典型特征

| 路径 | 响应时间 | 检索次数 | 答案长度 | 使用频率 |
|------|----------|----------|----------|----------|
| direct_answer | <1s | 0 | 100-300字 | 10% |
| simple_search | 2-3s | 1次 | 200-300字 | **65%** ⭐ |
| deep_research | 30-60s | 多次 | 800-2000字 | 15% |
| domain_knowledge | 3-5s | 1次 | 400-600字 | 10% |

### 关键设计原则

1. **效率优先** - 简单问题快速处理
2. **准确为本** - 复杂问题深度分析
3. **专业保障** - 领域知识精准解答
4. **智能路由** - 自动选择最优路径

---

**流程图版本:** v2.0  
**更新日期:** 2025-11-04  
**状态:** ✅ 已完成
