import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# 截图保存路径
project_root = Path(__file__).resolve().parents[2]
screenshot_path = project_root / "test_screenshot.png"
log_path = project_root / "frontend_diagnose.log"

async def run_diagnose():
    url = "http://localhost:5173/student/slide-learning/lesson2026070808195380a9f1/94?chapterId=db-section-94&unitId=db-unit-15&knowledgeChapterId=db-unit-15::source-18&pageNo=2"
    print(f"====== 开始诊断前端页面: {url} ======")
    
    logs = []
    def log(message):
        print(message)
        logs.append(message)

    async with async_playwright() as p:
        # 启动 Chromium 无头浏览器
        browser = await p.chromium.launch(headless=True)
        # 创建浏览器上下文
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # 监听控制台日志
        page.on("console", lambda msg: log(f"[Console] {msg.type}: {msg.text}"))
        # 监听控制台报错
        page.on("pageerror", lambda err: log(f"[PageError] {err}"))

        # 监听并拦截网络请求/响应
        async def handle_response(response):
            req_url = response.url
            if "/api/" in req_url:
                status = response.status
                log(f"[API Response] {response.request.method} {req_url} -> Status: {status}")
                try:
                    text = await response.text()
                    # 只打印前 500 个字符或格式化打印
                    try:
                        data = json.loads(text)
                        log(f"  Response JSON (Truncated): {json.dumps(data, ensure_ascii=False)[:600]}")
                    except Exception:
                        log(f"  Response text (Truncated): {text[:300]}")
                except Exception as e:
                    log(f"  Cannot read body: {e}")

        page.on("response", handle_response)

        log("正在导航到测试网页...")
        try:
            # 导航并等待页面网络状态闲置
            await page.goto(url, wait_until="networkidle", timeout=30000)
            log("导航成功，等待 5 秒以确保异步渲染完成...")
            await asyncio.sleep(5)
        except Exception as e:
            log(f"[Error] 导航失败或超时: {e}")

        # 截图保存
        log(f"正在保存截图至: {screenshot_path}")
        await page.screenshot(path=str(screenshot_path), full_page=True)
        log("截图保存成功。")

        # 打印 DOM 中的关键元素细节（如 img 标签等）
        images = await page.eval_on_selector_all("img", "elements => elements.map(el => ({src: el.src, alt: el.alt}))")
        log(f"找到 {len(images)} 个 img 标签，具体地址如下:")
        for idx, img in enumerate(images, start=1):
            log(f"  Image {idx}: src='{img['src']}' alt='{img['alt']}'")

        # 打印当前播放器状态
        player_exist = await page.locator("div").filter(has_text="电路模型").count()
        log(f"包含 '电路模型' 的元素数: {player_exist}")

        await browser.close()
        
    # 保存日志
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    log("====== 诊断结束 ======")

if __name__ == "__main__":
    asyncio.run(run_diagnose())
