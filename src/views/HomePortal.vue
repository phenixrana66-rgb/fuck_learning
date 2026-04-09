<template>
  <div class="portal-page">
    <section class="portal-hero">
      <div class="portal-copy">
        <div class="portal-kicker">Chaoxing AI Course</div>
        <h1>统一入口</h1>
        <p>
          本地调试时先进入首页，再按角色进入学生端或教师端。学生端会携带演示 token，
          教师端保留原有登录同步流程。
        </p>

        <div class="portal-actions">
          <RouterLink class="portal-button portal-button-student" to="/student/home?token=student_demo_token_001">
            进入学生端
          </RouterLink>
          <RouterLink class="portal-button portal-button-teacher" to="/teacher/login">
            进入教师端
          </RouterLink>
        </div>
      </div>

      <div class="portal-stage" aria-hidden="true">
        <div class="stage-grid"></div>
        <div class="stage-beam stage-beam-student"></div>
        <div class="stage-beam stage-beam-teacher"></div>
        <div class="stage-card stage-card-student">
          <span class="stage-label">Student</span>
          <strong>/student/home</strong>
          <small>自动带入 demo token</small>
        </div>
        <div class="stage-card stage-card-teacher">
          <span class="stage-label">Teacher</span>
          <strong>/teacher/login</strong>
          <small>继续使用教师登录页</small>
        </div>
      </div>
    </section>

    <section class="portal-roles">
      <article class="portal-role portal-role-student">
        <div class="portal-role-head">
          <span class="portal-role-tag">学生端</span>
          <h2>课程学习与 AI 互动</h2>
        </div>
        <p>适合直接验证学生首页、课程详情、学习通知与 AI 互动流程。</p>
        <ul class="portal-role-points">
          <li>默认进入学生首页</li>
          <li>自动附带 `student_demo_token_001`</li>
          <li>依赖本地 Flask 学生后端</li>
        </ul>
        <RouterLink class="portal-link" to="/student/home?token=student_demo_token_001">
          打开学生端
        </RouterLink>
      </article>

      <article class="portal-role portal-role-teacher">
        <div class="portal-role-head">
          <span class="portal-role-tag">教师端</span>
          <h2>平台同步与课程管理</h2>
        </div>
        <p>适合调试教师登录、课程同步、课件解析、脚本生成与音频生成流程。</p>
        <ul class="portal-role-points">
          <li>先进入教师登录页</li>
          <li>仍由登录页输入或接收 token</li>
          <li>根目录 `npm run dev` 会一并启动 mock</li>
        </ul>
        <RouterLink class="portal-link" to="/teacher/login">
          打开教师端
        </RouterLink>
      </article>
    </section>

    <section class="portal-checklist">
      <div class="portal-section-title">
        <span>启动清单</span>
        <h2>本地联调只需要记住这三步</h2>
      </div>

      <div class="portal-steps">
        <div class="portal-step">
          <div class="portal-step-index">01</div>
          <div>
            <h3>启动统一前端</h3>
            <code>npm run dev</code>
          </div>
        </div>

        <div class="portal-step">
          <div class="portal-step-index">02</div>
          <div>
            <h3>如需学生端，启动 Flask 后端</h3>
            <code>cd student-ai-course/backend/student_plugin && python app.py</code>
          </div>
        </div>

        <div class="portal-step">
          <div class="portal-step-index">03</div>
          <div>
            <h3>回到首页选择入口</h3>
            <code>http://localhost:5173/</code>
          </div>
        </div>
      </div>

      <div class="portal-notes">
        <div class="portal-note">
          <span>学生端后端</span>
          <strong>http://localhost:5000</strong>
        </div>
        <div class="portal-note">
          <span>教师端 mock</span>
          <strong>http://localhost:3001</strong>
        </div>
        <div class="portal-note">
          <span>统一前端入口</span>
          <strong>http://localhost:5173/</strong>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.portal-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(26, 188, 156, 0.2), transparent 28%),
    radial-gradient(circle at top right, rgba(61, 99, 240, 0.18), transparent 24%),
    linear-gradient(180deg, #f4f6fb 0%, #eef2f7 100%);
  color: #14213d;
}

.portal-hero,
.portal-roles,
.portal-checklist {
  max-width: 1320px;
  margin: 0 auto;
}

.portal-hero {
  min-height: min(780px, calc(100svh - 56px));
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
  gap: 28px;
  align-items: center;
}

.portal-copy {
  max-width: 560px;
}

.portal-kicker,
.portal-role-tag,
.portal-section-title span {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(20, 33, 61, 0.08);
  color: #385072;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.portal-copy h1 {
  margin: 18px 0 0;
  font-size: clamp(54px, 8vw, 96px);
  line-height: 0.95;
  letter-spacing: -0.05em;
  color: #10213f;
}

.portal-copy p {
  max-width: 480px;
  margin: 22px 0 0;
  color: #52627d;
  font-size: 17px;
  line-height: 1.9;
}

.portal-actions {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 30px;
}

.portal-button,
.portal-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0 22px;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.portal-button:hover,
.portal-link:hover {
  transform: translateY(-1px);
}

.portal-button-student {
  background: linear-gradient(135deg, #20b486, #5ad0ab);
  color: #fff;
  box-shadow: 0 16px 32px rgba(41, 157, 123, 0.24);
}

.portal-button-teacher {
  border: 1px solid rgba(16, 33, 63, 0.14);
  background: rgba(255, 255, 255, 0.74);
  color: #10213f;
}

.portal-stage {
  position: relative;
  min-height: 620px;
  overflow: hidden;
  border-radius: 34px;
  background:
    linear-gradient(145deg, rgba(16, 33, 63, 0.98), rgba(17, 44, 78, 0.92)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent);
  box-shadow: 0 32px 80px rgba(18, 36, 64, 0.22);
}

.stage-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), transparent 92%);
}

.stage-beam {
  position: absolute;
  border-radius: 999px;
  filter: blur(14px);
  opacity: 0.85;
  animation: stageFloat 7s ease-in-out infinite;
}

.stage-beam-student {
  top: 88px;
  left: 62px;
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(42, 215, 166, 0.42), transparent 68%);
}

.stage-beam-teacher {
  right: 66px;
  bottom: 92px;
  width: 320px;
  height: 320px;
  background: radial-gradient(circle, rgba(88, 120, 255, 0.34), transparent 70%);
  animation-delay: -2.2s;
}

.stage-card {
  position: absolute;
  width: min(74%, 320px);
  padding: 24px 24px 22px;
  border-radius: 26px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  box-shadow: 0 24px 60px rgba(7, 18, 36, 0.25);
  color: #ecf3ff;
  animation: stageDrift 0.9s ease both;
}

.stage-card-student {
  top: 118px;
  right: 56px;
}

.stage-card-teacher {
  left: 56px;
  bottom: 86px;
  animation-delay: 0.14s;
}

.stage-label {
  display: inline-flex;
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.stage-card strong {
  display: block;
  font-size: 28px;
  line-height: 1.2;
}

.stage-card small {
  display: block;
  margin-top: 10px;
  color: rgba(235, 244, 255, 0.7);
  font-size: 13px;
}

.portal-roles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
  margin-top: 24px;
}

.portal-role,
.portal-checklist {
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(222, 228, 238, 0.86);
  box-shadow: 0 18px 44px rgba(20, 33, 61, 0.08);
}

.portal-role {
  padding: 30px;
}

.portal-role-head h2,
.portal-section-title h2 {
  margin: 14px 0 0;
  color: #10213f;
  font-size: 32px;
  line-height: 1.15;
}

.portal-role p {
  margin: 14px 0 0;
  color: #5c6b85;
  line-height: 1.85;
}

.portal-role-points {
  margin: 20px 0 24px;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.portal-role-points li {
  color: #1e2e4d;
}

.portal-role-points li::before {
  content: '•';
  margin-right: 10px;
  color: #4e7efc;
}

.portal-link {
  border: 1px solid rgba(16, 33, 63, 0.12);
  background: #fff;
  color: #10213f;
}

.portal-checklist {
  margin-top: 22px;
  padding: 32px;
}

.portal-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.portal-step {
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff, #f6f8fb);
  border: 1px solid #e8edf4;
}

.portal-step-index {
  color: #91a0b8;
  font-size: 12px;
  letter-spacing: 0.12em;
}

.portal-step h3 {
  margin: 14px 0 0;
  color: #10213f;
  font-size: 20px;
}

.portal-step code,
.portal-note strong {
  display: block;
  margin-top: 10px;
  color: #1f4b3c;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  line-height: 1.7;
  word-break: break-all;
}

.portal-notes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.portal-note {
  padding: 18px 20px;
  border-top: 1px solid #e7edf6;
}

.portal-note span {
  color: #7b8aa3;
  font-size: 13px;
}

@keyframes stageFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }

  50% {
    transform: translate3d(0, -12px, 0);
  }
}

@keyframes stageDrift {
  from {
    opacity: 0;
    transform: translate3d(0, 18px, 0);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@media (max-width: 1100px) {
  .portal-page {
    padding: 18px;
  }

  .portal-hero,
  .portal-roles,
  .portal-steps,
  .portal-notes {
    grid-template-columns: 1fr;
  }

  .portal-hero {
    min-height: auto;
  }

  .portal-stage {
    min-height: 420px;
  }
}

@media (max-width: 720px) {
  .portal-copy h1 {
    font-size: 52px;
  }

  .portal-stage {
    min-height: 360px;
  }

  .stage-card {
    width: calc(100% - 40px);
    left: 20px;
    right: 20px;
  }

  .stage-card-student {
    top: 34px;
  }

  .stage-card-teacher {
    bottom: 28px;
  }

  .portal-role,
  .portal-checklist {
    padding: 22px;
  }

  .portal-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
