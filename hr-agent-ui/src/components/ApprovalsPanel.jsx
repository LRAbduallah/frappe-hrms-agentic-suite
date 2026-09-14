import React, { useState } from 'react'
import {
  Check,
  X,
  Clock,
  Shield,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Terminal,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
} from 'lucide-react'

export function ApprovalsPanel({ approvals, onApprove, onReject, onDryRun, onRefresh, loading, error }) {
  const [filter, setFilter] = useState('ALL')
  const [expandedId, setExpandedId] = useState(null)
  const [actionInProgress, setActionInProgress] = useState(null)
  const [actionError, setActionError] = useState(null)

  const filteredApprovals = approvals.filter((app) => {
    if (filter === 'ALL') return true
    return app.status === filter
  })

  const handleApprove = async (id) => {
    setActionInProgress(id)
    setActionError(null)
    try {
      await onApprove(id)
    } catch (error) {
      setActionError({ id, message: error.message || 'Approval execution failed.' })
    } finally {
      setActionInProgress(null)
    }
  }

  const handleReject = async (id) => {
    setActionInProgress(id)
    setActionError(null)
    try {
      await onReject(id)
    } catch (error) {
      setActionError({ id, message: error.message || 'Rejection failed.' })
    } finally {
      setActionInProgress(null)
    }
  }

  const handleDryRun = async (id) => {
    if (!onDryRun) return
    setActionInProgress(id)
    setActionError(null)
    try {
      await onDryRun(id)
    } catch (error) {
      setActionError({ id, message: error.message || 'Dry run failed.' })
    } finally {
      setActionInProgress(null)
    }
  }

  const renderBadge = (status) => {
    switch (status) {
      case 'PENDING':
        return (
          <span
            className="vercel-badge"
            style={{
              background: 'rgba(245, 166, 35, 0.1)',
              color: '#f5a623',
              border: '1px solid rgba(245, 166, 35, 0.25)',
            }}
          >
            <Clock size={11} /> PENDING
          </span>
        )
      case 'EXECUTED':
      case 'APPROVED':
        return (
          <span
            className="vercel-badge"
            style={{
              background: 'rgba(0, 112, 243, 0.1)',
              color: '#3291ff',
              border: '1px solid rgba(0, 112, 243, 0.25)',
            }}
          >
            <Check size={11} /> EXECUTED
          </span>
        )
      case 'FAILED':
        return (
          <span
            className="vercel-badge"
            style={{
              background: 'rgba(238, 0, 0, 0.15)',
              color: '#ff4d4f',
              border: '1px solid rgba(238, 0, 0, 0.3)',
            }}
          >
            <AlertCircle size={11} /> FAILED
          </span>
        )
      case 'REJECTED':
        return (
          <span
            className="vercel-badge"
            style={{
              background: 'rgba(238, 0, 0, 0.1)',
              color: '#ee0000',
              border: '1px solid rgba(238, 0, 0, 0.25)',
            }}
          >
            <X size={11} /> REJECTED
          </span>
        )
      default:
        return <span className="vercel-badge">{status}</span>
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--bg-surface)',
        borderLeft: '1px solid var(--border-subtle)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={16} color="var(--text-secondary)" />
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Approvals
          </span>
          <span
            style={{
              fontSize: '11px',
              background: 'var(--bg-subtle)',
              border: '1px solid var(--border-subtle)',
              padding: '1px 6px',
              borderRadius: '4px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {approvals.filter((a) => a.status === 'PENDING').length}
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
          }}
          title="Refresh"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Filter Tabs */}
      {error && (
        <div
          style={{
            margin: '10px 14px 0',
            padding: '8px 10px',
            borderRadius: '5px',
            background: 'rgba(238, 0, 0, 0.1)',
            border: '1px solid rgba(238, 0, 0, 0.3)',
            color: '#ff7875',
            fontSize: '11px',
            lineHeight: 1.4,
          }}
        >
          Approval sync failed: {error}
          <button
            onClick={onRefresh}
            style={{
              display: 'block',
              marginTop: '5px',
              padding: 0,
              background: 'none',
              border: 'none',
              color: '#ffaaa8',
              cursor: 'pointer',
              fontSize: '11px',
              textDecoration: 'underline',
            }}
          >
            Retry now
          </button>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          gap: '4px',
          padding: '8px 14px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-app)',
        }}
      >
        {['ALL', 'PENDING', 'EXECUTED', 'REJECTED'].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            style={{
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: 500,
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              background: filter === tab ? 'var(--bg-hover)' : 'transparent',
              color: filter === tab ? 'var(--text-primary)' : 'var(--text-muted)',
              transition: 'all 0.1s ease',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Approvals List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        {filteredApprovals.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '48px 12px',
              color: 'var(--text-muted)',
              fontSize: '13px',
            }}
          >
            No approval requests found.
          </div>
        ) : (
          filteredApprovals.map((req) => {
            const isExpanded = expandedId === req.id
            const isBusy = actionInProgress === req.id
            const workflowSteps = req.tool_name === 'frappe_create_workflow'
              ? (req.arguments?.steps || [])
              : []

            return (
              <div
                key={req.id}
                className="vercel-card"
                style={{
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {req.action}
                  </span>
                  {renderBadge(req.status)}
                </div>

                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {req.reason}
                </div>

                {workflowSteps.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '5px',
                      alignItems: 'center',
                      fontSize: '11px',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>Workflow:</span>
                    {workflowSteps.map((step, index) => (
                      <React.Fragment key={step.id || index}>
                        {index > 0 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
                        <span
                          style={{
                            padding: '2px 6px',
                            borderRadius: '999px',
                            background: 'rgba(80, 227, 194, 0.08)',
                            border: '1px solid rgba(80, 227, 194, 0.18)',
                            color: 'var(--text-primary)',
                          }}
                        >
                          {step.doctype || step.id}
                        </span>
                      </React.Fragment>
                    ))}
                  </div>
                )}

                {req.preflight && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '11px',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: req.preflight.dry_run_passed ? 'rgba(80, 227, 194, 0.08)' : 'rgba(255, 77, 79, 0.08)',
                      border: req.preflight.dry_run_passed ? '1px solid rgba(80, 227, 194, 0.2)' : '1px solid rgba(255, 77, 79, 0.2)',
                      color: req.preflight.dry_run_passed ? '#50e3c2' : '#ff7875',
                    }}
                  >
                    {req.preflight.dry_run_passed ? (
                      <>
                        <CheckCircle2 size={12} />
                        <span>Dry Run: <strong>Passed</strong></span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle size={12} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          Dry Run: <strong>{req.preflight.errors?.[0] || 'Prerequisites missing'}</strong>
                        </span>
                      </>
                    )}
                  </div>
                )}

                {req.status === 'FAILED' && req.result && (
                  <div
                    style={{
                      padding: '6px 8px',
                      borderRadius: '4px',
                      background: 'rgba(238, 0, 0, 0.1)',
                      border: '1px solid rgba(238, 0, 0, 0.3)',
                      color: '#ff6b6b',
                      fontSize: '11px',
                      lineHeight: 1.4,
                    }}
                  >
                    <strong>Execution Error:</strong> {req.result.message || JSON.stringify(req.result)}
                  </div>
                )}

                {actionError?.id === req.id && (
                  <div
                    style={{
                      padding: '6px 8px',
                      borderRadius: '4px',
                      background: 'rgba(238, 0, 0, 0.1)',
                      border: '1px solid rgba(238, 0, 0, 0.3)',
                      color: '#ff6b6b',
                      fontSize: '11px',
                      lineHeight: 1.4,
                    }}
                  >
                    <strong>Request failed:</strong> {actionError.message}
                  </div>
                )}

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    paddingTop: '6px',
                    borderTop: '1px solid var(--border-subtle)',
                  }}
                >
                  <span>#{req.id}</span>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : req.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '2px',
                      fontSize: '11px',
                    }}
                  >
                    {isExpanded ? 'Hide' : 'Payload'}
                    {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  </button>
                </div>

                {isExpanded && (
                  <div
                    style={{
                      marginTop: '4px',
                      padding: '8px',
                      borderRadius: '4px',
                      background: '#000000',
                      border: '1px solid var(--border-subtle)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                      color: '#d4d4d4',
                      overflowX: 'auto',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <Terminal size={11} /> Tool: {req.tool_name}
                    </div>
                    <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                      {JSON.stringify(req.arguments, null, 2)}
                    </pre>

                    {req.preflight?.checks && req.preflight.checks.length > 0 && (
                      <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #222' }}>
                        <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px', letterSpacing: '0.5px' }}>
                          Pre-Flight Dry Run Checks
                        </div>
                        {req.preflight.checks.map((chk, idx) => (
                          <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '11px', marginTop: '3px' }}>
                            {chk.status === 'PASSED' && <CheckCircle2 size={12} color="#50e3c2" style={{ marginTop: '1px', flexShrink: 0 }} />}
                            {chk.status === 'FAILED' && <XCircle size={12} color="#ff4d4f" style={{ marginTop: '1px', flexShrink: 0 }} />}
                            {chk.status === 'WARNING' && <AlertTriangle size={12} color="#f5a623" style={{ marginTop: '1px', flexShrink: 0 }} />}
                            <div>
                              <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{chk.name}: </span>
                              <span style={{ color: 'var(--text-secondary)' }}>{chk.detail}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {req.result && (
                      <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid #222', color: req.status === 'FAILED' ? '#ff6b6b' : '#50e3c2' }}>
                        Result: {JSON.stringify(req.result, null, 2)}
                      </div>
                    )}
                  </div>
                )}

                {req.status === 'PENDING' && (
                  <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                    <button
                      onClick={() => handleDryRun(req.id)}
                      disabled={isBusy}
                      className="vercel-btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Test payload and check Frappe prerequisites"
                    >
                      <Play size={11} /> Test Dry Run
                    </button>
                    <button
                      onClick={() => handleApprove(req.id)}
                      disabled={isBusy}
                      className="vercel-btn-primary"
                      style={{ flex: 1, padding: '4px 8px', fontSize: '12px' }}
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(req.id)}
                      disabled={isBusy}
                      className="vercel-btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '12px' }}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
