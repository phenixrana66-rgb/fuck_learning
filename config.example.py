"""本地配置示例文件。

复制为仓库根目录下的 config.local.py 后即可本地覆盖默认配置。
环境变量优先级更高；如果同时设置了 A12_* 环境变量，将覆盖这里的值。
"""

app_name = "AI互动智课后端服务"
app_version = "0.1.0"
api_prefix = "/api/v1"
debug = True
signature_enabled = False

# 数据库配置：可二选一
db_url = None
db_host = "10.195.20.215"
db_port = 3306
db_user = "your_db_user"
db_password = "your_db_password"
db_name = "chaoxing_ai_course"
db_echo = False

# LLM 配置
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-local-key"
llm_model = "gpt-5.1-codex-mini"
llm_timeout_seconds = 60.0
