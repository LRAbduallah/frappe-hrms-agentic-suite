import React, { useState } from 'react'
import {
  Users,
  CalendarCheck,
  FileBarChart,
  Mail,
  Activity,
  Server,
  Layers,
  Plus,
  Trash2,
  MessageSquare,
} from 'lucide-react'

const SPECIALISTS = [
  {
    id: 'employee_specialist',
    name: 'Employee Specialist',
    icon: <Users size={14} />,
    desc: 'Directory lookup & disambiguation',
  },
  {
    id: 'leave_attendance_specialist',
    name: 'Leave & Attendance Specialist',
    icon: <CalendarCheck size={14} />,
    desc: 'Authoritative balances & absence audit',
  },
  {
    id: 'reporting_specialist',
    name: 'Reporting Specialist',
    icon: <FileBarChart size={14} />,
    desc: 'Department metrics & anomaly analysis',
  },
  {
    id: 'communication_specialist',
    name: 'Communication Specialist',
    icon: <Mail size={14} />,
    desc: 'Personalized notifications & reminders',
  },
]

/** A small filled triangle pointing up (▲) or down (▼) */
function TriangleIcon({ open }) {
  return (
    <svg
      width="8"
      height="8"
      viewBox="0 0 8 8"
      style={{
        flexShrink: 0,
        transition: 'transform 0.2s ease',
        transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
      }}
    >
      {/* Filled triangle pointing up */}
      <polygon points="4,1 7,7 1,7" fill="currentColor" />
    </svg>
  )
}

function formatRelativeTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  return `${diffDays}d ago`
}

export function Sidebar({
  statusInfo,
  sessions = [],
  sessionsLoading = false,
  currentSessionId = null,
  onNewSession,
  onSessionSelect,
  onDeleteSession,
}) {
  const [systemOpen, setSystemOpen] = useState(true)
  const [specialistsOpen, setSpecialistsOpen] = useState(true)

  return (
    <div
      style={{
        width: '260px',
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* ── Brand Header ─────────────────────────────────────────────────── */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: '24px',
            height: '24px',
            background: '#ffffff',
            color: '#000000',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2.5l8.2 4.75v9.5L12 21.5l-8.2-4.75v-9.5L12 2.5zm0 3.1L6.5 8.8v6.4l5.5 3.2 5.5-3.2V8.8L12 5.6z"/>
            <circle cx="12" cy="12" r="2.2"/>
          </svg>
        </div>
        <div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Virtus Agent
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontStyle: 'italic'}}>
            Powered by strands
          </div>
        </div>
      </div>

      {/* ── Sessions Panel ────────────────────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {/* Sessions Header + New Chat button */}
        <div
          style={{
            padding: '10px 18px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <MessageSquare size={12} /> Sessions
          </div>
          <button
            onClick={onNewSession}
            title="New Chat"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: 500,
              color: 'var(--text-secondary)',
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)'
              e.currentTarget.style.borderColor = 'var(--text-muted)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-secondary)'
              e.currentTarget.style.borderColor = 'var(--border-subtle)'
            }}
          >
            <Plus size={11} />
            New
          </button>
        </div>

        {/* Sessions Scrollable List */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0 10px 10px',
          }}
        >
          {sessionsLoading && sessions.length === 0 ? (
            <div
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                padding: '8px 8px',
                fontStyle: 'italic',
              }}
            >
              Loading…
            </div>
          ) : sessions.length === 0 ? (
            <div
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                padding: '8px 8px',
                fontStyle: 'italic',
              }}
            >
              No sessions yet. Start a chat!
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {sessions.map((session) => {
                const isActive = session.session_id === currentSessionId
                return (
                  <div
                    key={session.session_id}
                    onClick={() => onSessionSelect(session.session_id)}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      background: isActive
                        ? 'rgba(255,255,255,0.06)'
                        : 'transparent',
                      border: isActive
                        ? '1px solid rgba(255,255,255,0.08)'
                        : '1px solid transparent',
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: '6px',
                      transition: 'background 0.15s ease, border-color 0.15s ease',
                      position: 'relative',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                        e.currentTarget.querySelector('.session-delete-btn').style.opacity = '1'
                      } else {
                        e.currentTarget.querySelector('.session-delete-btn').style.opacity = '1'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent'
                      }
                      e.currentTarget.querySelector('.session-delete-btn').style.opacity = '0'
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: isActive ? 500 : 400,
                          color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          lineHeight: 1.3,
                        }}
                      >
                        {session.title}
                      </div>
                      <div
                        style={{
                          fontSize: '10px',
                          color: 'var(--text-muted)',
                          marginTop: '2px',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {session.message_count} msg{session.message_count !== 1 ? 's' : ''} ·{' '}
                        {formatRelativeTime(session.updated_at)}
                      </div>
                    </div>

                    <button
                      className="session-delete-btn"
                      onClick={(e) => onDeleteSession(session.session_id, e)}
                      title="Delete session"
                      style={{
                        opacity: 0,
                        background: 'transparent',
                        border: 'none',
                        padding: '2px',
                        cursor: 'pointer',
                        color: 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        borderRadius: '3px',
                        flexShrink: 0,
                        transition: 'opacity 0.15s ease, color 0.15s ease',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = '#ee0000' }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)' }}
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── System Status (collapsible) ───────────────────────────────────── */}
      <div
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        {/* Section Header — clickable */}
        <button
          onClick={() => setSystemOpen((o) => !o)}
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            padding: '10px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            textAlign: 'left',
          }}
        >
          <TriangleIcon open={systemOpen} />
          <Server size={12} />
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            System Status
          </span>
        </button>

        {systemOpen && (
          <div style={{ padding: '0 18px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Backend</span>
              <span
                className="vercel-badge"
                style={{
                  background: statusInfo?.healthy ? 'rgba(0, 112, 243, 0.1)' : 'rgba(238, 0, 0, 0.1)',
                  color: statusInfo?.healthy ? '#3291ff' : '#ee0000',
                }}
              >
                {statusInfo?.healthy ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>MCP Gateway</span>
              <span
                className="vercel-badge"
                style={{ background: 'rgba(80, 227, 194, 0.1)', color: '#50e3c2' }}
              >
                CONNECTED
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Model</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)' }}>
                {statusInfo?.model || 'gpt-4o-mini'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Specialists (collapsible) ─────────────────────────────────────── */}
      <div
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        {/* Section Header — clickable */}
        <button
          onClick={() => setSpecialistsOpen((o) => !o)}
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            padding: '10px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            textAlign: 'left',
          }}
        >
          <TriangleIcon open={specialistsOpen} />
          <Layers size={12} />
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Specialists
          </span>
        </button>

        {specialistsOpen && (
          <div style={{ padding: '0 10px 10px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {SPECIALISTS.map((agent) => (
              <div
                key={agent.id}
                className="vercel-card"
                style={{
                  padding: '8px 10px',
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'flex-start',
                }}
              >
                <div style={{ color: 'var(--text-secondary)', marginTop: '1px' }}>
                  {agent.icon}
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {agent.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.3, marginTop: '2px' }}>
                    {agent.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <div
        style={{
          padding: '12px 18px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          flexShrink: 0,
        }}
      >
        <Activity size={12} />
        <span>HITL GOVERNANCE ACTIVE</span>
      </div>
    </div>
  )
}
