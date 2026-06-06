import { useEffect, useMemo, useState } from 'react'

import { importPastedText, importTxtFile } from '../api/imports'
import { createProject, deleteProject, fetchProject, listProjects } from '../api/projects'
import { useAuth } from '../stores/auth'

const scriptTypes = [
  { value: 'short_drama', label: '短剧剧本' },
  { value: 'film', label: '影视剧本' },
  { value: 'audio_drama', label: '广播剧剧本' },
  { value: 'stage_play', label: '舞台剧剧本' }
]

const statusLabels = {
  draft: '草稿',
  parsing: '解析中',
  generating: '生成中',
  ready: '已生成',
  failed: '失败'
}

const initialForm = {
  name: '',
  novel_title: '',
  original_author: '',
  script_type: 'film',
  description: ''
}

function toOptionalString(value) {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function formatDate(value) {
  if (!value) {
    return '暂无'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function ProjectsPage() {
  const { token, user, logout } = useAuth()
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [importText, setImportText] = useState('')
  const [importFile, setImportFile] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [error, setError] = useState('')

  const selectedScriptTypeLabel = useMemo(() => {
    if (!selectedProject?.script_type) {
      return '未选择'
    }
    return scriptTypes.find((item) => item.value === selectedProject.script_type)?.label || selectedProject.script_type
  }, [selectedProject])

  async function loadProjects() {
    setLoading(true)
    setError('')
    try {
      const nextProjects = await listProjects(token)
      setProjects(nextProjects)
      if (selectedProject) {
        const refreshed = nextProjects.find((project) => project.id === selectedProject.id)
        setSelectedProject(refreshed || null)
      }
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [token])

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function resetImportState() {
    setImportText('')
    setImportFile(null)
    setImportResult(null)
  }

  async function handleCreate(event) {
    event.preventDefault()
    setCreating(true)
    setError('')
    try {
      const project = await createProject(token, {
        name: form.name.trim(),
        novel_title: toOptionalString(form.novel_title),
        original_author: toOptionalString(form.original_author),
        script_type: form.script_type || null,
        description: toOptionalString(form.description)
      })
      setProjects((current) => [project, ...current])
      setSelectedProject(project)
      resetImportState()
      setForm(initialForm)
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setCreating(false)
    }
  }

  async function handleOpen(projectId) {
    setError('')
    try {
      const project = await fetchProject(token, projectId)
      setSelectedProject(project)
      resetImportState()
    } catch (caughtError) {
      setError(caughtError.message)
    }
  }

  async function handleDelete(projectId) {
    setDeletingId(projectId)
    setError('')
    try {
      await deleteProject(token, projectId)
      setProjects((current) => current.filter((project) => project.id !== projectId))
      if (selectedProject?.id === projectId) {
        setSelectedProject(null)
        resetImportState()
      }
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleImportText(event) {
    event.preventDefault()
    if (!selectedProject) {
      return
    }

    setImporting(true)
    setError('')
    setImportResult(null)
    try {
      const imported = await importPastedText(token, selectedProject.id, importText)
      setImportResult(imported)
      setImportText('')
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setImporting(false)
    }
  }

  async function handleImportFile(event) {
    event.preventDefault()
    if (!selectedProject || !importFile) {
      return
    }

    setImporting(true)
    setError('')
    setImportResult(null)
    try {
      const imported = await importTxtFile(token, selectedProject.id, importFile)
      setImportResult(imported)
      setImportFile(null)
      event.target.reset()
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setImporting(false)
    }
  }

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

      <section className="workspace-summary" aria-label="账号与项目概览">
        <div>
          <span className="summary-label">当前账号</span>
          <strong>{user?.email || '已登录用户'}</strong>
        </div>
        <div>
          <span className="summary-label">项目数量</span>
          <strong>{projects.length}</strong>
        </div>
        <button className="button secondary" type="button" onClick={loadProjects} disabled={loading}>
          {loading ? '刷新中...' : '刷新'}
        </button>
      </section>

      {error && <p className="form-error page-error">{error}</p>}

      <section className="project-workspace">
        <form className="panel project-form" onSubmit={handleCreate}>
          <h2>创建项目</h2>
          <label>
            项目名称
            <input required name="name" type="text" maxLength={120} value={form.name} onChange={updateField} />
          </label>
          <label>
            小说名称
            <input name="novel_title" type="text" maxLength={180} value={form.novel_title} onChange={updateField} />
          </label>
          <label>
            原作者
            <input name="original_author" type="text" maxLength={120} value={form.original_author} onChange={updateField} />
          </label>
          <label>
            剧本类型
            <select name="script_type" value={form.script_type} onChange={updateField}>
              {scriptTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            备注
            <textarea name="description" rows="4" value={form.description} onChange={updateField} />
          </label>
          <button className="button primary full" type="submit" disabled={creating}>
            {creating ? '创建中...' : '创建项目'}
          </button>
        </form>

        <section className="project-list-section" aria-label="项目列表">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Library</p>
              <h2>我的项目</h2>
            </div>
          </div>

          {loading ? (
            <div className="empty-state">
              <h2>正在加载项目</h2>
              <p>请稍候。</p>
            </div>
          ) : projects.length === 0 ? (
            <div className="empty-state">
              <h2>还没有项目</h2>
              <p>创建第一个小说改编项目后，它会出现在这里。</p>
            </div>
          ) : (
            <div className="project-list">
              {projects.map((project) => (
                <article className="project-card" key={project.id}>
                  <div>
                    <div className="project-card-header">
                      <h3>{project.name}</h3>
                      <span className={`status-pill status-${project.status}`}>
                        {statusLabels[project.status] || project.status}
                      </span>
                    </div>
                    <p className="project-meta">
                      {project.novel_title || '未填写小说名称'} · {project.original_author || '未填写作者'}
                    </p>
                    <p className="project-meta">更新于 {formatDate(project.updated_at)}</p>
                  </div>
                  <div className="project-actions">
                    <button className="button secondary" type="button" onClick={() => handleOpen(project.id)}>
                      打开
                    </button>
                    <button
                      className="button danger"
                      type="button"
                      onClick={() => handleDelete(project.id)}
                      disabled={deletingId === project.id}
                    >
                      {deletingId === project.id ? '删除中...' : '删除'}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>

      {selectedProject && (
        <section className="panel project-detail" aria-label="项目详情">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Detail</p>
              <h2>{selectedProject.name}</h2>
            </div>
            <span className={`status-pill status-${selectedProject.status}`}>
              {statusLabels[selectedProject.status] || selectedProject.status}
            </span>
          </div>
          <dl className="detail-grid">
            <div>
              <dt>小说名称</dt>
              <dd>{selectedProject.novel_title || '未填写'}</dd>
            </div>
            <div>
              <dt>原作者</dt>
              <dd>{selectedProject.original_author || '未填写'}</dd>
            </div>
            <div>
              <dt>剧本类型</dt>
              <dd>{selectedScriptTypeLabel}</dd>
            </div>
            <div>
              <dt>创建时间</dt>
              <dd>{formatDate(selectedProject.created_at)}</dd>
            </div>
          </dl>
          {selectedProject.description && <p className="detail-description">{selectedProject.description}</p>}

          <div className="import-tools" aria-label="小说导入">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Import</p>
                <h2>导入小说文本</h2>
              </div>
            </div>
            <div className="import-grid">
              <form className="project-form import-form" onSubmit={handleImportText}>
                <label>
                  粘贴文本
                  <textarea
                    required
                    name="import_text"
                    rows="8"
                    value={importText}
                    onChange={(event) => setImportText(event.target.value)}
                  />
                </label>
                <button className="button primary full" type="submit" disabled={importing}>
                  {importing ? '导入中...' : '导入粘贴文本'}
                </button>
              </form>

              <form className="project-form import-form" onSubmit={handleImportFile}>
                <label>
                  txt 文件
                  <input
                    required
                    accept=".txt,text/plain"
                    name="txt_file"
                    type="file"
                    onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                  />
                </label>
                <button className="button secondary full" type="submit" disabled={importing || !importFile}>
                  {importing ? '导入中...' : '导入 txt 文件'}
                </button>
              </form>
            </div>
            {importResult && (
              <p className="import-result">
                已导入 {importResult.content_length} 个字符，来源：{importResult.source_type}
              </p>
            )}
          </div>
        </section>
      )}
    </main>
  )
}

export default ProjectsPage
