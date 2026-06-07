import { apiRequest } from './client'

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

export function fetchLatestScript(token, projectId) {
  return apiRequest(`/projects/${projectId}/scripts/latest`, {
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

export function validateScriptYaml(token, projectId, yamlContent) {
  return apiRequest(`/projects/${projectId}/scripts/validate`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ yaml_content: yamlContent })
  })
}
