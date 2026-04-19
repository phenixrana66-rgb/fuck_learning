$env:A12_DB_HOST = "10.195.20.215"
$env:A12_DB_PORT = "3306"
$env:A12_DB_USER = "Zenith"
$env:A12_DB_PASSWORD = "123456"
$env:A12_DB_NAME = "chaoxing_ai_course"

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
