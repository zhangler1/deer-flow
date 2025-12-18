# _verify_langfuse.py_
import os, time, logging
from langfuse import get_client, observe  # v3 导入方式

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

# Langfuse 3.x 使用 get_client() 客户端初始化
lf = get_client()
print("Auth:", lf.auth_check())

@observe(as_type="chain")  # creates a trace + span
def demo():
    return "hello"

demo()

# Important in scripts/serverless
lf.flush()
time.sleep(1)
print("Done")