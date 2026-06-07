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

function findTopLevelSection(lines, name) {
  const start = lines.findIndex((line) => indentation(line) === 0 && line.trim() === `${name}:`)
  if (start < 0) {
    return [-1, -1]
  }

  let end = lines.length
  for (let index = start + 1; index < lines.length; index += 1) {
    if (lines[index].trim() && indentation(lines[index]) === 0) {
      end = index
      break
    }
  }
  return [start, end]
}

function parseCharacters(lines) {
  const [start, end] = findTopLevelSection(lines, 'characters')
  if (start < 0) {
    return []
  }

  const characters = []
  let current = null
  for (let index = start + 1; index < end; index += 1) {
    const line = lines[index]
    if (!line.trim()) {
      continue
    }

    if (indentation(line) === 2 && line.trim().startsWith('- ')) {
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

    if (current && indentation(line) === 4) {
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
  const first = lines[startIndex].trim().slice(2)
  const firstItem = keyValue(first)
  if (firstItem) {
    line[firstItem.key] = firstItem.value
  }

  for (let index = startIndex + 1; index < endIndex; index += 1) {
    if (indentation(lines[index]) !== 10) {
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

    if (indent === 6 && trimmed === 'lines:') {
      inLines = true
      continue
    }

    if (!inLines && indent === 6) {
      const item = keyValue(line)
      if (item) {
        scene[item.key] = item.value
      }
      continue
    }

    if (inLines && indent === 8 && trimmed.startsWith('- ')) {
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

  const sceneIndexes = []
  for (let index = scenesStart + 1; index < scriptEnd; index += 1) {
    if (indentation(lines[index]) === 4 && lines[index].trim().startsWith('- ')) {
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
