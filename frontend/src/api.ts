export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!resp.ok) throw new Error((await resp.text()) || `HTTP ${resp.status}`)
  if (resp.status === 204) return undefined as T
  const text = await resp.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}

export function parseMessage(content: string): { summary: string; bullets: string[] } {
  try {
    const data = JSON.parse(content) as Record<string, unknown>
    const summary = String(data.summary || '')
    const bullets: string[] = []
    for (const key of ['milestones', 'acceptance', 'notes', 'ship_notes', 'required_fixes', 'findings']) {
      const val = data[key]
      if (Array.isArray(val)) {
        for (const item of val.slice(0, 6)) {
          if (typeof item === 'string') bullets.push(item)
          else if (item && typeof item === 'object' && 'item' in item) {
            bullets.push(String((item as { item: string }).item))
          }
        }
      }
    }
    const files = data.files
    if (files && typeof files === 'object') {
      bullets.push(`файлы: ${Object.keys(files as object).slice(0, 8).join(', ')}`)
    }
    return { summary: summary || content.slice(0, 220), bullets }
  } catch {
    return { summary: content.slice(0, 220), bullets: [] }
  }
}
