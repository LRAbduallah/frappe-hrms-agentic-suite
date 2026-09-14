import React, { useCallback, useEffect, useState } from 'react'
import {
  Check,
  ChevronRight,
  Clock3,
  Mail,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  Workflow,
  X,
} from 'lucide-react'
import { api } from '../api'

const EMAIL_VIEWS = [
  { id: 'all', label: 'All emails' },
  { id: 'pending', label: 'Needs approval' },
  { id: 'sent', label: 'Sent' },
]

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatStatus(value) {
  return (value || 'unknown').replaceAll('_', ' ')
}

function StatusBadge({ status }) {
  const normalized = (status || '').toLowerCase()
  const icon = normalized === 'sent' || normalized === 'completed'
    ? <Check size={11} />
    : normalized === 'pending_review' || normalized === 'running'
      ? <Clock3 size={11} />
      : null

  return (
    <span className={`workflow-status workflow-status-${normalized || 'unknown'}`}>
      {icon}
      {formatStatus(status)}
    </span>
  )
}

function Metric({ label, value, tone }) {
  return (
    <div className="workflow-metric">
      <span className="workflow-metric-label">{label}</span>
      <strong className={tone ? `workflow-metric-value workflow-metric-${tone}` : 'workflow-metric-value'}>
        {value}
      </strong>
    </div>
  )
}

export function WorkflowPanel() {
  const [runs, setRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [selectedRun, setSelectedRun] = useState(null)
  const [emails, setEmails] = useState([])
  const [emailView, setEmailView] = useState('all')
  const [loadingRuns, setLoadingRuns] = useState(true)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [action, setAction] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editingEventId, setEditingEventId] = useState(null)
  const [editStatus, setEditStatus] = useState('pending_review')
  const [editMessage, setEditMessage] = useState('')

  const loadRuns = useCallback(async (preferredRunId = null) => {
    setLoadingRuns(true)
    try {
      const data = await api.listWorkflowRuns({ limit: 100 })
      const nextRuns = Array.isArray(data.items) ? data.items : []
      const candidate = preferredRunId
      const nextRunId = candidate && nextRuns.some((run) => run.id === candidate)
        ? candidate
        : nextRuns[0]?.id || null
      setRuns(nextRuns)
      setSelectedRunId(nextRunId)
      setError('')
      return nextRunId
    } catch (err) {
      setError(err.message || 'Could not load workflow runs.')
      return null
    } finally {
      setLoadingRuns(false)
    }
  }, [])

  const loadDetailsForRun = useCallback(async (runId) => {
    if (!runId) {
      setSelectedRun(null)
      setEmails([])
      setLoadingDetails(false)
      return
    }

    setLoadingDetails(true)
    try {
      const [run, emailData] = await Promise.all([
        api.getWorkflowRun(runId),
        api.listWorkflowEmails(runId, { view: emailView }),
      ])
      setSelectedRun(run)
      setEmails(Array.isArray(emailData.items) ? emailData.items : [])
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load workflow details.')
    } finally {
      setLoadingDetails(false)
    }
  }, [emailView])

  const loadDetails = useCallback(
    () => loadDetailsForRun(selectedRunId),
    [loadDetailsForRun, selectedRunId],
  )

  useEffect(() => {
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    loadDetails()
  }, [loadDetails])

  const refresh = async () => {
    setNotice('')
    const nextRunId = await loadRuns(selectedRunId)
    await loadDetailsForRun(nextRunId)
  }

  const handleCreate = async () => {
    setAction('create')
    setError('')
    setNotice('')
    try {
      const summary = await api.triggerWorkflow()
      const nextRunId = await loadRuns(summary.workflow_run_id)
      await loadDetailsForRun(nextRunId)
      setNotice(summary.workflow_run_id
        ? `Workflow run ${summary.workflow_run_id} created.`
        : 'Workflow run created.')
    } catch (err) {
      // The workflow service can persist a failed run before returning an error.
      // Reload so the failed run is visible instead of leaving the old list on screen.
      const nextRunId = await loadRuns()
      await loadDetailsForRun(nextRunId)
      setError(err.message || 'Could not create workflow run.')
    } finally {
      setAction('')
    }
  }

  const handleDeleteRun = async (runId) => {
    if (!window.confirm(`Delete workflow run ${runId} and its email audit records?`)) return
    setAction(`delete-run-${runId}`)
    setError('')
    try {
      await api.deleteWorkflowRun(runId)
      setNotice(`Workflow run ${runId} deleted.`)
      const nextRunId = await loadRuns(selectedRunId === runId ? null : selectedRunId)
      await loadDetailsForRun(nextRunId)
    } catch (err) {
      setError(err.message || 'Could not delete workflow run.')
    } finally {
      setAction('')
    }
  }

  const handleApprove = async (event) => {
    if (!selectedRunId) return
    setAction(`approve-${event.id}`)
    setError('')
    try {
      const updatedEvent = await api.updateWorkflowEmail(selectedRunId, event.id, {
        delivery_status: 'sent',
        provider_message: 'Approved in Workflow audit',
      })
      setEmails((currentEmails) => currentEmails.map((currentEvent) => (
        currentEvent.id === updatedEvent.id ? updatedEvent : currentEvent
      )))
      setNotice(`Email event ${event.id} approved.`)
      await loadRuns(selectedRunId)
      await loadDetailsForRun(selectedRunId)
    } catch (err) {
      setError(err.message || 'Could not approve workflow email.')
    } finally {
      setAction('')
    }
  }

  const beginEdit = (event) => {
    setEditingEventId(event.id)
    setEditStatus(event.delivery_status)
    setEditMessage(event.provider_message || '')
    setError('')
  }

  const handleSaveEdit = async (event) => {
    if (!selectedRunId) return
    setAction(`edit-${event.id}`)
    setError('')
    try {
      const updatedEvent = await api.updateWorkflowEmail(selectedRunId, event.id, {
        delivery_status: editStatus,
        provider_message: editMessage.trim() || null,
      })
      setEmails((currentEmails) => currentEmails.map((currentEvent) => (
        currentEvent.id === updatedEvent.id ? updatedEvent : currentEvent
      )))
      setEditingEventId(null)
      setNotice(`Email event ${event.id} updated.`)
      await loadRuns(selectedRunId)
      await loadDetailsForRun(selectedRunId)
    } catch (err) {
      setError(err.message || 'Could not update workflow email.')
    } finally {
      setAction('')
    }
  }

  const handleDeleteEmail = async (event) => {
    if (!selectedRunId || !window.confirm(`Delete email event ${event.id}?`)) return
    setAction(`delete-email-${event.id}`)
    setError('')
    try {
      await api.deleteWorkflowEmail(selectedRunId, event.id)
      setEmails((currentEmails) => currentEmails.filter((currentEvent) => currentEvent.id !== event.id))
      setNotice(`Email event ${event.id} deleted.`)
      await loadRuns(selectedRunId)
      await loadDetailsForRun(selectedRunId)
    } catch (err) {
      setError(err.message || 'Could not delete workflow email.')
    } finally {
      setAction('')
    }
  }

  const workflowBusy = action === 'create' || loadingRuns || loadingDetails

  return (
    <section className="workflow-panel">
      <div className="workflow-panel-header">
        <div>
          <div className="workflow-eyebrow"><Workflow size={14} /> WORKFLOW AUDIT</div>
          <h1>Leave workflow runs</h1>
          <p>Trigger, review, edit, and approve workflow email events without leaving chat.</p>
        </div>
        <div className="workflow-header-actions">
          {workflowBusy && (
            <span className="workflow-loading-status" role="status" aria-live="polite">
              <span className="workflow-loading-spinner" />
              {action === 'create' ? 'Creating workflow…' : 'Refreshing workflow…'}
            </span>
          )}
          <button className="vercel-btn-secondary workflow-action-button" onClick={refresh} disabled={loadingRuns || loadingDetails}>
            <RefreshCw size={13} className={loadingRuns || loadingDetails ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="vercel-btn-primary workflow-action-button" onClick={handleCreate} disabled={action === 'create'}>
            {action === 'create' ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
            {action === 'create' ? 'Creating…' : 'Create workflow'}
          </button>
        </div>
      </div>

      {(error || notice) && (
        <div className={error ? 'workflow-alert workflow-alert-error' : 'workflow-alert workflow-alert-success'}>
          <span>{error || notice}</span>
          <button onClick={() => { setError(''); setNotice('') }} aria-label="Dismiss notification">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="workflow-layout">
        <aside className="workflow-runs">
          <div className="workflow-section-heading">
            <div>
              <span className="workflow-section-label">Runs</span>
              <span className="workflow-count">{runs.length}</span>
            </div>
            <span className="workflow-muted">Newest first</span>
          </div>
          <div className="workflow-run-list">
            {loadingRuns && runs.length === 0 ? (
              <div className="workflow-empty">Loading workflow runs…</div>
            ) : runs.length === 0 ? (
              <div className="workflow-empty">
                <Workflow size={22} />
                <span>No workflow runs yet.</span>
                <button className="vercel-btn-secondary" onClick={handleCreate}>Create the first run</button>
              </div>
            ) : runs.map((run) => (
              <button
                className={`workflow-run-card${run.id === selectedRunId ? ' is-selected' : ''}`}
                key={run.id}
                onClick={() => setSelectedRunId(run.id)}
              >
                <div className="workflow-run-card-top">
                  <span className="workflow-run-type">{run.workflow_type || 'leave'} workflow</span>
                  <ChevronRight size={14} />
                </div>
                <div className="workflow-run-id">{run.id}</div>
                <div className="workflow-run-card-bottom">
                  <StatusBadge status={run.status} />
                  <span>{formatDate(run.triggered_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </aside>

        <div className="workflow-detail">
          {!selectedRunId ? (
            <div className="workflow-detail-empty">
              <Workflow size={30} />
              <h2>Select a workflow run</h2>
              <p>Create a run to start reviewing its email audit trail.</p>
            </div>
          ) : loadingDetails && !selectedRun ? (
            <div className="workflow-detail-empty">Loading workflow details…</div>
          ) : selectedRun ? (
            <>
              <div className="workflow-detail-header">
                <div>
                  <div className="workflow-eyebrow">RUN ID</div>
                  <h2>{selectedRun.id}</h2>
                  <span className="workflow-detail-date">Triggered {formatDate(selectedRun.triggered_at)}</span>
                </div>
                <div className="workflow-detail-actions">
                  <StatusBadge status={selectedRun.status} />
                  <button
                    className="icon-button icon-button-danger"
                    onClick={() => handleDeleteRun(selectedRun.id)}
                    disabled={action === `delete-run-${selectedRun.id}`}
                    title="Delete workflow run"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="workflow-metrics">
                <Metric label="Employees" value={selectedRun.total_employees} />
                <Metric label="Sent" value={selectedRun.sent_count} tone="success" />
                <Metric label="Needs approval" value={selectedRun.pending_review_count} tone="pending" />
                <Metric label="Failed" value={selectedRun.failed_count} tone="error" />
              </div>

              <div className="workflow-email-section">
                <div className="workflow-email-toolbar">
                  <div>
                    <span className="workflow-section-label">Email audit</span>
                    <span className="workflow-count">{emails.length}</span>
                  </div>
                  <div className="workflow-email-tabs">
                    {EMAIL_VIEWS.map((view) => (
                      <button
                        className={emailView === view.id ? 'is-active' : ''}
                        key={view.id}
                        onClick={() => setEmailView(view.id)}
                      >
                        {view.label}
                      </button>
                    ))}
                  </div>
                </div>

                {emails.length === 0 ? (
                  <div className="workflow-empty workflow-empty-inline">
                    <Mail size={18} />
                    <span>No email events in this view.</span>
                  </div>
                ) : (
                  <div className="workflow-email-list">
                    {emails.map((event) => {
                      const isEditing = editingEventId === event.id
                      const isBusy = action === `approve-${event.id}` || action === `edit-${event.id}` || action === `delete-email-${event.id}`
                      return (
                        <article className="workflow-email-card" key={event.id}>
                          <div className="workflow-email-card-header">
                            <div className="workflow-email-recipient">
                              <div className="workflow-avatar">{(event.employee_name || '?').slice(0, 1).toUpperCase()}</div>
                              <div>
                                <strong>{event.employee_name}</strong>
                                <span>{event.employee_email}</span>
                              </div>
                            </div>
                            <div className="workflow-email-card-meta">
                              <StatusBadge status={event.delivery_status} />
                              <span className="workflow-event-id">Event #{event.id}</span>
                            </div>
                          </div>
                          <div className="workflow-email-content">
                            <strong>{event.subject}</strong>
                            <p>{event.body}</p>
                          </div>
                          <div className="workflow-email-facts">
                            <span>Risk: <strong>{formatStatus(event.risk_category)}</strong></span>
                            <span>Remaining leave: <strong>{event.remaining_leave}</strong></span>
                            <span>Updated: <strong>{formatDate(event.updated_at)}</strong></span>
                          </div>

                          {isEditing ? (
                            <div className="workflow-edit-form">
                              <label>
                                Delivery status
                                <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)}>
                                  <option value="pending_review">Needs approval</option>
                                  <option value="sent">Sent</option>
                                  <option value="rejected">Rejected</option>
                                  <option value="failed">Failed</option>
                                </select>
                              </label>
                              <label>
                                Provider message
                                <textarea value={editMessage} onChange={(event) => setEditMessage(event.target.value)} rows={2} />
                              </label>
                              <div className="workflow-edit-actions">
                                <button className="vercel-btn-primary" onClick={() => handleSaveEdit(event)} disabled={isBusy}>
                                  <Check size={13} /> {isBusy ? 'Saving…' : 'Save changes'}
                                </button>
                                <button className="vercel-btn-secondary" onClick={() => setEditingEventId(null)} disabled={isBusy}>
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="workflow-email-actions">
                              {event.delivery_status === 'pending_review' && (
                                <button className="vercel-btn-primary" onClick={() => handleApprove(event)} disabled={isBusy}>
                                  <Send size={13} /> {isBusy ? 'Approving…' : 'Approve'}
                                </button>
                              )}
                              <button className="vercel-btn-secondary" onClick={() => beginEdit(event)} disabled={isBusy}>
                                Edit event
                              </button>
                              <button className="icon-button icon-button-danger" onClick={() => handleDeleteEmail(event)} disabled={isBusy} title="Delete email event">
                                <Trash2 size={14} />
                              </button>
                            </div>
                          )}
                        </article>
                      )
                    })}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </section>
  )
}
