export async function getProject() {
  const res = await fetch('/api/project')
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
  return res.json()
}

export async function putProject(project) {
  const res = await fetch('/api/project', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(project),
  })
  if (!res.ok) {
    const detail = (await res.json()).detail
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}
