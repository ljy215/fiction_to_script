import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './routes/ProtectedRoute'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import ProjectsPage from './pages/ProjectsPage'
import RegisterPage from './pages/RegisterPage'
import './styles.css'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/projects" element={<ProjectsPage />} />
      </Route>
      <Route path="/app" element={<Navigate to="/projects" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default AppRoutes
