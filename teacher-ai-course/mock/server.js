const http = require('http')

const PORT = 3001

const parseTasks = new Map()
const scriptTasks = new Map()
const audioTasks = new Map()

function sendJson(res, data) {
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8'
  })
  res.end(JSON.stringify(data))
}

function parseBody(req) {
  return new Promise((resolve) => {
    let body = ''
    req.on('data', (chunk) => {
      body += chunk
    })
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {})
      } catch (e) {
        resolve({})
      }
    })
  })
}

function createRequestId() {
  return `mock-${Date.now()}-${Math.floor(Math.random() * 10000)}`
}

function createKnowledgeTree(fileName = '测试课件') {
  return [
    {
      id: 'kp-1',
      name: `${fileName}-第一章`,
      children: [
        {
          id: 'kp-1-1',
          name: '知识点 1：课程导入',
          children: [
            { id: 'kp-1-1-1', name: '教学目标' },
            { id: 'kp-1-1-2', name: '课程背景' }
          ]
        },
        {
          id: 'kp-1-2',
          name: '知识点 2：核心概念',
          children: [
            { id: 'kp-1-2-1', name: '定义说明' },
            { id: 'kp-1-2-2', name: '典型案例' }
          ]
        }
      ]
    },
    {
      id: 'kp-2',
      name: `${fileName}-第二章`,
      children: [
        {
          id: 'kp-2-1',
          name: '知识点 3：推导分析',
          children: [
            { id: 'kp-2-1-1', name: '公式推导' },
            { id: 'kp-2-1-2', name: '图示理解' }
          ]
        },
        {
          id: 'kp-2-2',
          name: '知识点 4：课堂总结',
          children: [
            { id: 'kp-2-2-1', name: '重点回顾' },
            { id: 'kp-2-2-2', name: '课后思考' }
          ]
        }
      ]
    }
  ]
}

function buildScriptContent(scriptType, parseId) {
  const typeMap = {
    standard: '标准脚本',
    detail: '详细脚本',
    simple: '简洁脚本'
  }

  const title = typeMap[scriptType] || '标准脚本'

  if (scriptType === 'detail') {
    return `【${title}】
parseId：${parseId}

一、课程导入
同学们好，今天我们开始学习本节课程内容。首先从课程背景与学习目标入手，帮助大家建立整体认知框架。

二、核心概念讲解
请大家重点关注知识点中的关键定义、应用场景以及与前序知识的联系。
这里建议结合板书或课件图示进行说明，帮助学生理解抽象内容。

三、案例分析
接下来通过典型案例，对核心原理进行分步骤讲解。
需要强调解题思路、方法迁移和常见误区。

四、总结与提升
最后我们对本节内容做系统总结，并提出课后思考题，帮助大家进一步巩固。`
  }

  if (scriptType === 'simple') {
    return `【${title}】
parseId：${parseId}

1. 导入课程背景
2. 讲解核心概念
3. 展示典型案例
4. 总结重点内容`
  }

  return `【${title}】
parseId：${parseId}

同学们好，今天我们将围绕本节课的几个核心知识点展开学习。
首先介绍课程背景与目标，然后依次讲解关键概念、典型案例与课堂总结。
请大家在学习过程中注意知识点之间的联系，并尝试结合实际场景进行理解。`
}

function isValidToken(body) {
  return body.token === 'test_token_001' ||
    body.token === undefined ||  // 兼容前端 token 放 header
    body.token === null
}

http.createServer(async (req, res) => {
  const requestId = createRequestId()

  if (req.method !== 'POST') {
    return sendJson(res, {
      code: 405,
      msg: '仅支持 POST',
      data: null,
      requestId
    })
  }

  const body = await parseBody(req)
  const headerToken = req.headers['x-platform-token'] ||
    (req.headers.authorization || '').replace('Bearer ', '')
  const token = body.token || headerToken

  // 1. /api/v1/platform/syncUser
  if (req.url === '/api/v1/platform/syncUser') {
    if (token !== 'test_token_001') {
      return sendJson(res, {
        code: 401,
        msg: 'token 无效',
        data: null,
        requestId
      })
    }

    return sendJson(res, {
      code: 200,
      msg: 'success',
      data: {
        teacherId: 'T10001',
        userId: 'U10001',
        teacherName: '张老师',
        userName: '张老师',
        schoolId: 'SCH001',
        schoolName: '测试大学'
      },
      requestId
    })
  }

  // 2. /api/v1/platform/syncCourse
  if (req.url === '/api/v1/platform/syncCourse') {
    if (token !== 'test_token_001') {
      return sendJson(res, {
        code: 401,
        msg: 'token 无效',
        data: null,
        requestId
      })
    }

    return sendJson(res, {
      code: 200,
      msg: 'success',
      data: {
        courseList: [
          {
            courseId: 'C10001',
            courseName: '大学物理 AI 智课示范课',
            classId: 'CL10001',
            schoolId: 'SCH001'
          },
          {
            courseId: 'C10002',
            courseName: '高等数学 AI 智课示范课',
            classId: 'CL10002',
            schoolId: 'SCH001'
          },
          {
            courseId: 'C10003',
            courseName: '计算机基础 AI 智课示范课',
            classId: 'CL10003',
            schoolId: 'SCH001'
          }
        ]
      },
      requestId
    })
  }

  // 3. /api/v1/lesson/parse
  if (req.url === '/api/v1/lesson/parse') {
    const { action, fileName, fileContent, parseId, courseId } = body

    if (!courseId && action !== 'status') {
      return sendJson(res, {
        code: 400,
        msg: 'courseId 不能为空',
        data: null,
        requestId
      })
    }

    if (action === 'upload') {
      if (!fileName || !fileContent) {
        return sendJson(res, {
          code: 400,
          msg: '文件名称或文件内容不能为空',
          data: null,
          requestId
        })
      }

      const newParseId = `P${Date.now()}`
      parseTasks.set(newParseId, {
        count: 0,
        status: 'processing',
        fileName,
        courseId
      })

      return sendJson(res, {
        code: 200,
        msg: 'success',
        data: {
          parseId: newParseId,
          status: 'processing',
          knowledgeTree: []
        },
        requestId
      })
    }

    if (action === 'status') {
      if (!parseId || !parseTasks.has(parseId)) {
        return sendJson(res, {
          code: 404,
          msg: 'parseId 不存在',
          data: null,
          requestId
        })
      }

      const task = parseTasks.get(parseId)
      task.count += 1

      if (task.count >= 3) {
        task.status = 'success'
        parseTasks.set(parseId, task)

        return sendJson(res, {
          code: 200,
          msg: 'success',
          data: {
            parseId,
            status: 'success',
            knowledgeTree: createKnowledgeTree(task.fileName)
          },
          requestId
        })
      }

      return sendJson(res, {
        code: 200,
        msg: 'success',
        data: {
          parseId,
          status: 'processing',
          knowledgeTree: []
        },
        requestId
      })
    }

    return sendJson(res, {
      code: 400,
      msg: 'action 无效，仅支持 upload/status',
      data: null,
      requestId
    })
  }

  // 4. /api/v1/lesson/generateScript
  if (req.url === '/api/v1/lesson/generateScript') {
    const { parseId, scriptType = 'standard', courseId } = body

    if (!parseId) {
      return sendJson(res, {
        code: 400,
        msg: 'parseId 不能为空',
        data: null,
        requestId
      })
    }

    if (!courseId) {
      return sendJson(res, {
        code: 400,
        msg: 'courseId 不能为空',
        data: null,
        requestId
      })
    }

    const scriptId = `S${Date.now()}`
    const scriptContent = buildScriptContent(scriptType, parseId)

    scriptTasks.set(scriptId, {
      scriptId,
      parseId,
      scriptType,
      scriptContent,
      status: 'success'
    })

    return sendJson(res, {
      code: 200,
      msg: 'success',
      data: {
        scriptId,
        parseId,
        scriptType,
        scriptContent,
        status: 'success'
      },
      requestId
    })
  }

  // 5. /api/v1/lesson/generateAudio
  if (req.url === '/api/v1/lesson/generateAudio') {
    const { scriptId, voiceType = 'female_standard', courseId } = body

    if (!scriptId) {
      return sendJson(res, {
        code: 400,
        msg: 'scriptId 不能为空',
        data: null,
        requestId
      })
    }

    if (!courseId) {
      return sendJson(res, {
        code: 400,
        msg: 'courseId 不能为空',
        data: null,
        requestId
      })
    }

    const audioId = `A${Date.now()}`
    const audioUrl = 'https://www.w3schools.com/html/horse.mp3'

    audioTasks.set(audioId, {
      audioId,
      scriptId,
      voiceType,
      audioUrl,
      status: 'success'
    })

    return sendJson(res, {
      code: 200,
      msg: 'success',
      data: {
        audioId,
        scriptId,
        voiceType,
        audioUrl,
        status: 'success'
      },
      requestId
    })
  }

  return sendJson(res, {
    code: 404,
    msg: 'mock 接口不存在',
    data: null,
    requestId
  })
}).listen(PORT, () => {
  console.log(`Mock server running at http://localhost:${PORT}`)
})