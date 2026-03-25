/**
 * IntelMatchCard Component
 * 
 * Displays threat intelligence matches from VirusTotal and other sources.
 * Wave 5: VirusTotal Package Lookup
 */

export function IntelMatchCard({ intelMatches }) {
  if (!intelMatches || intelMatches.length === 0) {
    return null
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    try {
      return new Date(dateStr).toLocaleDateString()
    } catch {
      return dateStr
    }
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#e74c3c' // High confidence - red
    if (confidence >= 0.5) return '#f5a623' // Medium confidence - orange
    return '#7bc62d' // Low confidence - green
  }

  const getSourceIcon = (source) => {
    const icons = {
      'virustotal': '🛡️',
      'misp': '🔍',
      'alienvault': '👽',
      'threatfox': '🦊'
    }
    return icons[source.toLowerCase()] || '📊'
  }

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h4 style={{ marginBottom: '0.75rem', color: '#646cff' }}>
        🔎 Threat Intelligence Matches
      </h4>
      <div style={{
        padding: '1rem',
        background: '#0a0e27',
        borderRadius: '8px',
        border: '1px solid #2a3f5f'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {intelMatches.map((match, idx) => (
            <div
              key={idx}
              style={{
                background: '#1a2332',
                padding: '0.75rem',
                borderRadius: '6px',
                borderLeft: `4px solid ${getConfidenceColor(match.confidence)}`
              }}
            >
              {/* Header: Source + IOC Type */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem',
                flexWrap: 'wrap',
                gap: '0.5rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.2em' }}>
                    {getSourceIcon(match.source)}
                  </span>
                  <span style={{
                    fontWeight: 'bold',
                    color: '#646cff',
                    textTransform: 'capitalize'
                  }}>
                    {match.source}
                  </span>
                  <span style={{
                    background: '#0a0e27',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    fontSize: '0.8em',
                    color: 'rgba(255,255,255,0.7)',
                    textTransform: 'uppercase'
                  }}>
                    {match.ioc_type}
                  </span>
                </div>

                {/* Confidence Badge */}
                <div style={{
                  background: getConfidenceColor(match.confidence),
                  color: '#fff',
                  padding: '0.3rem 0.6rem',
                  borderRadius: '4px',
                  fontSize: '0.85em',
                  fontWeight: 'bold'
                }}>
                  {(match.confidence * 100).toFixed(0)}% Confidence
                </div>
              </div>

              {/* IOC Value */}
              <div style={{
                fontSize: '0.85em',
                color: 'rgba(255,255,255,0.6)',
                marginBottom: '0.5rem',
                fontFamily: 'monospace',
                wordBreak: 'break-all'
              }}>
                <strong>IOC:</strong> {match.ioc_value}
              </div>

              {/* Description */}
              {match.description && (
                <div style={{
                  fontSize: '0.9em',
                  color: 'rgba(255,255,255,0.9)',
                  marginBottom: '0.5rem',
                  lineHeight: '1.5'
                }}>
                  {match.description}
                </div>
              )}

              {/* Footer: Threat Actor + Date */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.8em',
                color: 'rgba(255,255,255,0.5)',
                marginTop: '0.5rem',
                flexWrap: 'wrap',
                gap: '0.5rem'
              }}>
                {match.threat_actor && (
                  <div>
                    <strong>Threat Actor:</strong> {match.threat_actor}
                  </div>
                )}
                {match.date_added && (
                  <div>
                    <strong>First Seen:</strong> {formatDate(match.date_added)}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Summary Footer */}
        <div style={{
          marginTop: '0.75rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid #2a3f5f',
          fontSize: '0.85em',
          color: 'rgba(255,255,255,0.6)',
          textAlign: 'center'
        }}>
          {intelMatches.length} threat intelligence {intelMatches.length === 1 ? 'match' : 'matches'} found
        </div>
      </div>
    </div>
  )
}

