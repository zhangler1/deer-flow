curl -v http://192.168.0.106:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-0.6",
    "messages": [{"role": "user", "content": "什么是机器学习？"}],
    "temperature": 0.6,
    "max_tokens": 100,
    "stream": false
  }'



  curl -v http://192.168.0.106:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sdf" \
  -d '{
    "model": "qwen3-0.6",
    "messages": [{"role": "user", "content": "什么是机器学习？"}],
    "temperature": 0.6,
    "max_tokens": 100,
    "stream": true
  }'

    curl -v http://192.168.0.106:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sdf" \
  -d '{
    "model": "qwen3-0.6",
    "messages": [{"role": "user", "content": "什么是机器学习？"}],
    "temperature": 0.6,
    "max_tokens": 100
  }'