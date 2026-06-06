import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { loginUser } from '../api/auth'
import { useAuth } from '../stores/auth'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, setToken } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />
  }

  const redirectTo = location.state?.from?.pathname || '/projects'

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const token = await loginUser(form)
      setToken(token.access_token)
      navigate(redirectTo, { replace: true })
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Welcome back</p>
        <h1>登录</h1>
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
            密码
            <input
              required
              name="password"
              type="password"
              autoComplete="current-password"
              value={form.password}
              onChange={updateField}
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="button primary full" type="submit" disabled={submitting}>
            {submitting ? '登录中...' : '登录'}
          </button>
        </form>
        <p className="auth-switch">
          还没有账号？ <Link to="/register">去注册</Link>
        </p>
      </section>
    </main>
  )
}

export default LoginPage
