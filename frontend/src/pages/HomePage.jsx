import { Link } from 'react-router-dom'

const capabilities = [
  '多语言小说输入，中文剧本输出',
  '至少 3 个章节的小说改编',
  '按剧本类型路由不同智能体',
  '完整 YAML 剧本文档导出',
  '剧本视图编辑器与历史版本'
]

function HomePage() {
  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">AI Novel To Script</p>
          <h1>AI 小说转剧本工具</h1>
          <p className="intro">
            面向小说作者的 Web 应用，将 3 个章节以上的小说文本改编为可编辑、可校验、可导出的中文 YAML 剧本初稿。
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/register">
              创建账号
            </Link>
            <Link className="button secondary" to="/login">
              登录
            </Link>
          </div>
        </div>
        <div className="status-panel" aria-label="当前前端状态">
          <span className="status-dot" />
          <div>
            <strong>认证流程前端已接入</strong>
            <p>React Router + JWT localStorage</p>
          </div>
        </div>
      </section>

      <section className="content-grid" aria-label="MVP 信息">
        <article className="panel">
          <h2>核心能力</h2>
          <ul>
            {capabilities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h2>下一步</h2>
          <p>
            后续 PR 将补充项目管理、小说导入、LangGraph 生成流程、剧本视图编辑器和 YAML 导出。
          </p>
        </article>
      </section>
    </main>
  )
}

export default HomePage
