import { API_BASE_URL, apiRequest } from './client'

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`
  }
}

export function createGenerationTask(token, projectId, payload) {
  return apiRequest(`/projects/${projectId}/generation-tasks`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  })
}

export function fetchGenerationTask(token, projectId, taskId) {
  return apiRequest(`/projects/${projectId}/generation-tasks/${taskId}`, {
    headers: authHeaders(token)
  })
}

export async function streamGenerationTask(token, projectId, taskId, onTask) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/generation-tasks/${taskId}/events`, {
    headers: authHeaders(token)
  })

  if (!response.ok || !response.body) {
    throw new Error('生成事件流连接失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finalTask = null

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const rawEvent of events) {
      const eventLines = rawEvent.split('\n')
      const eventName = eventLines.find((line) => line.startsWith('event:'))?.slice(6).trim()
      const dataLine = eventLines.find((line) => line.startsWith('data:'))
      if (!dataLine) {
        continue
      }

      const task = JSON.parse(dataLine.slice(5).trim())
      if (eventName === 'task' || eventName === 'done') {
        finalTask = task
        onTask(task)
      }
      if (eventName === 'done') {
        return task
      }
      if (eventName === 'error') {
        throw new Error(task.detail || '生成事件流失败')
      }
    }
  }

  return finalTask
}

export function fetchLatestScript(token, projectId) {
  return apiRequest(`/projects/${projectId}/scripts/latest`, {
    headers: authHeaders(token)
  })
}

export function fetchScriptVersions(token, projectId) {
  return apiRequest(`/projects/${projectId}/scripts`, {
    headers: authHeaders(token)
  })
}

export function updateScript(token, projectId, scriptId, yamlContent) {
  return apiRequest(`/projects/${projectId}/scripts/${scriptId}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify({ yaml_content: yamlContent })
  })
}

export function restoreScriptVersion(token, projectId, scriptId) {
  return apiRequest(`/projects/${projectId}/scripts/${scriptId}/restore`, {
    method: 'POST',
    headers: authHeaders(token)
  })
}

export function validateScriptYaml(token, projectId, yamlContent) {
  return apiRequest(`/projects/${projectId}/scripts/validate`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ yaml_content: yamlContent })
  })
}
