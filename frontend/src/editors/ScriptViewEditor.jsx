const lineTypeLabels = {
  action: '动作',
  dialogue: '对白',
  narration: '旁白',
  sound: '音效',
  transition: '转场',
  stage_direction: '舞台提示',
  note: '备注'
}

function ScriptViewEditor({
  scriptView,
  onLineTextChange,
  onLineCharacterChange,
  onRegenerateScene,
  onRegenerateLine,
  regeneratingTarget
}) {
  const characters = scriptView.characters || []
  const scenes = scriptView.scenes || []

  if (scriptView.parseError) {
    return (
      <section className="script-view-empty" aria-label="剧本视图解析结果">
        <strong>无法展示剧本视图</strong>
        <p>{scriptView.parseError}</p>
      </section>
    )
  }

  if (scenes.length === 0) {
    return (
      <section className="script-view-empty" aria-label="剧本视图空状态">
        <strong>暂无剧本视图</strong>
        <p>生成或粘贴包含 script.scenes 的 YAML 后，这里会显示按场景组织的剧本。</p>
      </section>
    )
  }

  return (
    <section className="script-view-editor" aria-label="剧本视图编辑器">
      <div className="script-view-toolbar">
        <strong>{scenes.length} 场</strong>
        <span>{characters.length} 个角色</span>
      </div>

      <div className="scene-list">
        {scenes.map((scene, sceneIndex) => (
          <article className="scene-editor" key={scene.id || `scene-${sceneIndex}`}>
            <header className="scene-header">
              <div>
                <span className="scene-index">场景 {scene.order || sceneIndex + 1}</span>
                <h3>{scene.heading || scene.id || `场景 ${sceneIndex + 1}`}</h3>
              </div>
              <div className="scene-actions">
                <span className="status-pill">{scene.lines?.length || 0} 行</span>
                <button
                  className="button secondary"
                  type="button"
                  onClick={() => onRegenerateScene(scene.id)}
                  disabled={!onRegenerateScene || regeneratingTarget === scene.id}
                >
                  {regeneratingTarget === scene.id ? '重生成中...' : '重生成场景'}
                </button>
              </div>
            </header>

            <dl className="scene-meta">
              <div>
                <dt>目的</dt>
                <dd>{scene.purpose || '未填写'}</dd>
              </div>
              <div>
                <dt>冲突</dt>
                <dd>{scene.conflict || '未填写'}</dd>
              </div>
              <div>
                <dt>结果</dt>
                <dd>{scene.outcome || '未填写'}</dd>
              </div>
            </dl>

            <div className="script-line-list">
              {(scene.lines || []).map((line, lineIndex) => {
                const lineType = line.type || 'action'
                const isDialogue = lineType === 'dialogue'
                return (
                  <div className={`script-line line-${lineType}`} key={line.id || `${scene.id}-${lineIndex}`}>
                    <div className="line-controls">
                      <span>{lineTypeLabels[lineType] || lineType}</span>
                      {isDialogue && (
                        <select
                          aria-label="对白角色"
                          value={line.character_id || ''}
                          onChange={(event) => onLineCharacterChange(scene.id, line.id, event.target.value)}
                        >
                          <option value="">未指定角色</option>
                          {characters.map((character) => (
                            <option key={character.id} value={character.id}>
                              {character.name || character.id}
                            </option>
                          ))}
                        </select>
                      )}
                      <button
                        className="button secondary"
                        type="button"
                        onClick={() => onRegenerateLine(scene.id, line.id)}
                        disabled={!onRegenerateLine || regeneratingTarget === line.id}
                      >
                        {regeneratingTarget === line.id ? '重生成中...' : '重生成行'}
                      </button>
                    </div>
                    <textarea
                      aria-label={`${lineTypeLabels[lineType] || lineType}文本`}
                      value={line.text || ''}
                      onChange={(event) => onLineTextChange(scene.id, line.id, event.target.value)}
                    />
                  </div>
                )
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default ScriptViewEditor
