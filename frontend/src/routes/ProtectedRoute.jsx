import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../stores/auth'

function ProtectedRoute() {
  const location = useLocation()
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <main className="center-page">
        <p className="muted">正在验证登录状态...</p>
      </main>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default ProtectedRoute
