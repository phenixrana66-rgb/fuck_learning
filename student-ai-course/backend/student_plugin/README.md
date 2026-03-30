# Student Plugin Backend

本目录提供学生端联调用的 Flask 适配层，默认开启 Mock 模式，用于本地调试免登鉴权、课程列表、播放进度、问答与续讲接口。

## 启动方式

```bash
cd backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 默认配置

- 默认端口：`5000`
- 默认调试 token：`student_demo_token_001`
- 所有接口均要求带签名的 JSON 请求体，包含 `time` 与 `enc`
- 本地调试默认开启 `CHAOXING_MOCK_MODE=true`
