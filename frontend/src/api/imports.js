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

export function importDocxFile(token, projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest(`/projects/${projectId}/imports/docx`, {
    method: 'POST',
    headers: authHeaders(token),
    body: formData
  })
}

export function importPdfFile(token, projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest(`/projects/${projectId}/imports/pdf`, {
    method: 'POST',
    headers: authHeaders(token),
    body: formData
  })
}

export function importEpubFile(token, projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest(`/projects/${projectId}/imports/epub`, {
    method: 'POST',
    headers: authHeaders(token),
    body: formData
  })
}

export function listChapters(token, projectId, sourceDocumentId) {
  return apiRequest(`/projects/${projectId}/imports/${sourceDocumentId}/chapters`, {
    headers: authHeaders(token)
  })
}
