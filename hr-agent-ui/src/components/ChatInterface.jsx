import React, { useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowUp,
  RotateCcw,
  Copy,
  Check,
  Cpu,
  Search,
  AlertCircle,
  FileSpreadsheet,
  User,
  Building2,
  Briefcase,
  Mail,
  Calendar,
  DollarSign,
  ChevronRight,
  Sparkles,
  Wallet,
  Plane,
  UserPlus,
  TrendingUp,
  ClipboardList,
  BarChart3,
} from 'lucide-react'

// ── Capabilities that the agent exposes ──────────────────────────────────────
const CAPABILITIES = [
  { icon: <User size={12} />, label: 'Employee Records', desc: 'Search, view, create & update employee profiles' },
  { icon: <Calendar size={12} />, label: 'Leave & Attendance', desc: 'Balances, policies, applications, corrections' },
  { icon: <DollarSign size={12} />, label: 'Payroll', desc: 'Salary slips, payroll entries, bonuses, advances' },
  { icon: <Wallet size={12} />, label: 'Expense Claims', desc: 'Create & track expense claims and travel requests' },
  { icon: <TrendingUp size={12} />, label: 'Lifecycle', desc: 'Onboarding, transfers, promotions, separations' },
  { icon: <UserPlus size={12} />, label: 'Recruitment', desc: 'Job openings, applicants, interviews, offers' },
  { icon: <BarChart3 size={12} />, label: 'Reports & Analytics', desc: 'Headcount, leave utilization, payroll summaries' },
  { icon: <Mail size={12} />, label: 'HR Communications', desc: 'Draft & approve employee notifications' },
]

const QUICK_ACTIONS = [
  {
    icon: <Sparkles size={13} />,
    title: 'What can you do?',
    desc: 'Show me everything you can help with in Frappe HRMS.',
  },
  {
    icon: <Search size={13} />,
    title: 'Employee Lookup',
    desc: 'Find employee HR-EMP-00001 and show their full profile.',
  },
  {
    icon: <DollarSign size={13} />,
    title: 'Generate Salary Slip',
    desc: 'Create a salary slip for HR-EMP-00001 for September 2026.',
  },
  {
    icon: <Calendar size={13} />,
    title: 'Apply Leave',
    desc: 'Submit a casual leave application for HR-EMP-00001 from 2026-09-20 to 2026-09-22.',
  },
  {
    icon: <Wallet size={13} />,
    title: 'Expense Claim',
    desc: 'Create an expense claim for HR-EMP-00001 for travel expenses of ₹5,000.',
  },
  {
    icon: <UserPlus size={13} />,
    title: 'Post Job Opening',
    desc: 'Create a Job Opening for a Senior Python Developer in the Engineering department.',
  },
  {
    icon: <AlertCircle size={13} />,
    title: 'Low Leave Alert',
    desc: 'Which employees have less than 2 days of annual leave remaining?',
  },
  {
    icon: <BarChart3 size={13} />,
    title: 'HR Report',
    desc: 'Give me a department headcount summary and attendance anomalies this month.',
  },
]

/* ─── Section icon map ──────────────────────────────────── */
const SECTION_ICONS = {
  'personal': <User size={13} />,
  'employment': <Briefcase size={13} />,
  'email': <Mail size={13} />,
  'other': <Building2 size={13} />,
  'note': <AlertCircle size={13} />,
  'date': <Calendar size={13} />,
  'salary': <DollarSign size={13} />,
}

function getSectionIcon(title = '') {
  const lower = title.toLowerCase()
  for (const [key, icon] of Object.entries(SECTION_ICONS)) {
    if (lower.includes(key)) return icon
  }
  return <ChevronRight size={13} />
}

/* ─── Status Badge ──────────────────────────────────────── */
function StatusBadge({ children }) {
  const text = String(children).trim().toLowerCase()
  const isActive = text === 'active'
  const isInactive = text === 'inactive' || text === 'left'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: '2px 8px',
        borderRadius: '999px',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.04em',
        background: isActive
          ? 'rgba(0, 200, 100, 0.12)'
          : isInactive
          ? 'rgba(238, 0, 0, 0.12)'
          : 'rgba(255, 166, 35, 0.12)',
        color: isActive ? '#34d399' : isInactive ? '#f87171' : '#f5a623',
        border: isActive
          ? '1px solid rgba(52, 211, 153, 0.25)'
          : isInactive
          ? '1px solid rgba(248, 113, 113, 0.25)'
          : '1px solid rgba(245, 166, 35, 0.25)',
        textTransform: 'uppercase',
      }}
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          background: isActive ? '#34d399' : isInactive ? '#f87171' : '#f5a623',
          flexShrink: 0,
        }}
      />
      {String(children).trim()}
    </span>
  )
}

/* ─── Inline code ───────────────────────────────────────── */
function InlineCode({ children }) {
  return (
    <code
      style={{
        background: 'rgba(255,255,255,0.07)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '4px',
        padding: '1px 6px',
        fontSize: '12px',
        fontFamily: 'var(--font-mono)',
        color: '#93c5fd',
      }}
    >
      {children}
    </code>
  )
}

/* ─── Strong text ───────────────────────────────────────── */
function StrongText({ children }) {
  const text = String(children)
  const lower = text.toLowerCase()

  if (lower === 'active' || lower === 'inactive' || lower === 'left') {
    return <StatusBadge>{text}</StatusBadge>
  }

  return (
    <strong
      style={{
        color: '#e2e8f0',
        fontWeight: 600,
      }}
    >
      {children}
    </strong>
  )
}

/* ─── Markdown Table ────────────────────────────────────── */
function MdTable({ children }) {
  return (
    <div
      style={{
        overflowX: 'auto',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)',
        marginTop: '4px',
        marginBottom: '4px',
      }}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '13px',
          lineHeight: 1.5,
        }}
      >
        {children}
      </table>
    </div>
  )
}

function MdThead({ children }) {
  return (
    <thead
      style={{
        background: 'rgba(255,255,255,0.04)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      {children}
    </thead>
  )
}

function MdTr({ children, ...props }) {
  return (
    <tr
      style={{
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background 0.12s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      {...props}
    >
      {children}
    </tr>
  )
}

function MdTh({ children }) {
  return (
    <th
      style={{
        padding: '8px 12px',
        textAlign: 'left',
        fontSize: '11px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        fontFamily: 'var(--font-mono)',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </th>
  )
}

function MdTd({ children }) {
  return (
    <td
      style={{
        padding: '8px 12px',
        color: 'var(--text-primary)',
        fontSize: '13px',
        verticalAlign: 'top',
      }}
    >
      {children}
    </td>
  )
}

/* ─── Blockquote (Notes) ────────────────────────────────── */
function MdBlockquote({ children }) {
  return (
    <blockquote
      style={{
        background: 'rgba(80, 227, 194, 0.06)',
        border: '1px solid rgba(80, 227, 194, 0.2)',
        borderLeft: '3px solid #50e3c2',
        borderRadius: '6px',
        padding: '10px 14px',
        margin: '4px 0',
        fontSize: '13px',
        color: 'var(--text-secondary)',
        fontStyle: 'normal',
      }}
    >
      {children}
    </blockquote>
  )
}

/* ─── H3 Section Header (Personal Information, etc) ─────── */
function MdH3({ children }) {
  const title = String(children)
  const icon = getSectionIcon(title)
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '7px',
        padding: '6px 0 4px',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '10px',
        marginTop: '18px',
      }}
    >
      <span style={{ color: 'var(--text-muted)' }}>{icon}</span>
      <h3
        style={{
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        {title}
      </h3>
    </div>
  )
}

/* ─── H2 Section Header ──────────────────────────────────── */
function MdH2({ children }) {
  return (
    <h2
      style={{
        fontSize: '15px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '12px',
        marginTop: '20px',
        letterSpacing: '-0.01em',
      }}
    >
      {children}
    </h2>
  )
}

/* ─── H1 ─────────────────────────────────────────────────── */
function MdH1({ children }) {
  return (
    <h1
      style={{
        fontSize: '17px',
        fontWeight: 700,
        color: 'var(--text-primary)',
        marginBottom: '14px',
        letterSpacing: '-0.02em',
      }}
    >
      {children}
    </h1>
  )
}

/* ─── List item ──────────────────────────────────────────── */
function MdLi({ children }) {
  return (
    <li
      style={{
        padding: '3px 0',
        color: 'var(--text-secondary)',
        fontSize: '13.5px',
        lineHeight: 1.6,
        listStyle: 'none',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '8px',
      }}
    >
      <span
        style={{
          width: '4px',
          height: '4px',
          borderRadius: '50%',
          background: 'var(--text-muted)',
          flexShrink: 0,
          marginTop: '9px',
        }}
      />
      <span style={{ flex: 1 }}>{children}</span>
    </li>
  )
}

function MdUl({ children }) {
  return (
    <ul style={{ margin: '4px 0', padding: 0 }}>{children}</ul>
  )
}

function MdOl({ children }) {
  return (
    <ol style={{ margin: '4px 0', padding: '0 0 0 20px', color: 'var(--text-secondary)', fontSize: '13.5px', lineHeight: 1.6 }}>
      {children}
    </ol>
  )
}

/* ─── Paragraph ─────────────────────────────────────────── */
function MdP({ children }) {
  return (
    <p
      style={{
        fontSize: '13.5px',
        lineHeight: 1.7,
        color: 'var(--text-secondary)',
        margin: '4px 0',
      }}
    >
      {children}
    </p>
  )
}

/* ─── Horizontal rule ────────────────────────────────────── */
function MdHr() {
  return (
    <hr
      style={{
        border: 'none',
        borderTop: '1px solid var(--border-subtle)',
        margin: '12px 0',
      }}
    />
  )
}

/* ─── Markdown Components Map ────────────────────────────── */
const MD_COMPONENTS = {
  h1: MdH1,
  h2: MdH2,
  h3: MdH3,
  p: MdP,
  strong: StrongText,
  code({ inline, children, ...props }) {
    if (inline) return <InlineCode {...props}>{children}</InlineCode>
    return (
      <pre
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '12px 14px',
          overflowX: 'auto',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          color: '#93c5fd',
          margin: '6px 0',
        }}
      >
        <code {...props}>{children}</code>
      </pre>
    )
  },
  blockquote: MdBlockquote,
  table: MdTable,
  thead: MdThead,
  tr: MdTr,
  th: MdTh,
  td: MdTd,
  ul: MdUl,
  ol: MdOl,
  li: MdLi,
  hr: MdHr,
  a({ href, children }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: '#60a5fa', textDecoration: 'underline', textDecorationColor: 'rgba(96,165,250,0.3)' }}
      >
        {children}
      </a>
    )
  },
}

/* ─── Message Bubble ─────────────────────────────────────── */
function AssistantMessage({ content }) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        padding: '16px 18px',
        maxWidth: '100%',
        position: 'relative',
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

/* ─── Main Component ─────────────────────────────────────── */
export function ChatInterface({
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  stop,
  onResetChat,
  onSelectPrompt,
}) {
  const [copiedIndex, setCopiedIndex] = React.useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && !isLoading) {
        handleSubmit(e)
      }
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--bg-app)',
        position: 'relative',
      }}
    >
      {/* Message Feed */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div style={{ width: '100%', maxWidth: '720px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {messages.length === 0 ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '440px',
                textAlign: 'center',
                padding: '40px 0',
              }}
            >
              {/* Vercel Logo */}
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  background: '#ffffff',
                  color: '#000000',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '16px',
                  boxShadow: '0 0 20px rgba(255, 255, 255, 0.15)',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 76 65" fill="#000">
                  <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
                </svg>
              </div>

              <h1
                style={{
                  fontSize: '20px',
                  fontWeight: 600,
                  letterSpacing: '-0.02em',
                  color: 'var(--text-primary)',
                  marginBottom: '8px',
                }}
              >
                HR Operations Agent
              </h1>

              <p
                style={{
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                  maxWidth: '480px',
                  lineHeight: 1.5,
                  marginBottom: '20px',
                }}
              >
                Connected to <strong>Frappe HRMS MCP</strong>. I can help with employees, leave & attendance,
                payroll, expense claims, onboarding, recruitment, analytics, and more — all with human-in-the-loop approvals.
              </p>

              {/* Capabilities strip */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '6px',
                  justifyContent: 'center',
                  marginBottom: '28px',
                  maxWidth: '560px',
                }}
              >
                {CAPABILITIES.map((cap, i) => (
                  <div
                    key={i}
                    title={cap.desc}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '999px',
                      fontSize: '11px',
                      color: 'var(--text-secondary)',
                      fontWeight: 500,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>{cap.icon}</span>
                    {cap.label}
                  </div>
                ))}
              </div>

              {/* Quick Actions Grid — 2 col, 4 rows */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '6px',
                  width: '100%',
                }}
              >
                {QUICK_ACTIONS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectPrompt(item.desc)}
                    className="vercel-card"
                    style={{
                      padding: '12px 14px',
                      textAlign: 'left',
                      background: 'var(--bg-surface)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '12px',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {item.icon} {item.title}
                    </div>
                    <div
                      style={{
                        fontSize: '12px',
                        color: 'var(--text-muted)',
                        lineHeight: 1.4,
                      }}
                    >
                      {item.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user'

              return (
                <div
                  key={msg.id || index}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    width: '100%',
                  }}
                >
                  <div
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-muted)',
                      marginBottom: '6px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {isUser ? 'You' : 'Assistant'}
                  </div>

                  {isUser ? (
                    /* User bubble — plain text pill */
                    <div
                      style={{
                        background: 'var(--bg-subtle)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '10px 14px',
                        maxWidth: '85%',
                        color: 'var(--text-primary)',
                        fontSize: '14px',
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {msg.content}
                    </div>
                  ) : (
                    /* Assistant — rich markdown card */
                    <div style={{ width: '100%' }}>
                      <AssistantMessage content={msg.content} />
                      {msg.content && (
                        <div style={{ marginTop: '6px', display: 'flex', gap: '6px' }}>
                          <button
                            onClick={() => handleCopy(msg.content, index)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '11px',
                              padding: '2px 4px',
                              borderRadius: '4px',
                            }}
                          >
                            {copiedIndex === index ? (
                              <>
                                <Check size={11} color="#50e3c2" /> Copied
                              </>
                            ) : (
                              <>
                                <Copy size={11} /> Copy
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}

          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <div
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#0070f3',
                }}
                className="animate-pulse"
              />
              Consulting Frappe HRMS agents...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Bar */}
      <div
        style={{
          padding: '16px 20px 24px',
          display: 'flex',
          justifyContent: 'center',
          background: 'linear-gradient(to top, #000000 70%, transparent 100%)',
        }}
      >
        <div style={{ width: '100%', maxWidth: '720px' }}>
          <form
            onSubmit={handleSubmit}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 8px 6px 14px',
              transition: 'border-color 0.15s ease',
              boxShadow: 'var(--shadow-vercel)',
            }}
          >
            <textarea
              rows={1}
              placeholder="Ask an HR question, investigate attendance, or propose corrections..."
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                resize: 'none',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-sans)',
                fontSize: '13.5px',
                lineHeight: '20px',
                padding: '4px 0',
              }}
            />

            {messages.length > 0 && (
              <button
                type="button"
                onClick={onResetChat}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '4px',
                }}
                title="Clear Conversation"
              >
                <RotateCcw size={14} />
              </button>
            )}

            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="vercel-btn-primary"
              style={{
                width: '32px',
                height: '32px',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '6px',
              }}
            >
              <ArrowUp size={16} />
            </button>
          </form>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '8px',
              fontSize: '11px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              padding: '0 4px',
            }}
          >
            <span>ENDPOINT: /v1/chat/completions</span>
            <span>PRESS ENTER TO SEND</span>
          </div>
        </div>
      </div>
    </div>
  )
}
