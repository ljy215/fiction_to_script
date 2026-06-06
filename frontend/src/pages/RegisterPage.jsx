import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { loginUser, registerUser } from '../api/auth'
import { useAuth } from '../stores/auth'

function RegisterPage() {
  const navigate = useNavigate()
  const { isAuthenticated, setToken } = useAuth()
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />
  }

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await registerUser({
        email: form.email,
        username: form.username || null,
        password: form.password
      })
      const token = await loginUser({ email: form.email, password: form.password })
      setToken(token.access_token)
      navigate('/projects', { replace: true })
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Create account</p>
        <h1>注册</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            邮箱
            <input
              required
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={updateField}
            />
          </label>
          <label>
            用户名
            <input
              name="username"
              type="text"
              autoComplete="nickname"
              value={form.username}
              onChange={updateField}
            />
          </label>
          <label>
            密码
            <input
              required
              minLength={8}
              name="password"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={updateField}
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="button primary full" type="submit" disabled={submitting}>
            {submitting ? '注册中...' : '注册并登录'}
          </button>
        </form>
        <p className="auth-switch">
          已有账号？ <Link to="/login">去登录</Link>
        </p>
      </section>
    </main>
  )
}

export default RegisterPage
