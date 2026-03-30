import os


class Config:
    STATIC_KEY = os.getenv("CHAOXING_STATIC_KEY", "chaoxing-ai-static-key")
    MOCK_MODE = os.getenv("CHAOXING_MOCK_MODE", "true").lower() == "true"
    CHAOXING_BASE_URL = os.getenv("CHAOXING_BASE_URL", "https://api.chaoxing.example.com")
