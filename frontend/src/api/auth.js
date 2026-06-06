import { apiRequest } from './client'

export function registerUser(payload) {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function loginUser(payload) {
  return apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function fetchCurrentUser(token) {
  return apiRequest('/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}
