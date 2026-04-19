# fuck_learning

## 1. 先安装这些软件

- Node.js 18+
- npm 9+
- Python 3.11+
- MySQL 8.x
- PostgreSQL 客户端
- Docker Desktop

## 2. 拉代码后先进入项目目录

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
```

## 3. 安装前后端依赖

前端：

```powershell
npm install
```

后端：

```powershell
pip install -r requirements.txt
```

如果你使用 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. 初始化 MySQL 业务库

创建数据库：

```sql
CREATE DATABASE chaoxing_ai_course DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

导入表结构：

```powershell
mysql -h 10.195.20.215 -P 3306 -u Zenith -p chaoxing_ai_course < ".\docs\mysql建表.sql"
```

导入测试数据：

```powershell
mysql -h 10.195.20.215 -P 3306 -u Zenith -p chaoxing_ai_course < ".\docs\init_test_data.sql"
```

## 5. 安装 PostgreSQL 客户端

Windows 安装 PostgreSQL 后，确保 `psql` 可以直接执行。

检查：

```powershell
psql --version
```

## 6. 连接共享向量数据库

数据库信息：

```text
host=10.199.6.229(后续端口号可能更改)
port=5433
database=chaoxing_ai_vector
user=vector_reader
password=123456
```

直接连接：

```powershell
psql "postgresql://vector_reader:123456@10.199.6.229:5433/chaoxing_ai_vector?sslmode=disable"
```

连接后查看向量表：

```
\dt
SELECT COUNT(*) FROM qa_vector_chunks;
```
退出：

```
\q
```
## 7. 配置本地配置文件

先复制一份 `config.example.py`，命名为 `config.local.py`

把 `config.local.py` 里的数据库配置改成下面这些值。

MySQL：

```python
db_host = "10.195.20.215"
db_port = 3306
db_user = "Zenith"
db_password = "123456"
db_name = "chaoxing_ai_course"
```

向量库：

```python
vector_db_url = "postgresql+psycopg://vector_reader:123456@10.199.6.229:5433/chaoxing_ai_vector"
```

教师端大语言模型：

```python
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-local-key"
llm_model = "gpt-5.1-codex-mini"
```

学生端问答 / embedding / ASR：

```python
qa_llm_provider = "dashscope"
qa_llm_model = "qwen-max"
qa_embedding_model = "text-embedding-v4"
qa_embedding_dimensions = 1024
dashscope_api_key = "你的千问 API Key"
dashscope_base_url = "https://dashscope.aliyuncs.com"
```

如果启用火山引擎语音：

```python
APPID = "你的 APPID"
ACCESS_TOKEN = "你的 ACCESS_TOKEN"
TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
TTS_CLUSTER = "volcano_tts"
TTS_VOICE_TYPE = "zh_male_M392_conversation_wvae_bigtts"
ASR_URL = "wss://openspeech.bytedance.com/api/v2/asr"
ASR_CLUSTER = "你的 ASR_CLUSTER"
```

## 8. 前端环境变量保持默认即可

`.env.development` 默认值：

```text
VITE_API_BASE=
VITE_STUDENT_API_BASE=/student-api
VITE_STATIC_KEY=chaoxing-ai-static-key
```

## 9. 正确启动顺序

按这个顺序执行：

1. 启动 MySQL
2. 确认 PostgreSQL 客户端已安装
3. 确认 `10.199.6.229:5433` 可连接
4. 确认 `config.local.py` 已配置
5. 启动后端
6. 启动前端

## 10. 启动后端

脚本方式：

```powershell
.\start-backend.ps1
```

脚本实际等价于：

```powershell
$env:A12_DB_HOST = "10.195.20.215"
$env:A12_DB_PORT = "3306"
$env:A12_DB_USER = "Zenith"
$env:A12_DB_PASSWORD = "123456"
$env:A12_DB_NAME = "chaoxing_ai_course"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

手动启动方式：

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

后端启动后访问：

```text
http://127.0.0.1:3001/docs
```

## 11. 启动前端

脚本方式：

```powershell
.\start-frontend.ps1
```

脚本实际等价于：

```powershell
npm run dev:web
```

手动启动方式：

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

前端启动后访问：

```text
http://127.0.0.1:5173/
```

## 12. 常用访问地址

门户页：

```text
http://127.0.0.1:5173/
```

学生首页：

```text
http://127.0.0.1:5173/student/home?token=student_demo_token_001
```

教师登录页：

```text
http://127.0.0.1:5173/teacher/login
```

后端 Swagger：

```text
http://127.0.0.1:3001/docs
```

## 13. 向量库连接信息

给对方这些值：

```text
host=10.199.6.229
port=5433
database=chaoxing_ai_vector
user=vector_reader
password=123456
```

完整连接串：

```text
postgresql+psycopg://vector_reader:123456@10.199.6.229:5433/chaoxing_ai_vector
```

## 14. 最短执行清单

```text
1. 安装 Node.js、Python、MySQL、PostgreSQL 客户端、Docker Desktop
2. npm install
3. pip install -r requirements.txt
4. 创建 MySQL 库 chaoxing_ai_course
5. 导入 docs/mysql建表.sql
6. 导入 docs/init_test_data.sql
7. 确认可连接 10.199.6.229:5433
8. 用 psql 连接 chaoxing_ai_vector
9. 配置 config.local.py
10. 配置 DashScope / LLM / 语音相关 API
11. 启动后端
12. 启动前端
13. 打开 http://127.0.0.1:5173/
```
