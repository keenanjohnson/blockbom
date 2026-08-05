import { findComponent, renamePartNumber, walkComponents } from './model'

const PART_FIELDS = [
  ['description', 'Description', 'text'],
  ['supplier', 'Supplier', 'text'],
  ['supplier_pn', 'Supplier PN', 'text'],
  ['link', 'Link', 'text'],
  ['cost', 'Cost', 'number'],
  ['weight_g', 'Weight (g)', 'number'],
]

function PartNumberCell({ pn, onChange }) {
  return (
    <input
      defaultValue={pn}
      onBlur={(e) => {
        const next = e.target.value.trim()
        if (next !== pn) onChange((draft) => renamePartNumber(draft, pn, next))
      }}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
    />
  )
}

export default function TablePanel({ project, onChange }) {
  const rows = []
  walkComponents(project.components, (component, level) => {
    rows.push({ component, level })
  })
  const parts = project.parts ?? {}

  const editComponent = (id, fn) => onChange((draft) => fn(findComponent(draft, id)))
  const editPart = (pn, fn) => onChange((draft) => fn(draft.parts[pn]))

  return (
    <div className="table-panel">
      <section>
        <h3>Components</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th className="num">Qty</th>
              <th>Part</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ component, level }) => (
              <tr key={component.id}>
                <td style={{ paddingLeft: `${0.8 + level * 1.4}rem` }}>
                  <input
                    value={component.name}
                    onChange={(e) =>
                      editComponent(component.id, (c) => (c.name = e.target.value))
                    }
                  />
                </td>
                <td className="num">
                  <input
                    type="number"
                    min="1"
                    value={component.qty ?? 1}
                    onChange={(e) =>
                      editComponent(component.id, (c) => {
                        c.qty = Math.max(1, Number(e.target.value) || 1)
                      })
                    }
                  />
                </td>
                <td>
                  <input
                    list="part-numbers-table"
                    value={component.part ?? ''}
                    placeholder="—"
                    onChange={(e) =>
                      editComponent(component.id, (c) => {
                        const value = e.target.value.trim()
                        if (value) c.part = value
                        else delete c.part
                      })
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <datalist id="part-numbers-table">
          {Object.keys(parts).map((pn) => (
            <option key={pn} value={pn} />
          ))}
        </datalist>
      </section>

      <section>
        <h3>Parts library</h3>
        <table>
          <thead>
            <tr>
              <th>Part Number</th>
              {PART_FIELDS.map(([key, label]) => (
                <th key={key}>{label}</th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {Object.entries(parts).map(([pn, part]) => (
              <tr key={pn}>
                <td>
                  <PartNumberCell pn={pn} onChange={onChange} />
                </td>
                {PART_FIELDS.map(([key, , type]) => (
                  <td key={key}>
                    <input
                      type={type}
                      step={type === 'number' ? '0.01' : undefined}
                      value={part[key] ?? ''}
                      onChange={(e) =>
                        editPart(pn, (p) => {
                          if (e.target.value === '') delete p[key]
                          else p[key] = type === 'number' ? Number(e.target.value) : e.target.value
                        })
                      }
                    />
                  </td>
                ))}
                <td>
                  <button
                    className="danger small"
                    title="Remove part from library"
                    onClick={() => onChange((draft) => delete draft.parts[pn])}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          onClick={() =>
            onChange((draft) => {
              draft.parts = draft.parts ?? {}
              let n = 1
              while (draft.parts[`PART-${n}`]) n += 1
              draft.parts[`PART-${n}`] = {}
            })
          }
        >
          + Add part
        </button>
      </section>
    </div>
  )
}
