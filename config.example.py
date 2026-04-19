"""本地配置示例文件。

复制为仓库根目录下的 config.local.py 后即可本地覆盖默认配置。
"""
# ====================== 基础应用配置 ======================
app_name = "AI互动智课后端服务"
app_version = "0.1.0"
api_prefix = "/api/v1"
debug = True
signature_enabled = False

# ====================== 数据库配置（二选一） ======================
db_url = None
db_host = "10.195.20.215"
db_port = 3306
db_user = "Zenith"
db_password = "123456"
db_name = "chaoxing_ai_course"
db_echo = False

# ====================== 教师端 LLM 配置 ======================
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-local-key"
llm_model = "gpt-5.1-codex-mini"
llm_timeout_seconds = 60.0

# 向量数据库（pgvector）配置
vector_db_url = "postgresql+psycopg://postgres:你的密码@127.0.0.1:5433/chaoxing_ai_vector"
# 火山引擎鉴权
APPID = "从火山引擎控制台获取"
ACCESS_TOKEN = "从火山引擎控制台获取" 

# 语音合成配置(火山引擎)
TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
TTS_CLUSTER = "volcano_tts"
TTS_VOICE_TYPE = "zh_male_M392_conversation_wvae_bigtts"

# 语音识别配置(火山引擎一句话识别60s)
ASR_URL = "wss://openspeech.bytedance.com/api/v2/asr"
ASR_CLUSTER = "从火山引擎控制台获取"

# ====================== 学生端 RAG/问答配置s ======================
# 通义千问（DashScope）配置
qa_llm_provider = "dashscope"
qa_llm_model = "qwen-max"
qa_embedding_model = "text-embedding-v4"
qa_embedding_dimensions = 1024
dashscope_api_key = "你的阿里云API Key"
dashscope_base_url = "https://dashscope.aliyuncs.com"



