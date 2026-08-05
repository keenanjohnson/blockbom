import { Handle, Position } from '@xyflow/react'

export function LeafNode({ data, selected }) {
  const { component } = data
  return (
    <div className={`leaf-node${selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Left} />
      <div className="leaf-name">
        {component.qty > 1 && <span className="qty-badge">{component.qty}x</span>}
        {component.name}
      </div>
      {component.part && <div className="leaf-part">{component.part}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export function AssemblyNode({ data, selected }) {
  const { component } = data
  return (
    <div className={`assembly-node${selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Left} />
      <div className="assembly-title">
        {component.qty > 1 && <span className="qty-badge">{component.qty}x</span>}
        {component.name}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export const nodeTypes = { leaf: LeafNode, assembly: AssemblyNode }
