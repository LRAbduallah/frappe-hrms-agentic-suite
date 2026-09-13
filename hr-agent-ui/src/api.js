const getBaseUrl = () => {
  return import.meta.env.VITE_API_BASE_URL || ''
}

export const api = {
  baseUrl: getBaseUrl(),

  async getHealth() {
    const res = await fetch(`${getBaseUrl()}/health`)
    return res.json()
  },

  async getReady() {
    const res = await fetch(`${getBaseUrl()}/ready`)
    return res.json()
  },

  async getModels() {
    const res = await fetch(`${getBaseUrl()}/v1/models`)
    return res.json()
  },

  async getApprovals(sessionId) {
    const url = sessionId
      ? `${getBaseUrl()}/v1/approvals?session_id=${encodeURIComponent(sessionId)}`
      : `${getBaseUrl()}/v1/approvals`
    const res = await fetch(url)
    return res.json()
  },

  async approveRequest(approvalId, decision = {}) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    })
    return res.json()
  },

  async rejectRequest(approvalId, decision = {}) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    })
    return res.json()
  },

  async dryRunApproval(approvalId) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/dry-run`, {
      method: 'POST',
    })
    return res.json()
  },

  // Streaming chat handler compliant with standard OpenAI SSE specification
  async sendChat({ messages, stream = true, sessionId = null }, onChunk, onDone, onError) {
    try {
      const res = await fetch(`${getBaseUrl()}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: import.meta.env.VITE_MODEL_NAME || 'hr-agent',
          messages: messages.map(m => ({
            role: m.role,
            content: m.content,
          })),
          stream,
          session_id: sessionId,
        }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server responded with ${res.status}`)
      }

      if (!stream) {
        const data = await res.json()
        const content = data.choices?.[0]?.message?.content || ''
        if (onChunk) onChunk(content)
        if (onDone) onDone(content)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunkText = decoder.decode(value, { stream: true })
        const lines = chunkText.split('\n')

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data: ')) continue

          const payload = trimmed.replace('data: ', '').trim()
          if (payload === '[DONE]') {
            if (onDone) onDone(accumulated)
            return
          }

          try {
            const parsed = JSON.parse(payload)
            const token = parsed.choices?.[0]?.delta?.content || ''
            if (token) {
              accumulated += token
              if (onChunk) onChunk(token, accumulated)
            }
          } catch (e) {
            // Ignore incomplete frames
          }
        }
      }

      if (onDone) onDone(accumulated)
    } catch (err) {
      if (onError) onError(err)
    }
  },

  // ── Session Management ───────────────────────────────────────────────────

  async getSessions() {
    const res = await fetch(`${getBaseUrl()}/v1/sessions`)
    if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`)
    return res.json()
  },

  async createSession() {
    const res = await fetch(`${getBaseUrl()}/v1/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) throw new Error(`Failed to create session: ${res.status}`)
    return res.json()
  },

  async getSession(sessionId) {
    const res = await fetch(`${getBaseUrl()}/v1/sessions/${encodeURIComponent(sessionId)}`)
    if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`)
    return res.json()
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${getBaseUrl()}/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error(`Failed to delete session: ${res.status}`)
  },
}

