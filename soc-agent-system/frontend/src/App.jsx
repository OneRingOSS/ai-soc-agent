import { useState, useEffect } from 'react'
import axios from 'axios'
import { Chart as ChartJS, ArcElement, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { Doughnut, Bar } from 'react-chartjs-2'
import useWebSocket from './hooks/useWebSocket'
import ThreatItem from './components/ThreatItem'
import './App.css'

// Register ChartJS components
ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

function App() {
  const [threats, setThreats] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // 'all' or 'review'

  // WebSocket connection for real-time updates
  const { connected, lastMessage } = useWebSocket('ws://localhost:8000/ws')

  // Fetch initial data
  useEffect(() => {
    fetchThreats()
    fetchAnalytics()
  }, [])

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        const message = JSON.parse(lastMessage)

        // Handle different message types
        if (message.type === 'initial_batch') {
          // Initial batch of threats - replace current threats
          if (message.data && Array.isArray(message.data)) {
            setThreats(message.data)
            fetchAnalytics()
          }
        } else if (message.type === 'new_threat') {
          // New threat - add to top of list
          if (message.data) {
            setThreats(prev => [message.data, ...prev].slice(0, 50))
            fetchAnalytics()
          }
        } else {
          // Legacy format - assume it's a direct threat object
          if (message.id && message.signal) {
            setThreats(prev => [message, ...prev].slice(0, 50))
            fetchAnalytics()
          }
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }
  }, [lastMessage])

  const fetchThreats = async () => {
    try {
      const response = await axios.get('/api/threats?limit=20')
      setThreats(response.data)
      setLoading(false)
    } catch (err) {
      setError('Failed to fetch threats')
      setLoading(false)
    }
  }

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get('/api/analytics')
      setAnalytics(response.data)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
    }
  }

  const triggerThreat = async (scenario) => {
    try {
      await axios.post('/api/threats/trigger', { scenario })
    } catch (err) {
      console.error('Failed to trigger threat:', err)
    }
  }

  const toggleFilter = (filterType) => {
    setFilter(filter === filterType ? 'all' : filterType)
  }

  // Filter threats based on current filter
  const filteredThreats = filter === 'review'
    ? threats.filter(threat => threat.requires_human_review)
    : threats

  if (loading) {
    return <div className="loading">Loading SOC Dashboard...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="app">
      <div className={`connection-status ${connected ? 'status-connected' : 'status-disconnected'}`}>
        {connected ? '● Connected' : '○ Disconnected'}
      </div>

      <header className="header">
        <h1>🛡️ SOC Agent System</h1>
        <p>Multi-Agent Threat Intelligence Dashboard</p>
      </header>

      <div className="dashboard">
        {/* Metrics */}
        {analytics && (
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>Total Threats</h3>
              <div className="value">{analytics.total_threats}</div>
            </div>
            <div className="metric-card">
              <h3>Customers Affected</h3>
              <div className="value">{analytics.customers_affected}</div>
            </div>
            <div className="metric-card">
              <h3>Avg Processing Time</h3>
              <div className="value">{analytics.average_processing_time_ms}ms</div>
            </div>
            <div
              className={`metric-card ${filter === 'review' ? 'metric-card-active' : ''}`}
              onClick={() => toggleFilter('review')}
              style={{ cursor: 'pointer' }}
            >
              <h3>Requires Review {filter === 'review' && '✓'}</h3>
              <div className="value">{analytics.threats_requiring_review}</div>
            </div>
          </div>
        )}

        {/* Charts */}
        {analytics && (
          <div className="charts-grid">
            <div className="chart-card">
              <h3>Threats by Type</h3>
              <Doughnut
                data={{
                  labels: Object.keys(analytics.threats_by_type),
                  datasets: [{
                    data: Object.values(analytics.threats_by_type),
                    backgroundColor: [
                      '#646cff', '#7bc62d', '#f5a623', '#ff6b6b', '#4ecdc4', '#95e1d3'
                    ],
                  }]
                }}
                options={{ responsive: true, maintainAspectRatio: true }}
              />
            </div>
            <div className="chart-card">
              <h3>Threats by Severity</h3>
              <Bar
                data={{
                  labels: Object.keys(analytics.threats_by_severity),
                  datasets: [{
                    label: 'Count',
                    data: Object.values(analytics.threats_by_severity),
                    backgroundColor: ['#7bc62d', '#f5a623', '#ff6b6b', '#ff3838'],
                  }]
                }}
                options={{ responsive: true, maintainAspectRatio: true }}
              />
            </div>
          </div>
        )}

        {/* Trigger Buttons */}
        <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <button onClick={() => triggerThreat('bot_attack')}>Trigger Bot Attack</button>
          <button onClick={() => triggerThreat('crypto_surge')}>Trigger Crypto Surge</button>
          <button onClick={() => triggerThreat('geo_impossible')}>Trigger Impossible Travel</button>
          <button onClick={() => triggerThreat('critical_threat')} className="btn-critical">
            🚨 Trigger Critical Threat
          </button>
          <button onClick={() => triggerThreat(null)}>Trigger Random</button>
        </div>

        {/* Threats List */}
        <div className="threats-list">
          <h2>
            {filter === 'review' ? 'Threats Requiring Review' : 'Recent Threats'}
            {filter === 'review' && (
              <button
                onClick={() => setFilter('all')}
                style={{ marginLeft: '1rem', fontSize: '0.9rem', padding: '0.3rem 0.8rem' }}
              >
                Clear Filter
              </button>
            )}
          </h2>
          {filteredThreats.length === 0 ? (
            <p style={{ color: 'rgba(255,255,255,0.6)', padding: '2rem', textAlign: 'center' }}>
              {filter === 'review'
                ? 'No threats requiring review.'
                : 'No threats detected yet. Click a button above to generate a threat.'}
            </p>
          ) : (
            filteredThreats.map(threat => (
              <ThreatItem key={threat.id} threat={threat} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default App
