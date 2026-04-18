const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => console.log('console:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('pageerror:', err.message));
  await page.goto('http://127.0.0.1:5173/student/player/L10001?token=student_demo_token_001', { waitUntil: 'networkidle' });
  await page.click('button.student-topbar-nav-item:nth-child(3)');
  await page.waitForTimeout(1000);
  const input = page.locator('.student-ai-input-area .el-textarea__inner').first();
  console.log('placeholder=', await input.getAttribute('placeholder'));
  await input.fill('压杆稳定里临界载荷和长细比有什么关系');
  await input.press('Enter');
  await page.waitForTimeout(5000);
  console.log('messages=', await page.locator('.student-chat-item').count());
  console.log('lastMessage=', (await page.locator('.student-chat-item').last().innerText()).replace(/\s+/g, ' ').slice(0, 220));
  console.log('voiceButtons=', await page.locator('.student-ai-icon-button.voice').count());
  await browser.close();
})();
