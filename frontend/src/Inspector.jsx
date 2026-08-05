import { useState } from 'react'

import { findComponent, removeComponent, renameComponentId } from './model'

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function ComponentInspector({ project, id, onChange, onSelect }) {
  const component = findComponent(project, id)
  const [idDraft, setIdDraft] = useState(id)
  if (!component) return null

  const edit = (fn) => onChange((draft) => fn(findComponent(draft, id)))
  const partNumbers = Object.keys(project.parts ?? {})

  const commitId = () => {
    if (idDraft === id) return
    onChange((draft) => {
      if (!renameComponentId(draft, id, idDraft.trim())) return
    })
    onSelect({ type: 'component', id: idDraft.trim() })
  }

  return (
    <div className="inspector">
      <h3>{component.children?.length ? 'Assembly' : 'Block'}</h3>
      <Field label="id">
        <input
          value={idDraft}
          onChange={(e) => setIdDraft(e.target.value)}
          onBlur={commitId}
          onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
        />
      </Field>
      <Field label="Name">
        <input
          value={component.name}
          onChange={(e) => edit((c) => (c.name = e.target.value))}
        />
      </Field>
      <Field label="Qty">
        <input
          type="number"
          min="1"
          value={component.qty ?? 1}
          onChange={(e) => edit((c) => (c.qty = Math.max(1, Number(e.target.value) || 1)))}
        />
      </Field>
      <Field label="Part">
        <input
          list="part-numbers"
          value={component.part ?? ''}
          placeholder="(no part)"
          onChange={(e) => edit((c) => {
            const value = e.target.value.trim()
            if (value) c.part = value
            else delete c.part
          })}
        />
        <datalist id="part-numbers">
          {partNumbers.map((pn) => (
            <option key={pn} value={pn} />
          ))}
        </datalist>
      </Field>
      {!component.part && (
        <>
          <Field label="Cost">
            <input
              type="number"
              min="0"
              step="0.01"
              value={component.cost ?? ''}
              onChange={(e) => edit((c) => {
                if (e.target.value === '') delete c.cost
                else c.cost = Number(e.target.value)
              })}
            />
          </Field>
          <Field label="Weight (g)">
            <input
              type="number"
              min="0"
              value={component.weight_g ?? ''}
              onChange={(e) => edit((c) => {
                if (e.target.value === '') delete c.weight_g
                else c.weight_g = Number(e.target.value)
              })}
            />
          </Field>
          <Field label="Link">
            <input
              value={component.link ?? ''}
              onChange={(e) => edit((c) => {
                if (e.target.value === '') delete c.link
                else c.link = e.target.value
              })}
            />
          </Field>
        </>
      )}
      <button
        className="danger"
        onClick={() => {
          onChange((draft) => removeComponent(draft, id))
          onSelect(null)
        }}
      >
        Delete {component.children?.length ? 'assembly' : 'block'}
      </button>
    </div>
  )
}

function ConnectionInspector({ project, index, onChange, onSelect }) {
  const connection = project.connections?.[index]
  if (!connection) return null
  return (
    <div className="inspector">
      <h3>Connection</h3>
      <div className="connection-ends">
        {connection.from} → {connection.to}
      </div>
      <Field label="Label">
        <input
          value={connection.label ?? ''}
          placeholder="e.g. 12V, SPI"
          onChange={(e) => onChange((draft) => {
            const c = draft.connections[index]
            if (e.target.value === '') delete c.label
            else c.label = e.target.value
          })}
        />
      </Field>
      <button
        className="danger"
        onClick={() => {
          onChange((draft) => draft.connections.splice(index, 1))
          onSelect(null)
        }}
      >
        Delete connection
      </button>
    </div>
  )
}

export default function Inspector({ project, selection, onChange, onSelect }) {
  if (!selection) {
    return (
      <div className="inspector inspector-empty">
        Select a block or connection to edit it. Drag a block into an assembly to
        move it; drag onto empty canvas to move it to the top level.
      </div>
    )
  }
  if (selection.type === 'component') {
    return (
      <ComponentInspector
        key={selection.id}
        project={project}
        id={selection.id}
        onChange={onChange}
        onSelect={onSelect}
      />
    )
  }
  return (
    <ConnectionInspector
      key={selection.index}
      project={project}
      index={selection.index}
      onChange={onChange}
      onSelect={onSelect}
    />
  )
}
