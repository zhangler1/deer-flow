# _verify_langfuse.py_
import os
import logging
from langfuse import observe  # v3 导入方式 - @observe 装饰器自动捕获输入输出

# Read from environment variables
# Ensure these are set in your environment:
# export LANGFUSE_PUBLIC_KEY="your_public_key"
# export LANGFUSE_SECRET_KEY="your_secret_key"
# export LANGFUSE_BASE_URL="https://cloud.langfuse.com"  # optional, defaults to cloud.langfuse.com
# export LANGFUSE_TRACING_ENVIRONMENT="default"  # optional

# Verify required environment variables are set
if not os.getenv("LANGFUSE_PUBLIC_KEY"):
    raise ValueError("LANGFUSE_PUBLIC_KEY environment variable is not set")
if not os.getenv("LANGFUSE_SECRET_KEY"):
    raise ValueError("LANGFUSE_SECRET_KEY environment variable is not set")

logging.getLogger("langfuse").setLevel(logging.DEBUG)

@observe(name="Demo Function", as_type="chain")  # v3: 装饰器会自动捕获输入输出
def demo():
    """v3 中 @observe 装饰器会自动记录一切，无需手动调用任何方法"""
    return "hello"

print("Running demo...")
demo()
print("Done! Check Langfuse dashboard for traces.")