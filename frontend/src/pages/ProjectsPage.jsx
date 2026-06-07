import { useEffect, useMemo, useState } from 'react'

import { createGenerationTask, fetchGenerationTask, fetchLatestScript, updateScript } from '../api/generation'
import { importDocxFile, importEpubFile, importPastedText, importPdfFile, importTxtFile, listChapters } from '../api/imports'
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

function downloadYaml(filename, content) {
  const blob = new Blob([content], { type: 'text/yaml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
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
  const [sourceDocument, setSourceDocument] = useState(null)
  const [chapters, setChapters] = useState([])
  const [generating, setGenerating] = useState(false)
  const [savingScript, setSavingScript] = useState(false)
  const [generationTask, setGenerationTask] = useState(null)
  const [scriptDocument, setScriptDocument] = useState(null)
  const [yamlDraft, setYamlDraft] = useState('')
  const [error, setError] = useState('')

  const selectedScriptTypeLabel = useMemo(() => {
    if (!selectedProject?.script_type) {
      return '未选择'
    }
    return scriptTypes.find((item) => item.value === selectedProject.script_type)?.label || selectedProject.script_type
  }, [selectedProject])

  const canGenerate = Boolean(selectedProject && sourceDocument?.is_generation_ready)

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

  function resetWorkspaceState() {
    setImportText('')
    setImportFile(null)
    setSourceDocument(null)
    setChapters([])
    setGenerationTask(null)
    setScriptDocument(null)
    setYamlDraft('')
  }

  async function loadChapters(projectId, documentId) {
    const nextChapters = await listChapters(token, projectId, documentId)
    setChapters(nextChapters)
  }

  async function loadLatestScript(projectId) {
    try {
      const latest = await fetchLatestScript(token, projectId)
      setScriptDocument(latest)
      setYamlDraft(latest.yaml_content)
    } catch {
      setScriptDocument(null)
      setYamlDraft('')
    }
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
      resetWorkspaceState()
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
      resetWorkspaceState()
      await loadLatestScript(projectId)
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
        resetWorkspaceState()
      }
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function acceptImportedDocument(imported) {
    setSourceDocument(imported)
    setScriptDocument(null)
    setYamlDraft('')
    await loadChapters(imported.project_id, imported.id)
  }

  async function handleImportText(event) {
    event.preventDefault()
    if (!selectedProject) {
      return
    }

    setImporting(true)
    setError('')
    try {
      const imported = await importPastedText(token, selectedProject.id, importText)
      await acceptImportedDocument(imported)
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
    try {
      const extension = importFile.name.toLowerCase().split('.').pop()
      const imported =
        extension === 'docx'
          ? await importDocxFile(token, selectedProject.id, importFile)
          : extension === 'pdf'
            ? await importPdfFile(token, selectedProject.id, importFile)
            : extension === 'epub'
              ? await importEpubFile(token, selectedProject.id, importFile)
              : await importTxtFile(token, selectedProject.id, importFile)
      await acceptImportedDocument(imported)
      setImportFile(null)
      event.target.reset()
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setImporting(false)
    }
  }

  async function handleGenerate() {
    if (!selectedProject || !sourceDocument) {
      return
    }

    setGenerating(true)
    setError('')
    try {
      const task = await createGenerationTask(token, selectedProject.id, {
        source_document_id: sourceDocument.id,
        script_type: selectedProject.script_type
      })
      setGenerationTask(task)

      const finalTask = task.status === 'succeeded' || task.status === 'failed'
        ? task
        : await fetchGenerationTask(token, selectedProject.id, task.id)
      setGenerationTask(finalTask)

      if (finalTask.status === 'succeeded') {
        await loadLatestScript(selectedProject.id)
        await loadProjects()
      } else if (finalTask.error_message) {
        setError(finalTask.error_message)
      }
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setGenerating(false)
    }
  }

  function handleExport() {
    if (!yamlDraft) {
      return
    }
    const baseName = selectedProject?.novel_title || selectedProject?.name || 'script'
    downloadYaml(`${baseName}.yaml`, yamlDraft)
  }

  async function handleSaveScript() {
    if (!selectedProject || !scriptDocument || !yamlDraft) {
      return
    }

    setSavingScript(true)
    setError('')
    try {
      const updated = await updateScript(token, selectedProject.id, scriptDocument.id, yamlDraft)
      setScriptDocument(updated)
      setYamlDraft(updated.yaml_content)
    } catch (caughtError) {
      setError(caughtError.message)
    } finally {
      setSavingScript(false)
    }
  }

  return (
    <main className="app-shell compact">
      <header className="topbar">
        <div>
          <p className="eyebrow">Novel to Script</p>
          <h1>小说改编工作台</h1>
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

          <div className="workflow-grid">
            <section className="workflow-panel" aria-label="小说导入">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Step 1</p>
                  <h2>导入小说</h2>
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
                    上传文件
                    <input
                      required
                      accept=".txt,.docx,.pdf,.epub,text/plain,application/pdf,application/epub+zip,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      name="source_file"
                      type="file"
                      onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                    />
                  </label>
                  <button className="button secondary full" type="submit" disabled={importing || !importFile}>
                    {importing ? '导入中...' : '导入 txt / docx / pdf / epub'}
                  </button>
                </form>
              </div>
            </section>

            <section className="workflow-panel" aria-label="章节确认">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Step 2</p>
                  <h2>章节确认</h2>
                </div>
                {sourceDocument && (
                  <span className={`status-pill ${sourceDocument.is_generation_ready ? 'status-ready' : 'status-failed'}`}>
                    {sourceDocument.chapter_count} / {sourceDocument.minimum_chapters_required} 章
                  </span>
                )}
              </div>
              {sourceDocument ? (
                <>
                  <p className="import-result">
                    已导入 {sourceDocument.content_length} 个字符，来源：{sourceDocument.source_type}
                  </p>
                  <div className="chapter-list">
                    {chapters.map((chapter) => (
                      <details className="chapter-row" key={chapter.id}>
                        <summary>
                          <strong>{chapter.order}. {chapter.title}</strong>
                          <span>{chapter.content_length} 字符</span>
                        </summary>
                        <p>{chapter.content_text}</p>
                      </details>
                    ))}
                  </div>
                </>
              ) : (
                <p className="muted">导入小说后会在这里显示章节识别结果。</p>
              )}
            </section>

            <section className="workflow-panel" aria-label="剧本生成">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Step 3</p>
                  <h2>生成剧本</h2>
                </div>
                {generationTask && <span className="status-pill status-generating">{generationTask.status}</span>}
              </div>
              <button className="button primary full" type="button" onClick={handleGenerate} disabled={!canGenerate || generating}>
                {generating ? '生成中...' : '生成中文 YAML 剧本'}
              </button>
              {sourceDocument && !sourceDocument.is_generation_ready && (
                <p className="form-error">至少需要 3 章内容才能开始生成。</p>
              )}
              {generationTask && (
                <div className="progress-track" aria-label="生成进度">
                  <span style={{ width: `${generationTask.progress}%` }} />
                </div>
              )}
            </section>
          </div>

          <section className="script-editor" aria-label="YAML 剧本编辑器">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Script</p>
                <h2>YAML 剧本</h2>
              </div>
              <button className="button secondary" type="button" onClick={handleExport} disabled={!yamlDraft}>
                导出 YAML
              </button>
              <button className="button primary" type="button" onClick={handleSaveScript} disabled={!scriptDocument || !yamlDraft || savingScript}>
                {savingScript ? '保存中...' : '保存'}
              </button>
            </div>
            <textarea
              className="yaml-editor"
              value={yamlDraft}
              onChange={(event) => setYamlDraft(event.target.value)}
              placeholder="生成后的 YAML 会显示在这里。"
            />
            {scriptDocument && (
              <p className="muted">
                当前版本：v{scriptDocument.version_number} · 更新时间 {formatDate(scriptDocument.updated_at)}
              </p>
            )}
          </section>
        </section>
      )}
    </main>
  )
}

export default ProjectsPage
