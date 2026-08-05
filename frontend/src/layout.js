import ELK from 'elkjs/lib/elk.bundled.js'

const elk = new ELK()

export const LEAF_WIDTH = 190
export const LEAF_HEIGHT = 64

function toElkNode(component) {
  const children = component.children ?? []
  if (children.length === 0) {
    return { id: component.id, width: LEAF_WIDTH, height: LEAF_HEIGHT }
  }
  return {
    id: component.id,
    children: children.map(toElkNode),
    layoutOptions: {
      'elk.padding': '[top=44.0,left=16.0,bottom=16.0,right=16.0]',
    },
  }
}

// Compute positions for the whole project with ELK; returns React Flow
// nodes (parents before children, positions relative to parent) and edges.
export async function layoutProject(project) {
  const graph = {
    id: '__root__',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
      'elk.spacing.nodeNode': '32',
      'elk.layered.spacing.nodeNodeBetweenLayers': '56',
    },
    children: (project.components ?? []).map(toElkNode),
    edges: (project.connections ?? []).map((edge, index) => ({
      id: `e${index}`,
      sources: [edge.from],
      targets: [edge.to],
    })),
  }

  const result = await elk.layout(graph)

  const assemblies = new Set()
  const componentsById = {}
  ;(function collect(components) {
    for (const component of components ?? []) {
      componentsById[component.id] = component
      if (component.children?.length) {
        assemblies.add(component.id)
        collect(component.children)
      }
    }
  })(project.components)

  const nodes = []
  ;(function convert(elkChildren, parentId) {
    for (const child of elkChildren ?? []) {
      const isAssembly = assemblies.has(child.id)
      nodes.push({
        id: child.id,
        type: isAssembly ? 'assembly' : 'leaf',
        position: { x: child.x ?? 0, y: child.y ?? 0 },
        data: { component: componentsById[child.id] },
        ...(parentId ? { parentId } : {}),
        ...(isAssembly
          ? { style: { width: child.width, height: child.height }, zIndex: -1 }
          : {}),
      })
      convert(child.children, child.id)
    }
  })(result.children, null)

  const edges = (project.connections ?? []).map((edge, index) => ({
    id: `e${index}`,
    source: edge.from,
    target: edge.to,
    label: edge.label ?? undefined,
    data: { index },
  }))

  return { nodes, edges }
}
