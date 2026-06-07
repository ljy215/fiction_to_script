# 剧本 YAML Schema 说明

版本：v1.0  
日期：2026-06-05  
状态：已根据当前确认项重做

## 1. Schema 目标

该 YAML Schema 用于承载 AI 小说转剧本工具生成的完整中文剧本初稿。它既是导出格式，也是前端剧本视图编辑器、后端校验器、历史版本和局部重生成的核心数据结构。

本 Schema 面向以下产品约束：

- 输入小说支持多语言。
- 最终剧本输出中文。
- 剧本类型由用户选择。
- 不同剧本类型由不同 LangGraph 智能体写作。
- 首期输出一个完整 YAML 剧本文档。
- 用户在剧本视图编辑器中编辑，系统同步 YAML。
- 系统支持历史版本和局部重生成。
- 只导出 YAML。

## 2. 设计原则

- 可读：作者和开发者可以直接阅读 YAML。
- 可编辑：前端可以将 YAML 映射为剧本视图编辑器。
- 可校验：后端可以检查必填字段、ID 引用和剧本行类型。
- 可追溯：场景和剧本行可以追溯到原小说章节和事件。
- 可重生成：局部重生成时能定位章节、事件、场景和剧本行。
- 可还原：剧本场景应保留原文章节中的环境背景、动作调度、关键对白和现场氛围，不能只保留人物对话和地点。
- 可扩展：未来可扩展多集、分镜、音频、视频，但 MVP 不要求实现。
- 安全：YAML 不包含 API Key、用户密码和内部敏感日志。

## 3. 顶层结构

```yaml
schema_version: "1.0"

document:
  id: "script_doc_001"
  project_id: "project_001"
  title: "示例剧本"
  status: "draft"
  created_at: "2026-06-05T10:00:00+08:00"
  updated_at: "2026-06-05T10:30:00+08:00"

source:
  novel_title: "示例小说"
  original_author: "原作者"
  source_language: "en"
  output_language: "zh-CN"
  minimum_chapters_required: 3
  chapter_count: 3
  input_files:
    - id: "file_001"
      filename: "novel.epub"
      file_type: "epub"
  chapters:
    - id: "ch_001"
      order: 1
      title: "第一章"
      summary: "章节中文摘要。"

script_config:
  script_type: "film"
  script_type_label: "影视剧本"
  fidelity_policy: "faithful"
  output_mode: "single_document"

generation:
  provider: "aliyun_bailian"
  model: "model-name"
  graph_name: "film_script_graph"
  graph_version: "1.0"
  generated_at: "2026-06-05T10:30:00+08:00"
  agent_runs:
    - node: "event_extractor"
      status: "success"
      started_at: "2026-06-05T10:10:00+08:00"
      finished_at: "2026-06-05T10:12:00+08:00"

characters:
  - id: "char_001"
    name: "林晚"
    original_name: "Lynn"
    aliases: ["女主"]
    role: "protagonist"
    description: "角色简介。"
    motivation: "角色目标。"
    arc: "角色弧光。"
    source_refs:
      - chapter_id: "ch_001"

locations:
  - id: "loc_001"
    name: "旧公寓"
    original_name: "Old Apartment"
    type: "interior"
    description: "地点简介。"
    source_refs:
      - chapter_id: "ch_001"

events:
  - id: "evt_001"
    chapter_id: "ch_001"
    order: 1
    summary: "林晚回到旧公寓，发现房间被翻动。"
    participants: ["char_001"]
    location_id: "loc_001"
    consequence: "林晚决定调查真相。"
    fidelity_note: "忠实原文章节核心事件。"

adaptation:
  logline: "一句话中文故事梗概。"
  theme: "主题。"
  strategy:
    preserved_events: ["evt_001"]
    merged_events: []
    omitted_events: []
    added_bridges:
      - "为连接场景补充少量过渡动作。"
  notes:
    - "整体改编以忠实原文为优先。"

script:
  scenes:
    - id: "sc_001"
      order: 1
      heading: "内景 旧公寓 夜"
      location_id: "loc_001"
      interior_exterior: "interior"
      time_of_day: "night"
      purpose: "建立女主困境并引出主线冲突。"
      conflict: "女主发现有人闯入过房间。"
      outcome: "女主决定追查。"
      source_refs:
        - chapter_id: "ch_001"
          event_id: "evt_001"
      lines:
        - id: "line_001"
          type: "action"
          text: "夜雨拍在旧公寓的窗玻璃上，走廊尽头的声控灯忽明忽暗，门缝里透出一线冷白色的光。"
        - id: "line_002"
          type: "sound"
          text: "远处电梯叮的一声停住，随后是金属门缓慢合拢的回响。"
        - id: "line_003"
          type: "action"
          text: "林晚握紧钥匙，肩膀贴着门框停了半秒，目光扫过被撬开的锁芯和散落在地的信封。"
        - id: "line_004"
          type: "dialogue"
          character_id: "char_001"
          speaker: "林晚"
          text: "谁来过这里？"
          emotion: "警觉"
        - id: "line_005"
          type: "action"
          text: "她没有立刻进屋，而是蹲下捡起信封，指尖避开上面的泥水，听见卧室里传来极轻的纸页摩擦声。"
        - id: "line_006"
          type: "transition"
          text: "切至："

editor_state:
  current_version_id: "version_001"
  last_saved_at: "2026-06-05T10:35:00+08:00"

notes:
  - id: "note_001"
    target_id: "sc_001"
    level: "suggestion"
    text: "可以继续加强悬疑气氛。"
```

## 4. 字段说明与设计原因

### 4.1 `schema_version`

类型：字符串  
必填：是

说明：Schema 版本号。

设计原因：后续产品会增加多集、分镜或更多剧本类型，版本号可以让旧 YAML 继续被兼容解析。

### 4.2 `document`

类型：对象  
必填：是

字段：

- `id`：剧本文档 ID。
- `project_id`：所属项目 ID。
- `title`：剧本标题。
- `status`：状态，例如 `draft`、`reviewing`、`final`。
- `created_at`：创建时间。
- `updated_at`：更新时间。

设计原因：YAML 是用户项目中的一个剧本文档，必须能和云端项目、历史版本关联。

### 4.3 `source`

类型：对象  
必填：是

字段：

- `novel_title`：小说名。
- `original_author`：原作者。
- `source_language`：原文语言。
- `output_language`：输出语言，MVP 固定为 `zh-CN`。
- `minimum_chapters_required`：最低章节数，固定为 `3`。
- `chapter_count`：实际章节数。
- `input_files`：输入文件列表。
- `chapters`：章节列表。

设计原因：产品支持多语言输入但输出中文，因此必须明确区分来源语言和输出语言。章节信息用于追溯和局部重生成。

### 4.4 `script_config`

类型：对象  
必填：是

字段：

- `script_type`：剧本类型代码。
- `script_type_label`：剧本类型中文名称。
- `fidelity_policy`：忠实度策略，MVP 使用 `faithful`。
- `output_mode`：输出模式，MVP 使用 `single_document`。

建议 `script_type`：

- `short_drama`：短剧剧本。
- `film`：影视剧本。
- `audio_drama`：广播剧剧本。
- `stage_play`：舞台剧剧本。

设计原因：用户选择不同剧本类型后，系统需要调用不同智能体流程，并在 YAML 中保留该选择。

### 4.5 `generation`

类型：对象  
必填：是

字段：

- `provider`：模型供应商，MVP 为 `aliyun_bailian`。
- `model`：模型名称。
- `graph_name`：LangGraph 图名称。
- `graph_version`：LangGraph 图版本。
- `generated_at`：生成时间。
- `agent_runs`：智能体节点运行记录。

设计原因：生成结果需要可追溯。记录供应商、模型和图版本可以帮助复现问题，但不能记录 API Key。

### 4.6 `characters`

类型：数组  
必填：是

字段：

- `id`：角色 ID。
- `name`：中文角色名。
- `original_name`：原文角色名，适用于多语言输入。
- `aliases`：别名。
- `role`：叙事角色，例如 `protagonist`、`antagonist`、`supporting`。
- `description`：角色简介。
- `motivation`：角色目标。
- `arc`：角色弧光。
- `source_refs`：来源章节。

设计原因：多语言小说可能存在翻译名和原名，二者都需要保留。对白通过 `character_id` 引用角色，避免名字不一致。

### 4.7 `locations`

类型：数组  
必填：是

字段：

- `id`：地点 ID。
- `name`：中文地点名。
- `original_name`：原文地点名。
- `type`：地点类型，例如 `interior`、`exterior`、`mixed`。
- `description`：地点描述。
- `source_refs`：来源章节。

设计原因：剧本视图编辑器和未来分镜都需要稳定地点资产。保留原文地点名有助于多语言追溯。

### 4.8 `events`

类型：数组  
必填：是

字段：

- `id`：事件 ID。
- `chapter_id`：来源章节 ID。
- `order`：事件在章节中的顺序。
- `summary`：中文事件摘要。
- `participants`：参与角色 ID。
- `location_id`：地点 ID。
- `consequence`：事件结果。
- `fidelity_note`：忠实原文说明。

设计原因：本项目要求尽量忠实原文。先抽取事件，再从事件改编场景，可以降低长文本遗漏和随意改写风险。

### 4.9 `adaptation`

类型：对象  
必填：是

字段：

- `logline`：一句话中文梗概。
- `theme`：主题。
- `strategy`：改编策略。
- `notes`：整体备注。

`strategy` 字段：

- `preserved_events`：保留事件 ID。
- `merged_events`：合并事件说明。
- `omitted_events`：删减事件说明。
- `added_bridges`：为剧本连贯性补充的过渡内容。

设计原因：即使以忠实原文为优先，小说转剧本仍然需要压缩、合并和补充过渡。该字段用于解释 AI 的改编决策。

### 4.10 `script`

类型：对象  
必填：是

字段：

- `scenes`：完整剧本场景列表。

设计原因：MVP 前期只输出一个完整剧本文档，不拆多集，因此顶层使用 `script.scenes` 而不是必选 `episodes`。未来可扩展为 `episodes[].scenes`。

### 4.11 `scenes`

类型：数组  
位置：`script.scenes`  
必填：是

字段：

- `id`：场景 ID。
- `order`：场景顺序。
- `heading`：剧本场景标题。
- `location_id`：地点 ID。
- `interior_exterior`：内外景。
- `time_of_day`：时间。
- `purpose`：场景目的。
- `conflict`：场景冲突。
- `outcome`：场景结果。
- `source_refs`：来源章节和事件。
- `lines`：剧本行。

内容要求：

- 场景必须按原文章节顺序组织，至少能追溯到一个 `chapter_id` 和一个 `event_id`。
- 每个章节至少应改编为 1 个场景；动作、冲突或对白密集章节可以拆成 2-4 个场景。
- `heading` 应具体呈现场景空间和时间，例如“外景 轩家村雪林 清晨”，不要使用“主要场景”这类占位标题。
- 每个场景必须包含背景建立：天气、光线、声音、道具、空间关系、人物走位、表情或肢体动作。
- 每个场景不能只由地点和对白构成；进入对白前应先用 `action` 或 `sound` 建立画面。
- 战斗、埋伏、追逐、修炼等场景应写清攻防动作、距离变化、伤势、节奏和现场氛围。

设计原因：剧本视图编辑器以场景为主要编辑单位，局部重生成也通常以场景为边界。小说转剧本不能只保留剧情摘要，否则作者无法继续打磨成可拍摄或可排演的剧本；场景层必须承载原文环境、动作和戏剧节奏。

### 4.12 `lines`

类型：数组  
位置：`script.scenes[].lines`  
必填：是

通用字段：

- `id`：剧本行 ID。
- `type`：剧本行类型。
- `text`：正文。

`type` 建议值：

- `action`：动作。
- `dialogue`：对白。
- `narration`：旁白。
- `sound`：音效。
- `transition`：转场。
- `stage_direction`：舞台提示，主要用于舞台剧。
- `note`：创作备注。

对白字段：

- `character_id`：角色 ID。
- `speaker`：显示名称。
- `emotion`：情绪。
- `parenthetical`：括注。

写作要求：

- `action` 用于承载背景环境、人物动作、表情、调度、战斗动作和关键视觉信息。
- `dialogue` 应尽量保留或改写原文关键对白，不能把对白密集章节压缩成单句概括。
- `sound` 用于广播剧、影视剧或气氛建立，例如脚步声、箭矢破空声、雨声、门轴声。
- `stage_direction` 用于舞台剧的舞台区位、灯光、上下场和演员动作。
- 对白之间应穿插必要 `action`，体现人物反应、停顿、压迫感和场景变化。

建议密度：

- 普通叙事场景至少包含 3 条 `action`。
- 对白密集场景至少包含 4-10 条 `dialogue`，并穿插 `action`。
- 战斗或行动场景应以 `action` 为主，`action` 数量应明显多于 `dialogue`。

设计原因：不同剧本类型侧重点不同。广播剧需要音效，舞台剧需要舞台提示，影视剧需要动作和转场，因此行类型必须结构化。结构化行也能避免 AI 将小说压缩成“地点 + 对白”的简化稿，使生成结果更接近可继续打磨的剧本初稿。

### 4.13 `editor_state`

类型：对象  
必填：否

字段：

- `current_version_id`：当前版本 ID。
- `last_saved_at`：最近保存时间。

设计原因：YAML 同时服务剧本视图编辑器，需要记录编辑状态，帮助前端恢复用户上次编辑位置和版本。

### 4.14 `notes`

类型：数组  
必填：否

字段：

- `id`：备注 ID。
- `target_id`：备注关联对象 ID。
- `level`：备注等级，例如 `info`、`suggestion`、`warning`。
- `text`：备注内容。

设计原因：AI 不确定翻译、补充桥段或改编取舍时，应通过备注提示用户确认。

## 5. ID 规则

建议 ID 前缀：

- `script_doc_`：剧本文档。
- `project_`：项目。
- `file_`：输入文件。
- `ch_`：章节。
- `evt_`：事件。
- `char_`：角色。
- `loc_`：地点。
- `sc_`：场景。
- `line_`：剧本行。
- `note_`：备注。
- `version_`：历史版本。

设计原因：稳定 ID 是局部重生成、历史版本对比、前端编辑和引用校验的基础。

## 6. 校验规则

### 6.1 基础结构校验

- YAML 必须可解析。
- `schema_version` 必须存在。
- `document` 必须存在。
- `source` 必须存在。
- `script_config` 必须存在。
- `generation` 必须存在。
- `characters` 必须存在。
- `locations` 必须存在。
- `events` 必须存在。
- `adaptation` 必须存在。
- `script.scenes` 必须存在。

### 6.2 语言校验

- `source.output_language` 必须为 `zh-CN`。
- 剧本正文应为中文。
- 原文名称可保留在 `original_name` 字段。

### 6.3 章节校验

- `source.chapter_count` 必须大于等于 `source.minimum_chapters_required`。
- `source.minimum_chapters_required` 必须为 `3`。
- `source.chapter_count` 应等于 `source.chapters` 数量。
- `source.chapters[].id` 必须唯一。

### 6.4 引用校验

- `events[].chapter_id` 必须存在于 `source.chapters[].id`。
- `events[].participants[]` 必须存在于 `characters[].id`。
- `events[].location_id` 必须存在于 `locations[].id`。
- `script.scenes[].location_id` 必须存在于 `locations[].id`。
- `script.scenes[].source_refs[].chapter_id` 必须存在于 `source.chapters[].id`。
- `script.scenes[].source_refs[].event_id` 必须存在于 `events[].id`。
- `dialogue` 类型的 line 必须有 `character_id`。
- `dialogue.character_id` 必须存在于 `characters[].id`。

### 6.5 剧本内容校验

- 每个场景必须有 `heading`。
- 每个场景必须至少包含一条 `line`。
- 每个场景至少应包含 `action`、`dialogue`、`narration` 中的一种。
- 每个场景应至少包含用于建立背景或动作调度的 `action`。
- 每个场景不应只包含 `dialogue` 类型的 line。
- 对白密集章节生成的场景应保留多条关键对白，而不是只输出摘要式对白。
- 每条 line 必须有 `id`、`type`、`text`。
- `type` 必须在允许枚举中。
- `script.scenes[].order` 必须为正整数。
- 同一场景下 `lines[].order` 如存在，必须按正整数排序。

### 6.6 安全校验

- YAML 不得包含 API Key。
- YAML 不得包含用户密码或密码哈希。
- YAML 不得包含服务端内部错误堆栈。

## 7. 局部重生成要求

局部重生成应尽量保持 ID 稳定。

建议规则：

- 重新生成场景时，保留 `scenes[].id`。
- 重新生成对白时，保留原角色 ID。
- 删除旧 line 并生成新 line 时，可以生成新的 `line_` ID。
- 重生成完成后必须再次执行 Schema 校验。
- 重生成结果应保存为新的历史版本。

设计原因：如果 ID 大量变化，历史版本对比和前端编辑状态会失效。

## 8. 历史版本要求

历史版本可以存储在数据库中，也可以将版本信息同步到 YAML 的 `editor_state`。

版本记录至少包含：

- 版本 ID。
- 项目 ID。
- 创建时间。
- 创建来源：AI 全量生成、用户保存、局部重生成、恢复历史版本。
- YAML 快照。
- 关联生成任务 ID。

设计原因：用户需要回滚和对比剧本改动，尤其是 AI 局部重生成可能覆盖人工修改。

## 9. 不进入 YAML 的内容

以下内容不得写入导出的 YAML：

- 阿里百炼 API Key。
- 用户密码。
- 用户登录态 Token。
- 服务端内部日志。
- 完整异常堆栈。
- 未脱敏的系统配置。

设计原因：YAML 是用户可导出的文件，必须避免泄漏敏感信息。

## 10. 未来扩展

当前 MVP 使用 `script.scenes` 表示完整剧本。未来如需扩展，可以增加：

- `episodes[].scenes`：多集短剧。
- `acts[].scenes`：三幕式结构。
- `shots`：分镜。
- `voice_assets`：配音资产。
- `production_notes`：拍摄和制作备注。

这些字段不作为 MVP 必填项。
