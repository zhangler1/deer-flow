# 系统背景注入 - 快速参考

## 🎯 核心变化（一句话）

**重构前**: API层直接修改用户消息  
**重构后**: 通过State传递，在Prompt Template中按需使用

## 📋 对比速查

| 方面 | 重构前 ❌ | 重构后 ✅ |
|-----|----------|---------|
| **用户消息** | 被修改污染 | 保持原始纯净 |
| **智能路由** | 基于污染数据 | 基于原始问题 |
| **API职责** | 修改业务逻辑 | 只传递参数 |
| **灵活性** | 硬编码格式 | 节点按需使用 |

## 🔄 数据流

```
用户消息 → State.system_context → 各节点Prompt Template
         ↓                        ↓
         保持原始                 按需使用
```

## 🎨 各节点使用建议

| 节点 | 使用背景？ | 原因 |
|-----|----------|------|
| **Router** | ❌ 不使用 | 需要基于原始问题分类 |
| **Coordinator** | ✅ 使用 | 理解业务背景决定流程 |
| **Planner** | ✅ 使用 | 制定针对性计划 |
| **Researcher** | ✅ 使用 | 执行领域搜索 |
| **Reporter** | ✅ 使用 | 撰写相关报告 |

## 💻 代码示例

### API层（已修改）

```python
# ✅ 只传递，不修改
if system_context:
    enhanced_logger.logger.info(
        f"🏛️ SYSTEM_CONTEXT | 系统背景已配置: {system_context}"
    )

workflow_input = {"system_context": system_context}
```

### Prompt Template（推荐）

```markdown
<!-- coordinator.md -->
{% if system_context %}
**系统背景**: {{ system_context }}
{% endif %}

**用户查询**: {{ research_topic }}
```

### 节点代码（可选）

```python
def coordinator_node(state: State, config: RunnableConfig):
    context = state.get("system_context", "")
    query = state.get("research_topic", "")
    
    # 在Prompt中使用
    messages = apply_prompt_template("coordinator", state, config)
```

## ✅ 验证清单

- [x] API层不修改用户消息
- [x] Router基于原始问题分类
- [x] 背景通过State传递
- [ ] Prompt模板包含背景引用（可选）
- [ ] 测试各路径正常工作

## 📚 相关文档

- [详细重构说明](./CONTEXT_INJECTION_REFACTOR.md)
- [系统背景分析](./SYSTEM_CONTEXT_ANALYSIS.md)

---

**最后更新**: 2025-01-05
