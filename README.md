# fuck_learning

## 初次使用

### 1. 安装软件
- Node.js 18+
- npm 9+
- Python 3.11+
- MySQL 客户端
- PostgreSQL 客户端（要能执行 `psql`）
- Docker Desktop

### 2. 进入项目
```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
```

### 3. 安装依赖
前端：
```powershell
npm install
```

后端：
```powershell
pip install -r requirements.txt
```

如果使用虚拟环境：
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 初始化 MySQL
数据库信息：
```text
host=10.195.20.215
port=3306
user=Zenith
password=123456
database=chaoxing_ai_course
```

建库：
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

### 5. 连接向量数据库
先确认 `psql` 可用：
```powershell
psql --version
```

向量数据库信息：
```text
host=10.199.6.229
port=5433
database=chaoxing_ai_vector
user=vector_reader
password=123456
```

测试连接：
```powershell
psql "postgresql://vector_reader:123456@10.199.6.229:5433/chaoxing_ai_vector?sslmode=disable"
```

连接后可执行：
```sql
\dt
SELECT COUNT(*) FROM qa_vector_chunks;
```

退出：
```sql
\q
```

### 6. 配置 `config.local.py`
复制配置文件：
```powershell
Copy-Item .\config.example.py .\config.local.py
```

至少改这几项：

MySQL：
```python
db_host = "10.195.20.215"
db_port = 3306
db_user = "Zenith"
db_password = "123456"
db_name = "chaoxing_ai_course"
```

向量数据库：
```python
vector_db_url = "postgresql+psycopg://vector_reader:123456@10.199.6.229:5433/chaoxing_ai_vector"
```

大语言模型：
```python
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-key"
llm_model = "gpt-5.1-codex-mini"
```

学生端问答 / embedding：
```python
qa_llm_provider = "dashscope"
qa_llm_model = "qwen-max"
qa_embedding_model = "text-embedding-v4"
qa_embedding_dimensions = 1024
dashscope_api_key = "你的 DashScope API Key"
dashscope_base_url = "https://dashscope.aliyuncs.com"
```

如果启用语音：
```python
APPID = "你的 APPID"
ACCESS_TOKEN = "你的 ACCESS_TOKEN"
TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
TTS_CLUSTER = "volcano_tts"
TTS_VOICE_TYPE = "zh_male_M392_conversation_wvae_bigtts"
ASR_URL = "wss://openspeech.bytedance.com/api/v2/asr"
ASR_CLUSTER = "你的 ASR_CLUSTER"
```

### 7. 启动后端
推荐：
```powershell
.\start-backend.ps1
```

等价命令：
```powershell
$env:A12_DB_HOST = "10.195.20.215"
$env:A12_DB_PORT = "3306"
$env:A12_DB_USER = "Zenith"
$env:A12_DB_PASSWORD = "123456"
$env:A12_DB_NAME = "chaoxing_ai_course"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 8. 启动前端
```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

### 9. 打开页面
前端：
```text
http://127.0.0.1:5173/
```

学生端：
```text
http://127.0.0.1:5173/student/home?token=student_demo_token_001
```

后端接口文档：
```text
http://127.0.0.1:3001/docs
```

## 后续使用

### 1. 进入项目
```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
```

### 2. 是否需要重新配置
只有下面几种情况才需要重新改配置：
- `config.local.py` 被删了或被覆盖了
- 数据库地址、端口、账号、密码变了
- LLM / DashScope / 语音 API Key 变了
- 新代码新增了新的配置项

### 3. 拉取新代码后做什么
如果只是普通代码改动：
```powershell
git pull
```

如果前端依赖有变化，再执行：
```powershell
npm install
```

如果后端依赖有变化，再执行：
```powershell
pip install -r requirements.txt
```

如果数据库脚本有变化，再按需要重新导入对应 SQL。

### 4. 启动后端
```powershell
.\start-backend.ps1
```

### 5. 启动前端
```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

### 6. 改完代码后怎么生效
前端代码改动后：
- 开着 `npm run dev` 时，通常会自动热更新
- 如果页面没刷新出来，手动刷新浏览器

后端代码改动后：
- 开着 `uvicorn --reload` 时，通常会自动重载
- 如果接口没有生效，重启后端

重启后端：
```powershell
.\start-backend.ps1
```

## 最短步骤

### 初次使用最短步骤
```text
1. 安装 Node.js、Python、MySQL 客户端、PostgreSQL 客户端、Docker Desktop
2. cd 到项目目录
3. npm install
4. pip install -r requirements.txt
5. 创建 MySQL 数据库 chaoxing_ai_course
6. 导入 docs/mysql建表.sql
7. 导入 docs/init_test_data.sql
8. 用 psql 测试连接 10.199.6.229:5433/chaoxing_ai_vector
9. 复制 config.example.py 为 config.local.py
10. 填好 MySQL、向量数据库、LLM、DashScope、语音配置
11. 启动后端
12. 启动前端
13. 打开学生端页面
```

### 后续使用最短步骤
```text
1. cd 到项目目录
2. git pull
3. 依赖变了就执行 npm install / pip install -r requirements.txt
4. 配置没变就不用重新改
5. 启动后端
6. 启动前端
7. 前端不生效就刷新页面，后端不生效就重启后端
```
