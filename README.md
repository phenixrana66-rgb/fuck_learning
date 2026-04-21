## 初次使用

### 1. 安装软件
- Node.js 18+
- npm 9+
- Python 3.11+
- MySQL 客户端
- PostgreSQL 客户端（要能执行 `psql`）
- Microsoft Power Point(用于提取课件图片)

### 2. 安装依赖
先进入代码根目录

前端：
```powershell
npm install
```

后端：
```powershell
python -m pip install -r requirements.txt
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
host=your_database_host
port=3306
user=user_name
password=123456
database=chaoxing_ai_course
```

#### 初始化主库（手工导入）

建库：
```sql
CREATE DATABASE chaoxing_ai_course DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

导入表结构：
```powershell
mysql -h your_database_host -P 3306 -u user_name -p chaoxing_ai_course < ".\docs\mysql建表.sql"
```

导入 QA 检索相关表：
```powershell
mysql -h your_database_host -P 3306 -u user_name -p chaoxing_ai_course < ".\docs\mysql_qa_retrieval.sql"
```

导入测试数据：
```powershell
mysql -h your_database_host -P 3306 -u user_name -p chaoxing_ai_course < ".\docs\init_test_data.sql"
```

### 5. 连接向量数据库
先确认 `psql` 可用：
```powershell
psql --version
```

向量数据库信息：
```text
host=your_vertor_database_host
port=5433
database=chaoxing_ai_vector
user=vector_reader
password=123456
```

测试连接：
```powershell
psql "postgresql://vector_reader:123456@your_vertor_database_host/chaoxing_ai_vector?sslmode=disable"
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

说明：
- 当前后端启动时直接读取仓库根目录下的 `config.local.py`
- `db_name` 里不要写 SQL 反引号
- 错误写法：``db_name = "`chaoxing_ai_course`"``
- 正确写法：`db_name = "chaoxing_ai_course"`

MySQL：
```python
db_host = "your_database_host"
db_port = 3306
db_user = "user_name"
db_password = "123456"
db_name = "chaoxing_ai_course_test"
```

数据库名
```python
db_name = "chaoxing_ai_course"
```

向量数据库：
```python
vector_db_url = "postgresql+psycopg://vector_reader:123456@your_vertor_database_host:5433/chaoxing_ai_vector"
```

大语言模型：
```python
llm_api_base_url = "http://127.0.0.1:13010/v1"
llm_api_key = "replace-with-your-key"
llm_model = "deepseek-chat"
```

学生端问答 / embedding数据库：
```python
qa_llm_provider = "dashscope"
qa_llm_model = "qwen-max"
qa_embedding_model = "text-embedding-v4"
qa_embedding_dimensions = 1024
dashscope_api_key = "你的 DashScope API Key"
dashscope_base_url = "https://dashscope.aliyuncs.com"
```

语音合成大模型：
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
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

启动前请先确认 `config.local.py` 里的 `db_name` 已经指向你要使用的数据库。

### 8. 启动前端
```powershell
.\start-frontend.ps1
```

### 9. 打开页面
前端：
```text
http://127.0.0.1:5173/
```

体验学生端功能时，请先使用教师端进行一次课程发布。

学生端：
```text
http://127.0.0.1:5173/student/home?token=student_demo_token_001
```

后端接口文档：
```text
http://127.0.0.1:3001/docs
```