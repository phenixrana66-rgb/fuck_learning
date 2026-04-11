import os


class Config:
    STATIC_KEY = os.getenv("CHAOXING_STATIC_KEY", "chaoxing-ai-static-key")
    MOCK_MODE = os.getenv("CHAOXING_MOCK_MODE", "true").lower() == "true"
    CHAOXING_BASE_URL = os.getenv("CHAOXING_BASE_URL", "https://api.chaoxing.example.com")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:123456@127.0.0.1:3306/chaoxing_ai_course?charset=utf8mb4",
    )
