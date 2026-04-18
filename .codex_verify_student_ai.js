const fs = require('fs');
const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:5173';
const TOKEN = 'student_demo_token_001';
const PLAYER_URL = `${BASE_URL}/student/player/L10001?token=${TOKEN}`;
const KNOWLEDGE_URL = `${BASE_URL}/student/knowledge-learning/L10001/1?token=${TOKEN}`;
const PLAYER_TRANSCRIPT = '压杆稳定里临界载荷和长细比有什么关系？';
const KNOWLEDGE_TRANSCRIPT = '请概括压杆稳定这一章的核心内容。';

async function installAsrMocks(page, transcript) {
  await page.addInitScript((mockTranscript) => {
    window.__mockTranscript = mockTranscript;
    window.__lastWsUrl = '';

    class MockWebSocket {
      static OPEN = 1;
      static CLOSED = 3;

      constructor(url) {
        this.url = url;
        this.readyState = MockWebSocket.OPEN;
        window.__lastWsUrl = url;
        setTimeout(() => this.onopen && this.onopen(new Event('open')), 10);
      }

      send(raw) {
        const payload = JSON.parse(raw || '{}');
        if (payload.type === 'start') {
          setTimeout(() => {
            this.onmessage && this.onmessage({ data: JSON.stringify({ type: 'ready' }) });
          }, 10);
          return;
        }

        if (payload.type === 'audio') {
          setTimeout(() => {
            this.onmessage && this.onmessage({
              data: JSON.stringify({
                type: 'transcript',
                text: window.__mockTranscript,
                final: Boolean(payload.final),
                seq: payload.seq || 1
              })
            });
          }, 50);
        }
      }

      close() {
        this.readyState = MockWebSocket.CLOSED;
        setTimeout(() => this.onclose && this.onclose(new CloseEvent('close')), 10);
      }
    }

    window.WebSocket = MockWebSocket;

    navigator.mediaDevices = navigator.mediaDevices || {};
    navigator.mediaDevices.getUserMedia = async () => ({
      getTracks() {
        return [{ stop() {} }];
      }
    });

    class MockMediaRecorder {
      static isTypeSupported() {
        return true;
      }

      constructor(stream, options = {}) {
        this.stream = stream;
        this.mimeType = options.mimeType || 'audio/webm';
        this.state = 'inactive';
        this.ondataavailable = null;
        this.onstop = null;
        this._timer = null;
      }

      start() {
        this.state = 'recording';
        this._timer = setTimeout(() => {
          if (this.ondataavailable) {
            this.ondataavailable({
              data: new Blob(['fake-audio'], { type: this.mimeType })
            });
          }
        }, 120);
      }

      stop() {
        this.state = 'inactive';
        clearTimeout(this._timer);
        setTimeout(() => this.onstop && this.onstop(), 0);
      }
    }

    window.MediaRecorder = MockMediaRecorder;
  }, transcript);
}

async function waitForInteractRequest(page) {
  return page.waitForResponse((response) => {
    return response.url().includes('/student-api/api/v1/qa/interact') && response.request().method() === 'POST';
  }, { timeout: 30000 });
}

async function verifyPlayer(page) {
  const requests = [];
  page.on('console', (msg) => console.log('[player console]', msg.type(), msg.text()));
  page.on('request', (request) => {
    if (request.url().includes('/student-api/')) {
      requests.push({ method: request.method(), url: request.url() });
    }
  });

  await page.goto(PLAYER_URL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'AI实时问答' }).click();
  await page.waitForSelector('.student-ai-chat-card');

  const voiceButton = page.locator('.student-ai-input-actions .student-ai-icon-button.voice');
  const textarea = page.locator('.student-ai-input-area textarea');

  await voiceButton.click();
  try {
    await page.waitForFunction(
      ({ selector, expected }) => {
        const el = document.querySelector(selector);
        return !!el && el.value === expected;
      },
      { selector: '.student-ai-input-area textarea', expected: PLAYER_TRANSCRIPT },
      { timeout: 30000 }
    );
  } catch (error) {
    await page.screenshot({ path: 'output/playwright/player-asr-timeout.png', fullPage: true });
    const diagnostics = await page.evaluate(() => ({
      wsUrl: window.__lastWsUrl || '',
      textareaValue: document.querySelector('.student-ai-input-area textarea')?.value || '',
      voiceLabel: document.querySelector('.student-ai-input-actions .student-ai-icon-button.voice')?.getAttribute('aria-label') || '',
      html: document.querySelector('.student-ai-input-area')?.innerHTML || ''
    }));
    console.log(JSON.stringify({ playerDiagnostics: diagnostics }, null, 2));
    throw error;
  }

  await voiceButton.click();
  await textarea.press('Enter');

  const interactResponse = await waitForInteractRequest(page);
  const interactBody = await interactResponse.json();

  await page.waitForFunction(
    (text) => Array.from(document.querySelectorAll('.student-chat-bubble')).some((node) => node.textContent.includes(text)),
    PLAYER_TRANSCRIPT
  );

  const wsUrl = await page.evaluate(() => window.__lastWsUrl);
  return {
    wsUrl,
    interactStatus: interactResponse.status(),
    interactAnswer: interactBody?.data?.answer || '',
    apiRequests: requests
  };
}

async function verifyKnowledge(page) {
  const requests = [];
  page.on('console', (msg) => console.log('[knowledge console]', msg.type(), msg.text()));
  page.on('request', (request) => {
    if (request.url().includes('/student-api/')) {
      requests.push({ method: request.method(), url: request.url() });
    }
  });

  await page.goto(KNOWLEDGE_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('.ai-card');

  const voiceButton = page.locator('.ai-input-actions .ai-icon-button.voice');
  const textarea = page.locator('.ai-textarea');

  await voiceButton.click();
  await page.waitForFunction(
    ({ selector, expected }) => {
      const el = document.querySelector(selector);
      return !!el && el.value === expected;
    },
    { selector: '.ai-textarea', expected: KNOWLEDGE_TRANSCRIPT },
    { timeout: 30000 }
  );

  await voiceButton.click();
  await textarea.press('Enter');

  const interactResponse = await waitForInteractRequest(page);
  const interactBody = await interactResponse.json();

  await page.waitForFunction(
    (text) => Array.from(document.querySelectorAll('.ai-message-bubble')).some((node) => node.textContent.includes(text)),
    KNOWLEDGE_TRANSCRIPT
  );

  const wsUrl = await page.evaluate(() => window.__lastWsUrl);
  return {
    wsUrl,
    interactStatus: interactResponse.status(),
    interactAnswer: interactBody?.data?.answer || '',
    apiRequests: requests
  };
}

async function main() {
  fs.mkdirSync('output/playwright', { recursive: true });
  const executablePath = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ].find((file) => fs.existsSync(file));

  const browser = await chromium.launch({
    headless: true,
    executablePath
  });
  try {
    const playerPage = await browser.newPage();
    await installAsrMocks(playerPage, PLAYER_TRANSCRIPT);
    const player = await verifyPlayer(playerPage);

    const knowledgePage = await browser.newPage();
    await installAsrMocks(knowledgePage, KNOWLEDGE_TRANSCRIPT);
    const knowledge = await verifyKnowledge(knowledgePage);

    console.log(JSON.stringify({ player, knowledge }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
