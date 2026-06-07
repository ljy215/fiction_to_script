function indentation(line) {
  return line.match(/^ */)?.[0].length || 0
}

function stripComment(value) {
  let inSingle = false
  let inDouble = false
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index]
    const prev = value[index - 1]
    if (char === "'" && !inDouble) {
      inSingle = !inSingle
    }
    if (char === '"' && !inSingle && prev !== '\\') {
      inDouble = !inDouble
    }
    if (char === '#' && !inSingle && !inDouble) {
      return value.slice(0, index).trim()
    }
  }
  return value.trim()
}

function parseScalar(rawValue = '') {
  const value = stripComment(String(rawValue).trim())
  if (!value) {
    return ''
  }
  if (value === 'null' || value === '~') {
    return ''
  }
  if (value.startsWith('"') && value.endsWith('"')) {
    try {
      return JSON.parse(value)
    } catch {
      return value.slice(1, -1)
    }
  }
  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1).replace(/''/g, "'")
  }
  return value
}

function formatScalar(value) {
  return JSON.stringify(String(value ?? ''))
}

function keyValue(line) {
  const trimmed = line.trim()
  const separator = trimmed.indexOf(':')
  if (separator < 0) {
    return null
  }
  return {
    key: trimmed.slice(0, separator).trim(),
    value: parseScalar(trimmed.slice(separator + 1))
  }
}

function lineHasKey(line, key) {
  return line.trim().startsWith(`${key}:`)
}

function findTopLevelSection(lines, name) {
  const start = lines.findIndex((line) => indentation(line) === 0 && line.trim() === `${name}:`)
  if (start < 0) {
    return [-1, -1]
  }

  let end = lines.length
  for (let index = start + 1; index < lines.length; index += 1) {
    const trimmed = lines[index].trim()
    if (trimmed && indentation(lines[index]) === 0 && !trimmed.startsWith('- ') && /^[A-Za-z_][A-Za-z0-9_-]*:/.test(trimmed)) {
      end = index
      break
    }
  }
  return [start, end]
}

function firstListItemIndent(lines, start, end) {
  for (let index = start; index < end; index += 1) {
    if (lines[index].trim().startsWith('- ')) {
      return indentation(lines[index])
    }
  }
  return -1
}

function parseCharacters(lines) {
  const [start, end] = findTopLevelSection(lines, 'characters')
  if (start < 0) {
    return []
  }

  const itemIndent = firstListItemIndent(lines, start + 1, end)
  if (itemIndent < 0) {
    return []
  }
  const propertyIndent = itemIndent + 2
  const characters = []
  let current = null
  for (let index = start + 1; index < end; index += 1) {
    const line = lines[index]
    if (!line.trim()) {
      continue
    }

    if (indentation(line) === itemIndent && line.trim().startsWith('- ')) {
      if (current) {
        characters.push(current)
      }
      current = {}
      const item = keyValue(line.trim().slice(2))
      if (item) {
        current[item.key] = item.value
      }
      continue
    }

    if (current && indentation(line) === propertyIndent && !line.trim().startsWith('- ')) {
      const item = keyValue(line)
      if (item) {
        current[item.key] = item.value
      }
    }
  }
  if (current) {
    characters.push(current)
  }
  return characters.filter((character) => character.id || character.name)
}

function parseLine(lines, startIndex, endIndex) {
  const line = {}
  const propertyIndent = indentation(lines[startIndex]) + 2
  const first = lines[startIndex].trim().slice(2)
  const firstItem = keyValue(first)
  if (firstItem) {
    line[firstItem.key] = firstItem.value
  }

  for (let index = startIndex + 1; index < endIndex; index += 1) {
    if (indentation(lines[index]) !== propertyIndent) {
      continue
    }
    const item = keyValue(lines[index])
    if (item) {
      line[item.key] = item.value
    }
  }
  return line
}

function parseScene(lines, startIndex, endIndex) {
  const scene = { lines: [] }
  const sceneIndent = indentation(lines[startIndex])
  const propertyIndent = sceneIndent + 2
  const first = lines[startIndex].trim().slice(2)
  const firstItem = keyValue(first)
  if (firstItem) {
    scene[firstItem.key] = firstItem.value
  }

  let inLines = false
  let lineStart = -1
  for (let index = startIndex + 1; index < endIndex; index += 1) {
    const line = lines[index]
    const indent = indentation(line)
    const trimmed = line.trim()

    if (indent === propertyIndent && trimmed === 'lines:') {
      inLines = true
      continue
    }

    if (!inLines && indent === propertyIndent && !trimmed.startsWith('- ')) {
      const item = keyValue(line)
      if (item) {
        scene[item.key] = item.value
      }
      continue
    }

    if (inLines && indent === propertyIndent && !trimmed.startsWith('- ') && trimmed !== 'lines:') {
      inLines = false
      const item = keyValue(line)
      if (item) {
        scene[item.key] = item.value
      }
      continue
    }

    if (inLines && indent === propertyIndent && trimmed.startsWith('- ')) {
      if (lineStart >= 0) {
        scene.lines.push(parseLine(lines, lineStart, index))
      }
      lineStart = index
    }
  }

  if (lineStart >= 0) {
    scene.lines.push(parseLine(lines, lineStart, endIndex))
  }
  return scene
}

function parseScenes(lines) {
  const [scriptStart, scriptEnd] = findTopLevelSection(lines, 'script')
  if (scriptStart < 0) {
    return []
  }

  const scenesStart = lines.findIndex(
    (line, index) => index > scriptStart && index < scriptEnd && indentation(line) === 2 && line.trim() === 'scenes:'
  )
  if (scenesStart < 0) {
    return []
  }

  const sceneIndent = firstListItemIndent(lines, scenesStart + 1, scriptEnd)
  if (sceneIndent < 0) {
    return []
  }
  const sceneIndexes = []
  for (let index = scenesStart + 1; index < scriptEnd; index += 1) {
    if (indentation(lines[index]) === sceneIndent && lines[index].trim().startsWith('- ')) {
      sceneIndexes.push(index)
    }
  }

  return sceneIndexes.map((startIndex, index) => {
    const endIndex = sceneIndexes[index + 1] || scriptEnd
    return parseScene(lines, startIndex, endIndex)
  })
}

export function parseScriptView(yamlContent) {
  const lines = String(yamlContent || '').split(/\r?\n/)
  const characters = parseCharacters(lines)
  const scenes = parseScenes(lines)

  return {
    characters,
    scenes,
    parseError: yamlContent && scenes.length === 0 ? '未能从 YAML 中读取 script.scenes。' : ''
  }
}

export function updateSceneLineText(scriptView, sceneId, lineId, text) {
  return {
    ...scriptView,
    scenes: scriptView.scenes.map((scene) =>
      scene.id === sceneId
        ? {
            ...scene,
            lines: scene.lines.map((line) => (line.id === lineId ? { ...line, text } : line))
          }
        : scene
    )
  }
}

export function updateSceneLineCharacter(scriptView, sceneId, lineId, characterId) {
  const character = scriptView.characters.find((item) => item.id === characterId)
  return {
    ...scriptView,
    scenes: scriptView.scenes.map((scene) =>
      scene.id === sceneId
        ? {
            ...scene,
            lines: scene.lines.map((line) =>
              line.id === lineId ? { ...line, character_id: characterId, speaker: character?.name || line.speaker } : line
            )
          }
        : scene
    )
  }
}

function findSceneBlock(lines, sceneId) {
  const [scriptStart, scriptEnd] = findTopLevelSection(lines, 'script')
  if (scriptStart < 0) {
    return [-1, -1]
  }

  const scenesStart = lines.findIndex(
    (line, index) => index > scriptStart && index < scriptEnd && indentation(line) === 2 && line.trim() === 'scenes:'
  )
  if (scenesStart < 0) {
    return [-1, -1]
  }

  const sceneIndent = firstListItemIndent(lines, scenesStart + 1, scriptEnd)
  if (sceneIndent < 0) {
    return [-1, -1]
  }

  const sceneStarts = []
  for (let index = scenesStart + 1; index < scriptEnd; index += 1) {
    if (indentation(lines[index]) === sceneIndent && lines[index].trim().startsWith('- ')) {
      sceneStarts.push(index)
    }
  }

  for (let index = 0; index < sceneStarts.length; index += 1) {
    const start = sceneStarts[index]
    const end = sceneStarts[index + 1] || scriptEnd
    const scene = parseScene(lines, start, end)
    if (scene.id === sceneId) {
      return [start, end]
    }
  }
  return [-1, -1]
}

function findLineBlock(lines, sceneStart, sceneEnd, lineId) {
  const scene = parseScene(lines, sceneStart, sceneEnd)
  const lineIds = new Set((scene.lines || []).map((line) => line.id))
  if (!lineIds.has(lineId)) {
    return [-1, -1]
  }

  const propertyIndent = indentation(lines[sceneStart]) + 2
  const linesStart = lines.findIndex(
    (line, index) => index > sceneStart && index < sceneEnd && indentation(line) === propertyIndent && line.trim() === 'lines:'
  )
  if (linesStart < 0) {
    return [-1, -1]
  }

  const lineIndent = firstListItemIndent(lines, linesStart + 1, sceneEnd)
  if (lineIndent < 0) {
    return [-1, -1]
  }

  for (let index = sceneStart + 1; index < sceneEnd; index += 1) {
    if (indentation(lines[index]) === lineIndent && lines[index].trim().startsWith('- ')) {
      let end = sceneEnd
      for (let cursor = index + 1; cursor < sceneEnd; cursor += 1) {
        if (indentation(lines[cursor]) === lineIndent && lines[cursor].trim().startsWith('- ')) {
          end = cursor
          break
        }
        if (indentation(lines[cursor]) <= propertyIndent && lines[cursor].trim() && !lines[cursor].trim().startsWith('- ')) {
          end = cursor
          break
        }
      }
      const line = parseLine(lines, index, end)
      if (line.id === lineId) {
        return [index, end, lineIndent + 2]
      }
    }
  }
  return [-1, -1, -1]
}

function upsertScalar(lines, blockStart, blockEnd, indent, key, value) {
  const nextLine = `${' '.repeat(indent)}${key}: ${formatScalar(value)}`
  for (let index = blockStart; index < blockEnd; index += 1) {
    if (indentation(lines[index]) === indent && lineHasKey(lines[index], key)) {
      lines[index] = nextLine
      return blockEnd
    }
  }
  lines.splice(blockStart + 1, 0, nextLine)
  return blockEnd + 1
}

export function serializeScriptViewToYaml(yamlContent, scriptView) {
  const lines = String(yamlContent || '').split(/\r?\n/)

  for (const scene of scriptView.scenes || []) {
    const [sceneStart, sceneEnd] = findSceneBlock(lines, scene.id)
    if (sceneStart < 0) {
      continue
    }

    let currentSceneEnd = sceneEnd
    for (const scriptLine of scene.lines || []) {
      const [lineStart, lineEnd, linePropertyIndent] = findLineBlock(lines, sceneStart, currentSceneEnd, scriptLine.id)
      if (lineStart < 0) {
        continue
      }

      let currentLineEnd = upsertScalar(lines, lineStart, lineEnd, linePropertyIndent, 'text', scriptLine.text || '')
      currentSceneEnd += currentLineEnd - lineEnd

      if ((scriptLine.type || 'action') === 'dialogue') {
        const beforeCharacterEnd = currentLineEnd
        currentLineEnd = upsertScalar(lines, lineStart, currentLineEnd, linePropertyIndent, 'character_id', scriptLine.character_id || '')
        currentSceneEnd += currentLineEnd - beforeCharacterEnd
        const beforeSpeakerEnd = currentLineEnd
        currentLineEnd = upsertScalar(lines, lineStart, currentLineEnd, linePropertyIndent, 'speaker', scriptLine.speaker || '')
        currentSceneEnd += currentLineEnd - beforeSpeakerEnd
      }
    }
  }

  return lines.join('\n')
}
