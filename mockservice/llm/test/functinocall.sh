echo -e "\033[32m=== 测试 Function Call 功能 ===\033[0m" && curl -X POST http://192.168.0.106:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-0.6",
    "messages": [{"role": "user", "content": "请帮我查询北京的天气"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取天气信息",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "城市名称"
              }
            },
            "required": ["location"]
          }
        }
      }
    ],
    "tool_choice": "auto"
  }' 2>/dev/null | python3 -m json.tool