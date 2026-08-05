// Pure helpers over the project object (the JSON served by /api/project).
// All mutating helpers expect a fresh copy (App clones before mutating).

export function walkComponents(components, fn, level = 0, parent = null) {
  for (const component of components ?? []) {
    fn(component, level, parent)
    walkComponents(component.children, fn, level + 1, component)
  }
}

export function findComponent(project, id) {
  let found = null
  walkComponents(project.components, (c) => {
    if (c.id === id) found = c
  })
  return found
}

export function subtreeIds(component) {
  const ids = []
  walkComponents([component], (c) => ids.push(c.id))
  return ids
}

export function allIds(project) {
  const ids = []
  walkComponents(project.components, (c) => ids.push(c.id))
  return ids
}

export function nextId(project, base) {
  const ids = new Set(allIds(project))
  let n = 1
  while (ids.has(`${base}${n}`)) n += 1
  return `${base}${n}`
}

// Detach a component from wherever it is; returns it (or null).
export function detachComponent(project, id) {
  function detachFrom(list) {
    const index = list.findIndex((c) => c.id === id)
    if (index >= 0) return list.splice(index, 1)[0]
    for (const component of list) {
      if (component.children) {
        const found = detachFrom(component.children)
        if (found) return found
      }
    }
    return null
  }
  return detachFrom(project.components)
}

// Remove a component and its subtree, plus any connections touching it.
export function removeComponent(project, id) {
  const removed = detachComponent(project, id)
  if (!removed) return
  const gone = new Set(subtreeIds(removed))
  project.connections = (project.connections ?? []).filter(
    (edge) => !gone.has(edge.from) && !gone.has(edge.to),
  )
}

// Move a component under a new parent (null = root). No-ops on cycles.
export function reparentComponent(project, id, newParentId) {
  if (id === newParentId) return
  const component = findComponent(project, id)
  if (!component) return
  if (newParentId && subtreeIds(component).includes(newParentId)) return
  const detached = detachComponent(project, id)
  if (!detached) return
  if (newParentId === null) {
    project.components.push(detached)
  } else {
    const parent = findComponent(project, newParentId)
    if (!parent) {
      project.components.push(detached)
      return
    }
    parent.children = parent.children ?? []
    parent.children.push(detached)
  }
}

export function addComponent(project, parentId) {
  const id = nextId(project, 'block')
  const component = { id, name: 'New block', qty: 1 }
  if (parentId) {
    const parent = findComponent(project, parentId)
    parent.children = parent.children ?? []
    parent.children.push(component)
  } else {
    project.components.push(component)
  }
  return id
}

export function renameComponentId(project, oldId, newId) {
  if (!newId || oldId === newId) return false
  if (allIds(project).includes(newId)) return false
  const component = findComponent(project, oldId)
  if (!component) return false
  component.id = newId
  for (const edge of project.connections ?? []) {
    if (edge.from === oldId) edge.from = newId
    if (edge.to === oldId) edge.to = newId
  }
  return true
}

export function renamePartNumber(project, oldPn, newPn) {
  if (!newPn || oldPn === newPn) return false
  if (project.parts?.[newPn]) return false
  project.parts[newPn] = project.parts[oldPn]
  delete project.parts[oldPn]
  walkComponents(project.components, (c) => {
    if (c.part === oldPn) c.part = newPn
  })
  return true
}
