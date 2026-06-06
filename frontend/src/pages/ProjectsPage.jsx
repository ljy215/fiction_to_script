import { useAuth } from '../stores/auth'

function ProjectsPage() {
  const { user, logout } = useAuth()

  return (
    <main className="app-shell compact">
      <header className="topbar">
        <div>
          <p className="eyebrow">Projects</p>
          <h1>项目工作台</h1>
        </div>
        <button className="button secondary" type="button" onClick={logout}>
          退出登录
        </button>
      </header>

      <section className="panel">
        <h2>账号</h2>
        <p className="muted">{user?.email || '已登录用户'}</p>
      </section>

      <section className="empty-state">
        <h2>项目管理将在下一个 PR 接入</h2>
        <p>
          当前页面用于验证登录态和受保护路由。后续会在这里创建、查看和管理小说改编项目。
        </p>
      </section>
    </main>
  )
}

export default ProjectsPage
