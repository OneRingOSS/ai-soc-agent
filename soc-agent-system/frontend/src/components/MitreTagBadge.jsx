/**
 * MITRE ATT&CK Tag Components
 * Displays MITRE technique tags with color-coding by tactic
 */

// Color mapping for MITRE ATT&CK tactics
// Using distinct, vibrant colors for better visual differentiation
const TACTIC_COLORS = {
  // Enterprise ATT&CK
  'TA0001': { bg: 'rgba(231, 76, 60, 0.2)', border: '#e74c3c', name: 'Initial Access' },        // Red
  'TA0002': { bg: 'rgba(52, 152, 219, 0.2)', border: '#3498db', name: 'Execution' },            // Blue
  'TA0003': { bg: 'rgba(230, 126, 34, 0.2)', border: '#e67e22', name: 'Persistence' },          // Orange
  'TA0004': { bg: 'rgba(155, 89, 182, 0.2)', border: '#9b59b6', name: 'Privilege Escalation' }, // Purple
  'TA0005': { bg: 'rgba(241, 196, 15, 0.2)', border: '#f1c40f', name: 'Defense Evasion' },      // Yellow
  'TA0006': { bg: 'rgba(39, 174, 96, 0.2)', border: '#27ae60', name: 'Credential Access' },     // Green
  'TA0007': { bg: 'rgba(233, 30, 99, 0.2)', border: '#e91e63', name: 'Discovery' },             // Pink
  'TA0008': { bg: 'rgba(103, 58, 183, 0.2)', border: '#673ab7', name: 'Lateral Movement' },     // Indigo
  'TA0009': { bg: 'rgba(0, 188, 212, 0.2)', border: '#00bcd4', name: 'Collection' },            // Cyan
  'TA0010': { bg: 'rgba(149, 165, 166, 0.2)', border: '#95a5a6', name: 'Exfiltration' },        // Gray
  'TA0011': { bg: 'rgba(26, 188, 156, 0.2)', border: '#1abc9c', name: 'Command and Control' },  // Teal
  'TA0040': { bg: 'rgba(192, 57, 43, 0.2)', border: '#c0392b', name: 'Impact' },                // Dark Red

  // Mobile ATT&CK (Android/iOS) - Using same distinct colors
  'TA0027': { bg: 'rgba(231, 76, 60, 0.2)', border: '#e74c3c', name: 'Initial Access' },        // Red
  'TA0028': { bg: 'rgba(52, 152, 219, 0.2)', border: '#3498db', name: 'Execution' },            // Blue
  'TA0029': { bg: 'rgba(230, 126, 34, 0.2)', border: '#e67e22', name: 'Persistence' },          // Orange
  'TA0030': { bg: 'rgba(155, 89, 182, 0.2)', border: '#9b59b6', name: 'Privilege Escalation' }, // Purple
  'TA0031': { bg: 'rgba(241, 196, 15, 0.2)', border: '#f1c40f', name: 'Defense Evasion' },      // Yellow
  'TA0032': { bg: 'rgba(39, 174, 96, 0.2)', border: '#27ae60', name: 'Credential Access' },     // Green
  'TA0033': { bg: 'rgba(233, 30, 99, 0.2)', border: '#e91e63', name: 'Discovery' },             // Pink
  'TA0034': { bg: 'rgba(103, 58, 183, 0.2)', border: '#673ab7', name: 'Lateral Movement' },     // Indigo
  'TA0035': { bg: 'rgba(0, 188, 212, 0.2)', border: '#00bcd4', name: 'Collection' },            // Cyan
  'TA0036': { bg: 'rgba(149, 165, 166, 0.2)', border: '#95a5a6', name: 'Exfiltration' },        // Gray
  'TA0037': { bg: 'rgba(26, 188, 156, 0.2)', border: '#1abc9c', name: 'Command and Control' },  // Teal
  'TA0038': { bg: 'rgba(192, 57, 43, 0.2)', border: '#c0392b', name: 'Impact' },                // Dark Red
  'TA0039': { bg: 'rgba(255, 152, 0, 0.2)', border: '#ff9800', name: 'Network Effects' },       // Amber
  'TA0041': { bg: 'rgba(0, 150, 136, 0.2)', border: '#009688', name: 'Remote Service Effects' },// Dark Teal

  // Default fallback
  'default': { bg: 'rgba(158, 158, 158, 0.2)', border: '#9e9e9e', name: 'Unknown' }             // Medium Gray
}

// Get source badge color
const getSourceColor = (source) => {
  switch (source) {
    case 'wazuh':
      return { bg: 'rgba(123, 198, 45, 0.3)', color: '#7bc62d', label: 'Wazuh' }
    case 'priority_agent':
      return { bg: 'rgba(100, 108, 255, 0.3)', color: '#646cff', label: 'AI' }
    case 'fallback':
      return { bg: 'rgba(245, 166, 35, 0.3)', color: '#f5a623', label: 'Fallback' }
    default:
      return { bg: 'rgba(149, 225, 211, 0.3)', color: '#95e1d3', label: source }
  }
}

/**
 * Single MITRE tag badge component
 */
export const MitreTagBadge = ({ tag, compact = false, showSource = true }) => {
  const tacticColor = TACTIC_COLORS[tag.tactic_id] || TACTIC_COLORS['default']
  const sourceColor = getSourceColor(tag.source)
  
  if (compact) {
    // Compact version for card preview
    return (
      <span
        style={{
          display: 'inline-block',
          background: tacticColor.bg,
          border: `1px solid ${tacticColor.border}`,
          color: tacticColor.border,
          padding: '0.2rem 0.5rem',
          borderRadius: '4px',
          fontSize: '0.75em',
          fontFamily: 'monospace',
          fontWeight: '600'
        }}
        title={`${tag.technique_name} (${tag.tactic})`}
      >
        {tag.technique_id}
      </span>
    )
  }
  
  // Full version for details view
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: tacticColor.bg,
        border: `1px solid ${tacticColor.border}`,
        borderRadius: '6px',
        padding: '0.5rem 0.75rem',
        fontSize: '0.85em'
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <span style={{
            fontFamily: 'monospace',
            fontWeight: 'bold',
            color: tacticColor.border,
            fontSize: '1.1em'
          }}>
            {tag.technique_id}
          </span>
          <span style={{ color: 'rgba(255,255,255,0.9)', fontWeight: '500' }}>
            {tag.technique_name}
          </span>
        </div>
        <div style={{ fontSize: '0.9em', color: 'rgba(255,255,255,0.6)' }}>
          <span style={{ color: tacticColor.border }}>{tag.tactic_id}</span>
          {' • '}
          {tag.tactic}
        </div>
      </div>
      
      {showSource && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
          <span
            style={{
              background: sourceColor.bg,
              color: sourceColor.color,
              padding: '0.15rem 0.4rem',
              borderRadius: '3px',
              fontSize: '0.75em',
              fontWeight: '600',
              textTransform: 'uppercase'
            }}
          >
            {sourceColor.label}
          </span>
          <span style={{ fontSize: '0.75em', color: 'rgba(255,255,255,0.5)' }}>
            {(tag.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * List of MITRE tags (for details view)
 */
export const MitreTagList = ({ tags }) => {
  if (!tags || tags.length === 0) {
    return null
  }
  
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h4 style={{ marginBottom: '0.75rem', color: '#646cff' }}>
        🎯 MITRE ATT&CK Techniques ({tags.length})
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {tags.map((tag, idx) => (
          <MitreTagBadge key={idx} tag={tag} compact={false} showSource={true} />
        ))}
      </div>
    </div>
  )
}

