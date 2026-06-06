import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <main className="center-page">
      <section className="auth-card">
        <p className="eyebrow">404</p>
        <h1>页面不存在</h1>
        <Link className="button primary full" to="/">
          返回首页
        </Link>
      </section>
    </main>
  )
}

export default NotFoundPage
