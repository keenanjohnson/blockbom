import { useCallback, useEffect, useState } from 'react'

import { getProject, putProject } from './api'
import { addComponent, findComponent } from './model'
import DiagramCanvas from './DiagramCanvas'
import Inspector from './Inspector'
import TablePanel from './TablePanel'

function money(value, complete) {
  const formatted = value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return complete ? formatted : `≥ ${formatted}`
}

export default function App() {
  const [payload, setPayload] = useState(null)
  const [project, setProject] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState(null)
  const [view, setView] = useState('diagram')
  const [selection, setSelection] = useState(null)

  useEffect(() => {
    getProject()
      .then((data) => {
        setPayload(data)
        setProject(data.project)
      })
      .catch((e) => setError(String(e.message ?? e)))
  }, [])

  const onChange = useCallback((mutate) => {
    setProject((current) => {
      const draft = structuredClone(current)
      mutate(draft)
      return draft
    })
    setDirty(true)
  }, [])

  const save = useCallback(async () => {
    if (!project) return
    try {
      const data = await putProject(project)
      setPayload(data)
      setProject(data.project)
      setDirty(false)
      setError(null)
    } catch (e) {
      setError(String(e.message ?? e))
    }
  }, [project])

  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault()
        save()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [save])

  if (error && !project) return <div className="fatal">{error}</div>
  if (!project) return <div className="fatal">Loading…</div>

  const rollup = payload?.rollup

  const addBlock = () => {
    let newId
    onChange((draft) => {
      const selected =
        selection?.type === 'component' ? findComponent(draft, selection.id) : null
      const parentId = selected?.children?.length ? selected.id : null
      newId = addComponent(draft, parentId)
    })
    setSelection({ type: 'component', id: newId })
  }

  const addAssembly = () => {
    onChange((draft) => {
      const groupId = addComponent(draft, null)
      const group = findComponent(draft, groupId)
      group.name = 'New assembly'
      group.children = [{ id: `${groupId}_child`, name: 'New block', qty: 1 }]
    })
  }

  return (
    <div className="app">
      <header>
        <div className="title">
          <h1>{project.name}</h1>
          {dirty && <span className="dirty-chip">unsaved</span>}
        </div>
        <div className="stats">
          {rollup && (
            <>
              <div className="stat">
                <span className="stat-label">cost</span>
                <span className="stat-value">
                  {money(rollup.total_cost, rollup.cost_complete)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">weight</span>
                <span className="stat-value">
                  {money(rollup.total_weight_g, rollup.weight_complete)} g
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">parts</span>
                <span className="stat-value">{rollup.part_count}</span>
              </div>
              {dirty && <span className="stat-note">as of last save</span>}
            </>
          )}
        </div>
        <div className="actions">
          <button onClick={addBlock}>+ Block</button>
          <button onClick={addAssembly}>+ Assembly</button>
          <div className="view-toggle">
            <button
              className={view === 'diagram' ? 'active' : ''}
              onClick={() => setView('diagram')}
            >
              Diagram
            </button>
            <button
              className={view === 'table' ? 'active' : ''}
              onClick={() => setView('table')}
            >
              Table
            </button>
          </div>
          <button className="primary" onClick={save} disabled={!dirty}>
            Save
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {payload?.problems?.length > 0 && (
        <div className="problems-banner">
          {payload.problems.map((problem, i) => (
            <div key={i}>{problem}</div>
          ))}
        </div>
      )}

      <main>
        {view === 'diagram' ? (
          <>
            <div className="canvas">
              <DiagramCanvas
                project={project}
                onChange={onChange}
                selection={selection}
                onSelect={setSelection}
              />
            </div>
            <aside>
              <Inspector
                project={project}
                selection={selection}
                onChange={onChange}
                onSelect={setSelection}
              />
            </aside>
          </>
        ) : (
          <TablePanel project={project} onChange={onChange} />
        )}
      </main>
    </div>
  )
}
