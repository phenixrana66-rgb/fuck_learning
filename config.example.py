"""本地配置示例文件。
复制为仓库根目录下的 config.local.py 后即可本地覆盖默认配置。 
环境变量优先级更高；如果同时设置了 A12_* 环境变量，将覆盖这里的值。
"""
# ====================== 基础应用配置 ======================
app_name = "AI互动智课后端服务"
app_version = "0.1.0"
api_prefix = "/api/v1"
debug = True
signature_enabled = False

# ====================== 数据库配置（二选一） ======================
db_url = None
db_host = "127.0.0.1"
db_port = 3306
db_user = "your_db_user"
db_password = "your_db_password"
db_name = "chaoxing_ai_course"
db_echo = False

# ====================== 教师端 LLM 配置 ======================
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-local-key"
llm_model = "gpt-5.1-codex-mini"
llm_timeout_seconds = 60.0

# ====================== 学生端 RAG/问答配置s ======================
# 通义千问（DashScope）配置
qa_llm_provider = "dashscope"
qa_llm_model = "qwen-max"
qa_embedding_model = "text-embedding-v4"
qa_embedding_dimensions = 1024
dashscope_api_key = "你的阿里云API Key"
dashscope_base_url = "https://dashscope.aliyuncs.com"


# 向量数据库（pgvector）配置
vector_db_url = "postgresql+psycopg://postgres:你的密码@127.0.0.1:5433/chaoxing_ai_vector"