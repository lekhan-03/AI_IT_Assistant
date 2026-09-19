import { useState, useEffect } from 'react'
import { BrainCircuit, Sparkles, Send, Loader2, AlertCircle, CheckCircle2, ChevronRight, BookOpen } from 'lucide-react'
import './index.css'

function App() {
  const [ticketText, setTicketText] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [mode, setMode] = useState('checking...')
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/status')
      .then(r => r.json())
      .then(d => setMode(d.mode))
      .catch(() => setMode('rules-only'))
  }, [])

  const sampleTickets = [
    { label: '01 — Wi-Fi connected, no websites', text: "My laptop is connected to Wi-Fi but I can't access any websites. Teams isn't working either. I have a client call in 20 minutes." },
    { label: '02 — Changed password, Outlook keeps prompting', text: "I changed my password this morning. I can log into my laptop but Outlook keeps asking me for my password." },
    { label: '03 — Laptop extremely slow', text: "My laptop has become extremely slow since this morning. I only have Chrome, Outlook and Teams open." },
    { label: '04 — "Nothing is connecting"', text: "Nothing is connecting since I changed my password." },
    { label: '05 — Printer out of toner', text: "The HP LaserJet Pro on the 4th floor is completely out of toner and says offline. We have a huge meeting in 10 minutes" }
  ]

  const runTriage = async (textToRun = ticketText, hist = history) => {
    if (!textToRun.trim()) {
      setError("Enter a ticket first.")
      return
    }
    setError(null)
    setLoading(true)
    
    try {
      const res = await fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_text: textToRun, history: hist })
      })
      if (!res.ok) throw new Error("Failed to reach server")
      const data = await res.json()
      setResults(data.results)
    } catch (err) {
      setError("Something went wrong reaching the triage service.")
    } finally {
      setLoading(false)
    }
  }

  const handleFollowup = (idx, ans) => {
    const q = results[idx].follow_up_question
    const newHist = [...history, { question: q, answer: ans }]
    setHistory(newHist)
    runTriage(ticketText, newHist)
  }

  const handleNewTicket = () => {
    setTicketText('')
    setHistory([])
    setResults(null)
    setError(null)
  }

  return (
    <div className="app-container">
      <header className="header" style={{ alignItems: 'baseline' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="logo animate-in" style={{ background: 'var(--text-main)', WebkitBackgroundClip: 'text' }}>
            Triage<span style={{ color: 'var(--accent-secondary)' }}>/</span>console
          </div>
          <div className="animate-in" style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'monospace', animationDelay: '0.05s' }}>
            internal IT support assistant
          </div>
          <div className="status-pill animate-in" style={{ animationDelay: '0.1s' }}>
            <div className="status-dot"></div>
            engine: {mode}
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="glass-panel animate-in" style={{ animationDelay: '0.2s' }}>
          <div className="panel-header">
            New ticket
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <textarea
              className="glass-input"
              style={{ minHeight: '130px' }}
              placeholder="Paste or type the support request exactly as the employee wrote it..."
              value={ticketText}
              onChange={e => setTicketText(e.target.value)}
            />
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button 
                className="btn-glow" 
                onClick={() => runTriage()}
                disabled={loading || !ticketText.trim()}
              >
                Analyze ticket
              </button>
              {loading && <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Analyzing…</span>}
              {error && <span style={{ color: 'var(--priority-critical)', fontSize: '12px' }}>{error}</span>}
            </div>

            <div style={{ marginTop: '14px' }}>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                Sample tickets
              </div>
              {sampleTickets.map((s, i) => (
                <button
                  key={i}
                  className="sample-chip"
                  onClick={() => {
                    setTicketText(s.text)
                    setHistory([])
                    setResults(null)
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-panel animate-in" style={{ animationDelay: '0.3s' }}>
          <div className="panel-header">
            Triage result
          </div>
          <div className="panel-body">
            {!results ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)', fontSize: '14px' }}>
                Submit a ticket on the left to see category, priority, missing information and a recommended next step.
              </div>
            ) : (
              <div>
                {history.length > 0 && (
                  <div className="history-log">
                    {history.map((h, i) => (
                      <div key={i} className="history-item">
                        <div className="history-q">Q: {h.question}</div>
                        <div style={{ fontSize: '13px' }}>{h.answer}</div>
                      </div>
                    ))}
                  </div>
                )}
                
                <div style={{ display: 'flex', overflowX: 'auto', gap: '20px', paddingBottom: '10px' }}>
                  {results.map((r, idx) => (
                    <div key={idx} style={{ minWidth: '320px', flex: 1, border: '1px solid var(--border-light)', borderRadius: '4px', padding: '16px', background: 'var(--bg-card)', display: 'flex', flexDirection: 'column' }}>
                      
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '18px' }}>
                        <span className={`badge priority-${r.priority}`}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor' }}></div>
                          {r.priority}
                        </span>
                        <span className="badge">
                          {r.category}
                        </span>
                        {r.kb_reference && (
                          <span className="badge source-badge">
                            📚 Source: {r.kb_reference}
                          </span>
                        )}
                        <span style={{ marginLeft: 'auto', fontSize: '11.5px', color: 'var(--text-muted)', alignSelf: 'center' }}>
                          {r.engine} (conf: {r.confidence})
                        </span>
                      </div>

                      {r.missing_info && r.missing_info.length > 0 && (
                        <div className="result-section" style={{ marginTop: '0', marginBottom: '22px' }}>
                          <h4 style={{ fontSize: '12px', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px', marginBottom: '8px' }}>What's missing</h4>
                          <ul style={{ paddingLeft: '18px', fontSize: '14px', color: 'var(--text-main)', margin: '0' }}>
                            {r.missing_info.map((m, i) => <li key={i} style={{ marginBottom: '5px' }}>{m}</li>)}
                          </ul>
                        </div>
                      )}

                      <div className="result-section" style={{ marginBottom: '22px' }}>
                        <h4 style={{ fontSize: '12px', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px', marginBottom: '8px' }}>{r.needs_followup ? 'Requires Info' : 'Next step'}</h4>
                        {r.needs_followup ? (
                          <div style={{ border: '1px solid var(--priority-high)', background: 'rgba(239, 68, 68, 0.05)', padding: '14px 16px' }}>
                            <div style={{ fontSize: '14.5px', fontWeight: 600, marginBottom: '10px', color: 'var(--text-main)' }}>
                              {r.follow_up_question}
                            </div>
                            <FollowUpForm onSubmit={(ans) => handleFollowup(idx, ans)} loading={loading} />
                          </div>
                        ) : (
                          <div className="highlight-box" style={{ fontSize: '15px' }}>
                            {r.next_step}
                          </div>
                        )}
                      </div>

                      <div className="result-section">
                        <h4 style={{ fontSize: '12px', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px', marginBottom: '8px' }}>Reasoning</h4>
                        <div style={{ fontSize: '14px', color: 'var(--text-main)' }}>
                          {r.reasoning}
                        </div>
                      </div>

                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      <footer style={{ marginTop: '40px', fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-light)', paddingTop: '14px' }}>
        Rule-based reasoning is always explainable and works without an API key. When an AI API key is set, the assistant uses the models for the analysis and falls back to the rule engine automatically if the model output is malformed or unavailable.
      </footer>
    </div>
  )
}

function FollowUpForm({ onSubmit, loading }) {
  const [ans, setAns] = useState('')
  return (
    <div style={{ display: 'flex', gap: '0.5rem' }}>
      <input 
        type="text" 
        className="glass-input" 
        style={{ padding: '0.5rem 1rem' }}
        placeholder="Type the employee's answer..."
        value={ans}
        onChange={e => setAns(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && ans.trim() && !loading && onSubmit(ans.trim())}
      />
      <button 
        className="btn-glow"
        style={{ padding: '0.5rem 1rem' }}
        onClick={() => onSubmit(ans.trim())}
        disabled={loading || !ans.trim()}
      >
        Submit
      </button>
    </div>
  )
}

export default App
