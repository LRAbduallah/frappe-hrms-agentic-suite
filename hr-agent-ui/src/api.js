const getBaseUrl = () => {
  return import.meta.env.VITE_API_BASE_URL || ''
}

const getWorkflowBaseUrl = () => {
  return import.meta.env.VITE_WORKFLOW_API_BASE_URL || ''
}

const requestOptions = (options = {}) => ({
  ...options,
  credentials: 'include',
})

const workflowRequestOptions = (options = {}) => requestOptions({
  cache: 'no-store',
  ...options,
})

export const api = {
  baseUrl: getBaseUrl(),

  async getCurrentUser() {
    const res = await fetch(`${getBaseUrl()}/auth/me`, requestOptions())
    if (!res.ok) throw new Error('Not authenticated')
    return res.json()
  },

  async login(username, password) {
    const res = await fetch(`${getBaseUrl()}/auth/login`, requestOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }))
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Invalid username or password')
    }
    return res.json()
  },

  async logout() {
    await fetch(`${getBaseUrl()}/auth/logout`, requestOptions({ method: 'POST' }))
  },

  async getHealth() {
    const res = await fetch(`${getBaseUrl()}/health`, requestOptions())
    return res.json()
  },

  async getReady() {
    const res = await fetch(`${getBaseUrl()}/ready`, requestOptions())
    return res.json()
  },

  async getModels() {
    const res = await fetch(`${getBaseUrl()}/v1/models`, requestOptions())
    return res.json()
  },

  async getApprovals(sessionId) {
    const url = sessionId
      ? `${getBaseUrl()}/v1/approvals?session_id=${encodeURIComponent(sessionId)}`
      : `${getBaseUrl()}/v1/approvals`
    const res = await fetch(url, requestOptions())
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to load approvals (${res.status})`)
    return data
  },

  async approveRequest(approvalId, decision = {}) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/approve`, requestOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    }))
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || data.message || `Approval failed (${res.status})`)
    return data
  },

  async rejectRequest(approvalId, decision = {}) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/reject`, requestOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    }))
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || data.message || `Rejection failed (${res.status})`)
    return data
  },

  async dryRunApproval(approvalId) {
    const res = await fetch(`${getBaseUrl()}/v1/approvals/${approvalId}/dry-run`, requestOptions({
      method: 'POST',
    }))
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || data.message || `Dry run failed (${res.status})`)
    return data
  },

  // Streaming chat handler compliant with standard OpenAI SSE specification
  async sendChat({ messages, stream = true, sessionId = null }, onChunk, onDone, onError, onStatus) {
    try {
      const res = await fetch(`${getBaseUrl()}/v1/chat/completions`, requestOptions({
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
      }))

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
      let pending = ''
      let finished = false

      const processLine = (line) => {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data:')) return

        const payload = trimmed.slice(5).trim()
        if (payload === '[DONE]') {
          finished = true
          return
        }

        try {
          const parsed = JSON.parse(payload)
          const status = parsed.agent_status?.message
          if (status && onStatus) onStatus(status)
          const token = parsed.choices?.[0]?.delta?.content || ''
          if (token) {
            accumulated += token
            if (onChunk) onChunk(token, accumulated)
          }
        } catch {
          // A complete SSE line should contain valid JSON; leave malformed data visible in logs.
          console.warn('Ignoring malformed chat SSE payload')
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        pending += decoder.decode(value, { stream: true })
        const lines = pending.split('\n')
        pending = lines.pop() || ''

        for (const line of lines) {
          processLine(line)
          if (finished) break
        }
        if (finished) break
      }

      pending += decoder.decode()
      if (!finished && pending.trim()) processLine(pending)
      if (onDone) onDone(accumulated)
    } catch (err) {
      if (onError) onError(err)
    }
  },

  // ── Session Management ───────────────────────────────────────────────────

  async getSessions() {
    const res = await fetch(`${getBaseUrl()}/v1/sessions`, requestOptions())
    if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`)
    return res.json()
  },

  async createSession() {
    const res = await fetch(`${getBaseUrl()}/v1/sessions`, requestOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }))
    if (!res.ok) throw new Error(`Failed to create session: ${res.status}`)
    return res.json()
  },

  async getSession(sessionId) {
    const res = await fetch(`${getBaseUrl()}/v1/sessions/${encodeURIComponent(sessionId)}`, requestOptions())
    if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`)
    return res.json()
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${getBaseUrl()}/v1/sessions/${encodeURIComponent(sessionId)}`, requestOptions({
      method: 'DELETE',
    }))
    if (!res.ok) throw new Error(`Failed to delete session: ${res.status}`)
  },

  // ── Leave workflow audit ─────────────────────────────────────────────────

  async listWorkflowRuns({ status, workflowType, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })
    if (status) params.set('status', status)
    if (workflowType) params.set('workflow_type', workflowType)

    const res = await fetch(`${getWorkflowBaseUrl()}/workflows?${params}`, workflowRequestOptions())
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to load workflow runs (${res.status})`)
    return data
  },

  async triggerWorkflow() {
    const res = await fetch(`${getWorkflowBaseUrl()}/workflows/trigger`, workflowRequestOptions({
      method: 'POST',
    }))
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to create workflow run (${res.status})`)
    return data
  },

  async getWorkflowRun(runId) {
    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}`,
      workflowRequestOptions(),
    )
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to load workflow run (${res.status})`)
    return data
  },

  async deleteWorkflowRun(runId) {
    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}`,
      workflowRequestOptions({ method: 'DELETE' }),
    )
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to delete workflow run (${res.status})`)
    }
  },

  async listWorkflowEmails(runId, { deliveryStatus, limit = 100, offset = 0, view = 'all' } = {}) {
    const endpoint = view === 'sent'
      ? 'sent-emails'
      : view === 'pending'
        ? 'pending-emails'
        : 'emails'
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })
    if (deliveryStatus) params.set('delivery_status', deliveryStatus)

    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}/${endpoint}?${params}`,
      workflowRequestOptions(),
    )
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to load workflow emails (${res.status})`)
    return data
  },

  async getWorkflowEmail(runId, eventId) {
    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}/emails/${encodeURIComponent(eventId)}`,
      workflowRequestOptions(),
    )
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to load workflow email (${res.status})`)
    return data
  },

  async updateWorkflowEmail(runId, eventId, payload) {
    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}/emails/${encodeURIComponent(eventId)}`,
      workflowRequestOptions({
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    )
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `Failed to update workflow email (${res.status})`)
    return data
  },

  async deleteWorkflowEmail(runId, eventId) {
    const res = await fetch(
      `${getWorkflowBaseUrl()}/workflows/${encodeURIComponent(runId)}/emails/${encodeURIComponent(eventId)}`,
      workflowRequestOptions({ method: 'DELETE' }),
    )
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to delete workflow email (${res.status})`)
    }
  },
}
