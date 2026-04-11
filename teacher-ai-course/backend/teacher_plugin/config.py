import os


class Config:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:123456@127.0.0.1:3306/chaoxing_ai_course?charset=utf8mb4",
    )
    TEST_PLATFORM_TOKEN = os.getenv("CHAOXING_TEACHER_TEST_TOKEN", "test_token_001")
    DEFAULT_AUDIO_URL = os.getenv(
        "CHAOXING_DEFAULT_AUDIO_URL",
        "https://www.w3schools.com/html/horse.mp3",
    )
