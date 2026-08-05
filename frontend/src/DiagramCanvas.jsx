import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
} from '@xyflow/react'

import { layoutProject } from './layout'
import { removeComponent, reparentComponent, walkComponents } from './model'
import { nodeTypes } from './nodes'

// Signature of everything that affects node positions: the hierarchy shape
// and the connection list. Names/qty/parts only change labels.
function structureKey(project) {
  const tree = []
  walkComponents(project.components, (c, level) => tree.push(`${level}:${c.id}`))
  const edges = (project.connections ?? []).map((e) => `${e.from}>${e.to}`)
  return JSON.stringify([tree, edges])
}

export default function DiagramCanvas({ project, onChange, selection, onSelect }) {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const { getIntersectingNodes, fitView } = useReactFlow()
  const selectionRef = useRef(selection)
  selectionRef.current = selection

  // Full ELK layout only when the structure changes...
  const key = structureKey(project)
  const projectRef = useRef(project)
  projectRef.current = project
  useEffect(() => {
    let cancelled = false
    layoutProject(projectRef.current).then(({ nodes, edges }) => {
      if (cancelled) return
      const selected = selectionRef.current
      setNodes(
        nodes.map((node) =>
          selected?.type === 'component' && selected.id === node.id
            ? { ...node, selected: true }
            : node,
        ),
      )
      setEdges(edges)
      setTimeout(() => fitView({ padding: 0.15, duration: 200 }), 60)
    })
    return () => {
      cancelled = true
    }
  }, [key, fitView])

  // ...otherwise just refresh node/edge data in place (labels, qty badges)
  // so typing in the inspector doesn't re-layout or drop the selection.
  useEffect(() => {
    const byId = {}
    walkComponents(project.components, (c) => (byId[c.id] = c))
    setNodes((current) =>
      current.map((node) =>
        byId[node.id] ? { ...node, data: { component: byId[node.id] } } : node,
      ),
    )
    setEdges((current) =>
      current.map((edge) => {
        const connection = (project.connections ?? [])[edge.data.index]
        return connection ? { ...edge, label: connection.label ?? undefined } : edge
      }),
    )
  }, [project])

  const onNodesChange = useCallback(
    (changes) => setNodes((n) => applyNodeChanges(changes, n)),
    [],
  )
  const onEdgesChange = useCallback(
    (changes) => setEdges((e) => applyEdgeChanges(changes, e)),
    [],
  )

  const onConnect = useCallback(
    (connection) =>
      onChange((draft) => {
        draft.connections = draft.connections ?? []
        draft.connections.push({ from: connection.source, to: connection.target })
      }),
    [onChange],
  )

  // Dragging is only meaningful as a reparent gesture: positions are always
  // recomputed by auto-layout afterwards.
  const onNodeDragStop = useCallback(
    (_event, node) => {
      const depths = {}
      const byId = {}
      for (const n of nodes) byId[n.id] = n
      const depthOf = (n) => {
        if (!n.parentId) return 0
        if (!(n.id in depths)) depths[n.id] = depthOf(byId[n.parentId]) + 1
        return depths[n.id]
      }

      const descendants = new Set()
      const collect = (id) => {
        for (const n of nodes) {
          if (n.parentId === id) {
            descendants.add(n.id)
            collect(n.id)
          }
        }
      }
      collect(node.id)

      const target = getIntersectingNodes(node)
        .filter((n) => n.type === 'assembly')
        .filter((n) => n.id !== node.id && !descendants.has(n.id))
        .sort((a, b) => depthOf(byId[b.id]) - depthOf(byId[a.id]))[0]

      const newParent = target ? target.id : null
      const currentParent = node.parentId ?? null
      if (newParent !== currentParent) {
        onChange((draft) => reparentComponent(draft, node.id, newParent))
      } else {
        // Snap back to the computed layout.
        layoutProject(projectRef.current).then(({ nodes }) => setNodes(nodes))
      }
    },
    [nodes, onChange, getIntersectingNodes],
  )

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes, edges: selectedEdges }) => {
      if (selectedNodes.length === 1) {
        onSelect({ type: 'component', id: selectedNodes[0].id })
      } else if (selectedEdges.length === 1) {
        onSelect({ type: 'connection', index: selectedEdges[0].data.index })
      } else {
        onSelect(null)
      }
    },
    [onSelect],
  )

  const onDelete = useCallback(
    ({ nodes: deletedNodes, edges: deletedEdges }) =>
      onChange((draft) => {
        const removedIndices = new Set(deletedEdges.map((e) => e.data.index))
        draft.connections = (draft.connections ?? []).filter(
          (_, index) => !removedIndices.has(index),
        )
        for (const n of deletedNodes) removeComponent(draft, n.id)
      }),
    [onChange],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeDragStop={onNodeDragStop}
      onSelectionChange={onSelectionChange}
      onDelete={onDelete}
      deleteKeyCode={['Backspace', 'Delete']}
      defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed } }}
      proOptions={{ hideAttribution: true }}
      fitView
    >
      <Background gap={20} />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}
