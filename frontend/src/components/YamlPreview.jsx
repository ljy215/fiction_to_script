function YamlPreview({ yamlContent, validationResult, validationError, validating }) {
  const hasErrors = validationResult?.errors?.length > 0

  return (
    <aside className="yaml-preview-panel" aria-label="YAML 预览与校验结果">
      <div className="yaml-preview-block">
        <div className="preview-heading">
          <h3>YAML 预览</h3>
          <span>{yamlContent ? `${yamlContent.length} 字符` : '暂无内容'}</span>
        </div>
        <pre className="yaml-preview-content">{yamlContent || '生成或输入 YAML 后将在这里预览。'}</pre>
      </div>

      <div className="validation-panel" aria-live="polite">
        <div className="preview-heading">
          <h3>校验结果</h3>
          {validating && <span>校验中...</span>}
          {!validating && validationResult?.valid && <span className="validation-pass">通过</span>}
          {!validating && hasErrors && <span className="validation-fail">{validationResult.errors.length} 个问题</span>}
        </div>

        {validationError && <p className="form-error">{validationError}</p>}

        {!validationError && !validationResult && (
          <p className="muted compact-note">点击校验后显示 Schema 检查结果。</p>
        )}

        {validationResult?.valid && (
          <p className="validation-success">当前 YAML 已通过后端 Schema 校验。</p>
        )}

        {hasErrors && (
          <ul className="validation-errors">
            {validationResult.errors.map((error, index) => (
              <li key={`${error.path}-${index}`}>
                <code>{error.path}</code>
                <span>{error.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}

export default YamlPreview
