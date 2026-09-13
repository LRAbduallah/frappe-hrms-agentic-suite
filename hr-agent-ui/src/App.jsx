import React, { useState, useEffect, useCallback } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatInterface } from './components/ChatInterface'
import { ApprovalsPanel } from './components/ApprovalsPanel'
import { api } from './api'
import { Activity, LogOut, Shield, SidebarClose, SidebarOpen, Sparkles } from 'lucide-react'

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.login(username, password)
      onLogin()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-layout">
        <section className="login-welcome">
          <div className="login-eyebrow">
            <span className="login-status-dot" />
            HRMS OPERATIONS AGENT
          </div>
          <h1>Make every HR operation feel effortless.</h1>
          <p className="login-intro">
            Ask questions, coordinate approvals, and take action across your HRMS
            workspace with an agent that understands your operations.
          </p>
          <div className="login-highlights">
            <div>
              <Sparkles size={16} />
              <span>Intelligent HR workflows</span>
            </div>
            <div>
              <Shield size={16} />
              <span>Human approval controls</span>
            </div>
            <div>
              <Activity size={16} />
              <span>Connected to your HRMS</span>
            </div>
          </div>
        </section>

        <form onSubmit={submit} className="vercel-card login-card">
          <div style={{ marginBottom: '24px' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, marginBottom: '6px' }}>Welcome back</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Sign in to your operations workspace</div>
          </div>
          <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '6px' }}>
            Username
          </label>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="auth-input"
            required
          />
          <label style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '12px', margin: '16px 0 6px' }}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            className="auth-input"
            required
          />
          {error && <div style={{ color: '#ff6b6b', fontSize: '12px', marginTop: '14px' }}>{error}</div>}
          <button type="submit" className="vercel-btn-primary" disabled={submitting} style={{ width: '100%', marginTop: '20px' }}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
          <div className="login-card-footer">
            Secure workspace access
          </div>
        </form>
      </div>
    </div>
  )
}

export function App() {
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState('Thinking')
  const [approvals, setApprovals] = useState([])
  const [approvalsLoading, setApprovalsLoading] = useState(false)
  const [showApprovals, setShowApprovals] = useState(true)
  const [statusInfo, setStatusInfo] = useState({
    healthy: true,
    model: 'gpt-4o-mini',
    mcpToolsCount: 0,
  })

  // ── Session state ─────────────────────────────────────────────────────────
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)

  useEffect(() => {
    api.getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false))
  }, [])

  // ── Fetch sessions list ───────────────────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const data = await api.getSessions()
      if (Array.isArray(data)) setSessions(data)
    } catch (e) {
      console.error('Sessions fetch failed:', e)
    } finally {
      setSessionsLoading(false)
    }
  }, [])

  // ── Create a brand-new session ────────────────────────────────────────────
  const handleNewSession = useCallback(async () => {
    try {
      const { session_id } = await api.createSession()
      setCurrentSessionId(session_id)
      setMessages([])
      await fetchSessions()
    } catch (e) {
      console.error('Create session failed:', e)
      // Fallback: generate a client-side UUID (backend will persist on first message)
      setCurrentSessionId(crypto.randomUUID())
      setMessages([])
    }
  }, [fetchSessions])

  // ── Resume an existing session ────────────────────────────────────────────
  const handleSessionSelect = useCallback(async (sessionId) => {
    if (sessionId === currentSessionId) return
    try {
      const detail = await api.getSession(sessionId)
      setCurrentSessionId(sessionId)
      // Rehydrate messages from the Strands session history
      const rehydrated = (detail.messages || []).map((m, idx) => ({
        id: `session-${sessionId}-${idx}`,
        role: m.role,
        content: m.content,
      }))
      setMessages(rehydrated)
    } catch (e) {
      console.error('Load session failed:', e)
    }
  }, [currentSessionId])

  // ── Delete a session ──────────────────────────────────────────────────────
  const handleDeleteSession = useCallback(async (sessionId, e) => {
    e.stopPropagation()
    try {
      await api.deleteSession(sessionId)
      if (sessionId === currentSessionId) {
        setCurrentSessionId(null)
        setMessages([])
      }
      await fetchSessions()
    } catch (err) {
      console.error('Delete session failed:', err)
    }
  }, [currentSessionId, fetchSessions])

  // ── Poll server readiness ─────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const ready = await api.getReady()
      setStatusInfo({
        healthy: true,
        model: ready.model || 'gpt-4o-mini',
        mcpToolsCount: ready.discovered_mcp_tools || 0,
      })
    } catch {
      setStatusInfo((prev) => ({ ...prev, healthy: false }))
    }
  }, [])

  // ── Poll approvals ────────────────────────────────────────────────────────
  const fetchApprovals = useCallback(async () => {
    setApprovalsLoading(true)
    try {
      const data = await api.getApprovals()
      if (Array.isArray(data)) setApprovals(data)
    } catch (e) {
      console.error('Approvals fetch failed:', e)
    } finally {
      setApprovalsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!user) return undefined
    fetchStatus()
    fetchApprovals()
    fetchSessions()
    const approvalsInterval = setInterval(fetchApprovals, 5000)
    const sessionsInterval = setInterval(fetchSessions, 10000)
    return () => {
      clearInterval(approvalsInterval)
      clearInterval(sessionsInterval)
    }
  }, [user, fetchStatus, fetchApprovals, fetchSessions])

  if (authLoading) {
    return <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg-app)', color: 'var(--text-secondary)' }}>Loading…</div>
  }

  if (!user) {
    return <LoginScreen onLogin={() => api.getCurrentUser().then(setUser)} />
  }

  const handleInputChange = (e) => {
    setInput(e.target.value)
  }

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || input
    if (!query.trim() || isLoading) return

    // Ensure we always have a session ID before sending
    let sessionId = currentSessionId
    if (!sessionId) {
      try {
        const { session_id } = await api.createSession()
        sessionId = session_id
        setCurrentSessionId(session_id)
        await fetchSessions()
      } catch {
        sessionId = crypto.randomUUID()
        setCurrentSessionId(sessionId)
      }
    }

    const userMsg = { id: Date.now().toString(), role: 'user', content: query.trim() }
    const assistantMsgId = (Date.now() + 1).toString()
    const assistantMsg = { id: assistantMsgId, role: 'assistant', content: '' }

    const updatedMessages = [...messages, userMsg]
    setMessages([...updatedMessages, assistantMsg])
    setInput('')
    setIsLoading(true)
    setAgentStatus('Thinking')

    await api.sendChat(
      { messages: updatedMessages, stream: true, sessionId },
      (chunk, accumulated) => {
        setAgentStatus('Writing response')
        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, content: accumulated } : msg))
        )
      },
      () => {
        setIsLoading(false)
        setAgentStatus('')
        fetchApprovals()
        // Refresh sessions list so the new session title appears
        fetchSessions()
      },
      (error) => {
        setIsLoading(false)
        setAgentStatus('')
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: `Error: ${error.message || 'Execution error.'}` }
              : msg
          )
        )
      },
      (status) => setAgentStatus(status)
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    handleSendMessage()
  }

  const handleApprove = async (id) => {
    await api.approveRequest(id, { approved_by: 'hr_manager', comment: 'Approved via Virtus Studio' })
    await fetchApprovals()
  }

  const handleReject = async (id) => {
    await api.rejectRequest(id, { approved_by: 'hr_manager', comment: 'Rejected via Virtus Studio' })
    await fetchApprovals()
  }

  const handleDryRun = async (id) => {
    await api.dryRunApproval(id)
    await fetchApprovals()
  }

  const pendingCount = approvals.filter((a) => a.status === 'PENDING').length

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        background: 'var(--bg-app)',
        overflow: 'hidden',
      }}
    >
      {/* Left Sidebar */}
      <Sidebar
        statusInfo={statusInfo}
        sessions={sessions}
        sessionsLoading={sessionsLoading}
        currentSessionId={currentSessionId}
        onNewSession={handleNewSession}
        onSessionSelect={handleSessionSelect}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main App */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minWidth: 0,
        }}
      >
        {/* Navigation Bar */}
        <div
          style={{
            height: '48px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            background: 'var(--bg-surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>
              Frappe HRMS Operations
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>/</span>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {currentSessionId ? currentSessionId : 'No active session'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{user.username}</span>
            <button
              onClick={async () => {
                await api.logout()
                setUser(null)
              }}
              className="vercel-btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', fontSize: '12px' }}
            >
              <LogOut size={13} />
              <span>Sign out</span>
            </button>
            <button
              onClick={() => setShowApprovals(!showApprovals)}
              className="vercel-btn-secondary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                fontSize: '12px',
              }}
            >
              <Shield size={13} />
              <span>Approvals</span>
              {pendingCount > 0 && (
                <span
                  style={{
                    background: '#f5a623',
                    color: '#000',
                    borderRadius: '4px',
                    padding: '0 5px',
                    fontSize: '10px',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {pendingCount}
                </span>
              )}
              {showApprovals ? <SidebarClose size={13} /> : <SidebarOpen size={13} />}
            </button>
          </div>
        </div>

        {/* Workspace Body */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <div style={{ flex: 1, height: '100%', minWidth: 0 }}>
            <ChatInterface
              messages={messages}
              input={input}
              handleInputChange={handleInputChange}
              handleSubmit={handleSubmit}
              isLoading={isLoading}
              agentStatus={agentStatus}
              stop={() => setIsLoading(false)}
              onResetChat={handleNewSession}
              onSelectPrompt={(p) => handleSendMessage(p)}
            />
          </div>

          {/* Right Approvals Flyout */}
          {showApprovals && (
            <div style={{ width: '350px', height: '100%', flexShrink: 0 }}>
              <ApprovalsPanel
                approvals={approvals}
                onApprove={handleApprove}
                onReject={handleReject}
                onDryRun={handleDryRun}
                onRefresh={fetchApprovals}
                loading={approvalsLoading}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
