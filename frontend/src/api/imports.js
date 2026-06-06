import { apiRequest } from './client'

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`
  }
}

export function importPastedText(token, projectId, text) {
  return apiRequest(`/projects/${projectId}/imports/text`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ text })
  })
}

export function importTxtFile(token, projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest(`/projects/${projectId}/imports/txt`, {
    method: 'POST',
    headers: authHeaders(token),
    body: formData
  })
}
