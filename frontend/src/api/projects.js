import { apiRequest } from './client'

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`
  }
}

export function listProjects(token) {
  return apiRequest('/projects', {
    headers: authHeaders(token)
  })
}

export function createProject(token, payload) {
  return apiRequest('/projects', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  })
}

export function fetchProject(token, projectId) {
  return apiRequest(`/projects/${projectId}`, {
    headers: authHeaders(token)
  })
}

export function deleteProject(token, projectId) {
  return apiRequest(`/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(token)
  })
}
