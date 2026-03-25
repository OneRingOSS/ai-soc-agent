import { useState } from 'react'
import { MitreTagBadge, MitreTagList } from './MitreTagBadge'
import { IntelMatchCard } from './IntelMatchCard'

function ThreatItem({ threat }) {
  const [expanded, setExpanded] = useState(false)

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className="threat-item">
      <div className="threat-header">
        <div>
          <strong>{threat.signal.customer_name}</strong>
          <span style={{ margin: '0 0.5rem', color: 'rgba(255,255,255,0.5)' }}>•</span>
          <span style={{ color: 'rgba(255,255,255,0.7)' }}>
            {threat.signal.threat_type.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        <span className={`severity-badge severity-${threat.severity}`}>
          {threat.severity}
        </span>
      </div>

      <div style={{ fontSize: '0.9em', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
        {formatTimestamp(threat.signal.timestamp)}
      </div>

      <p style={{ marginBottom: '0.75rem', lineHeight: '1.6' }}>
        {threat.executive_summary}
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.6)' }}>
          Processing: {threat.total_processing_time_ms}ms
        </span>
        {threat.requires_human_review && (
          <span style={{
            fontSize: '0.85em',
            background: '#5c4a1a',
            color: '#f5a623',
            padding: '0.2rem 0.5rem',
            borderRadius: '4px'
          }}>
            ⚠️ Requires Review
          </span>
        )}
        {threat.adversarial_detection && threat.adversarial_detection.manipulation_detected && (
          <span style={{
            fontSize: '0.85em',
            background: '#4a1a1a',
            color: '#ff4444',
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            fontWeight: 'bold'
          }}>
            🚨 Adversarial Attack Detected
          </span>
        )}
      </div>

      {/* MITRE Tags Compact Preview */}
      {threat.mitre_tags && threat.mitre_tags.length > 0 && (
        <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {threat.mitre_tags.slice(0, 3).map((tag, idx) => (
            <MitreTagBadge key={idx} tag={tag} compact={true} showSource={false} />
          ))}
          {threat.mitre_tags.length > 3 && (
            <span style={{ fontSize: '0.75em', color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
              +{threat.mitre_tags.length - 3} more
            </span>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        style={{ fontSize: '0.9em', padding: '0.4em 0.8em' }}
      >
        {expanded ? 'Hide Details' : 'Show Details'}
      </button>

      {expanded && (
        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #2a3f5f' }}>

          {/* Adversarial Detection Section */}
          {threat.adversarial_detection && threat.adversarial_detection.manipulation_detected && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.75rem', color: '#ff4444' }}>🚨 Adversarial Attack Detection</h4>
              <div style={{
                padding: '1rem',
                background: '#1a0a0a',
                borderRadius: '8px',
                border: '2px solid #ff4444'
              }}>
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                  <div style={{
                    background: '#4a1a1a',
                    color: '#ff4444',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    fontSize: '0.9em',
                    fontWeight: 'bold'
                  }}>
                    ⚠️ MANIPULATION DETECTED
                  </div>
                  <div style={{
                    background: '#1a2332',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    fontSize: '0.9em'
                  }}>
                    Confidence: {(threat.adversarial_detection.confidence * 100).toFixed(0)}%
                  </div>
                  {threat.adversarial_detection.attack_vector && (
                    <div style={{
                      background: '#1a2332',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.9em',
                      fontFamily: 'monospace'
                    }}>
                      Vector: {threat.adversarial_detection.attack_vector.replace(/_/g, ' ')}
                    </div>
                  )}
                </div>

                {threat.adversarial_detection.explanation && (
                  <div style={{ fontSize: '0.9em', marginBottom: '0.75rem', color: 'rgba(255,255,255,0.9)', lineHeight: '1.6' }}>
                    <strong style={{ color: '#ff4444' }}>Analysis:</strong> {threat.adversarial_detection.explanation}
                  </div>
                )}

                {threat.adversarial_detection.anomalies && threat.adversarial_detection.anomalies.length > 0 && (
                  <div style={{ fontSize: '0.9em' }}>
                    <strong style={{ color: '#ff4444' }}>Detected Anomalies ({threat.adversarial_detection.anomalies.length}):</strong>
                    <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {threat.adversarial_detection.anomalies.map((anomaly, idx) => (
                        <div key={idx} style={{
                          background: '#1a2332',
                          padding: '0.75rem',
                          borderRadius: '4px',
                          borderLeft: `4px solid #ff4444`
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 'bold', color: '#ff4444', textTransform: 'uppercase', fontSize: '0.85em' }}>
                              {anomaly.type.replace(/_/g, ' ')}
                            </span>
                            <span style={{
                              background: anomaly.severity === 'critical' ? '#4a1a1a' : '#5c4a1a',
                              color: anomaly.severity === 'critical' ? '#ff4444' : '#f5a623',
                              padding: '0.2rem 0.5rem',
                              borderRadius: '3px',
                              fontSize: '0.75em',
                              fontWeight: 'bold',
                              textTransform: 'uppercase'
                            }}>
                              {anomaly.severity}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.9em', marginBottom: '0.5rem', color: 'rgba(255,255,255,0.8)', lineHeight: '1.5' }}>
                            {anomaly.description}
                          </div>
                          {anomaly.indicators && anomaly.indicators.length > 0 && (
                            <div style={{ fontSize: '0.85em', marginTop: '0.5rem' }}>
                              <strong style={{ color: '#7bc62d' }}>Indicators:</strong>
                              <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem', color: 'rgba(255,255,255,0.7)' }}>
                                {anomaly.indicators.map((indicator, iidx) => (
                                  <li key={iidx} style={{ marginBottom: '0.25rem' }}>{indicator}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {anomaly.confidence && (
                            <div style={{ fontSize: '0.8em', color: 'rgba(255,255,255,0.5)', marginTop: '0.5rem' }}>
                              Confidence: {(anomaly.confidence * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {threat.adversarial_detection.recommendation && (
                  <div style={{
                    marginTop: '0.75rem',
                    padding: '0.75rem',
                    background: '#4a1a1a',
                    borderRadius: '4px',
                    fontSize: '0.9em',
                    color: 'rgba(255,255,255,0.9)'
                  }}>
                    <strong style={{ color: '#ff4444' }}>Recommendation:</strong> {threat.adversarial_detection.recommendation.replace(/_/g, ' ')}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* MITRE ATT&CK Tags - Full List */}
          <MitreTagList tags={threat.mitre_tags} />

          {/* Threat Intelligence Matches - Wave 5 */}
          <IntelMatchCard intelMatches={threat.intel_matches} />

          {/* False Positive Score Section */}
          {threat.false_positive_score && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.75rem', color: '#646cff' }}>🎯 False Positive Analysis</h4>
              <div style={{
                padding: '1rem',
                background: '#0a0e27',
                borderRadius: '8px',
                border: threat.adversarial_detection && threat.adversarial_detection.manipulation_detected ? '2px solid #ff4444' : '1px solid #2a3f5f'
              }}>
                {threat.adversarial_detection && threat.adversarial_detection.manipulation_detected && (
                  <div style={{
                    background: '#4a1a1a',
                    color: '#ff4444',
                    padding: '0.75rem',
                    borderRadius: '6px',
                    marginBottom: '0.75rem',
                    fontSize: '0.9em',
                    fontWeight: 'bold',
                    border: '1px solid #ff4444'
                  }}>
                    ⚠️ WARNING: This FP score may be unreliable due to detected adversarial manipulation of historical data
                  </div>
                )}
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                  <div className={`fp-score-badge fp-score-${threat.false_positive_score.score < 0.3 ? 'low' : threat.false_positive_score.score < 0.7 ? 'medium' : 'high'}`}>
                    FP Score: {(threat.false_positive_score.score * 100).toFixed(0)}%
                  </div>
                  <div style={{
                    background: '#1a2332',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    fontSize: '0.9em'
                  }}>
                    Confidence: {(threat.false_positive_score.confidence * 100).toFixed(0)}%
                  </div>
                  <div style={{
                    background: '#1a2332',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    fontSize: '0.9em',
                    textTransform: 'capitalize'
                  }}>
                    {threat.false_positive_score.recommendation.replace(/_/g, ' ')}
                  </div>
                </div>

                {threat.false_positive_score.explanation && (
                  <div style={{ fontSize: '0.9em', marginBottom: '0.75rem', color: 'rgba(255,255,255,0.8)' }}>
                    {threat.false_positive_score.explanation}
                  </div>
                )}

                {threat.false_positive_score.indicators && threat.false_positive_score.indicators.length > 0 && (
                  <div style={{ fontSize: '0.9em' }}>
                    <strong style={{ color: '#7bc62d' }}>Indicators:</strong>
                    <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {threat.false_positive_score.indicators.map((indicator, idx) => (
                        <div key={idx} style={{
                          background: '#1a2332',
                          padding: '0.5rem',
                          borderRadius: '4px',
                          borderLeft: `3px solid ${indicator.weight > 0 ? '#f5a623' : '#7bc62d'}`
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                            <span style={{ fontWeight: 'bold' }}>{indicator.indicator}</span>
                            <span style={{ color: indicator.weight > 0 ? '#f5a623' : '#7bc62d' }}>
                              Weight: {indicator.weight > 0 ? '+' : ''}{indicator.weight.toFixed(2)}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.7)' }}>
                            {indicator.description}
                          </div>
                          {indicator.source && (
                            <div style={{ fontSize: '0.8em', color: 'rgba(255,255,255,0.5)', marginTop: '0.25rem' }}>
                              Source: {indicator.source}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Response Plan Section */}
          {threat.response_plan && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.75rem', color: '#646cff' }}>⚡ Response Plan</h4>
              <div style={{
                padding: '1rem',
                background: '#0a0e27',
                borderRadius: '8px',
                border: '1px solid #2a3f5f'
              }}>
                {/* Primary Action */}
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                    PRIMARY ACTION
                  </div>
                  <div className={`response-action-card urgency-${threat.response_plan.primary_action.urgency}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                      <div style={{ fontSize: '1.1em', fontWeight: 'bold', textTransform: 'uppercase' }}>
                        {threat.response_plan.primary_action.action_type.replace(/_/g, ' ')}
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <span className={`urgency-badge urgency-${threat.response_plan.primary_action.urgency}`}>
                          {threat.response_plan.primary_action.urgency}
                        </span>
                        {threat.response_plan.primary_action.auto_executable && (
                          <span style={{
                            background: '#1a4d2e',
                            color: '#7bc62d',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.8em'
                          }}>
                            ✓ Auto-Executable
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{ fontSize: '0.9em', marginBottom: '0.5rem' }}>
                      <strong>Target:</strong> {threat.response_plan.primary_action.target}
                    </div>
                    <div style={{ fontSize: '0.9em', color: 'rgba(255,255,255,0.8)' }}>
                      {threat.response_plan.primary_action.reason}
                    </div>
                  </div>
                </div>

                {/* Secondary Actions */}
                {threat.response_plan.secondary_actions && threat.response_plan.secondary_actions.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                      SECONDARY ACTIONS
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {threat.response_plan.secondary_actions.map((action, idx) => (
                        <div key={idx} style={{
                          background: '#1a2332',
                          padding: '0.75rem',
                          borderRadius: '6px',
                          fontSize: '0.9em'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                            <strong>{action.action_type.replace(/_/g, ' ')}</strong>
                            <span style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.6)' }}>
                              {action.urgency}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.7)' }}>
                            {action.reason}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* SLA and Escalation */}
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.9em' }}>
                  <div style={{
                    background: '#1a2332',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '6px'
                  }}>
                    ⏱️ SLA: {threat.response_plan.sla_minutes} minutes
                  </div>
                  {threat.response_plan.escalation_path && threat.response_plan.escalation_path.length > 0 && (
                    <div style={{
                      background: '#1a2332',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      flex: 1
                    }}>
                      📞 Escalation: {threat.response_plan.escalation_path.join(' → ')}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <h4 style={{ marginBottom: '0.5rem', color: '#646cff' }}>🤖 Agent Analyses</h4>
          {Object.entries(threat.agent_analyses).map(([agentName, analysis]) => (
            <div key={agentName} style={{
              marginBottom: '1rem',
              padding: '0.75rem',
              background: '#0a0e27',
              borderRadius: '4px',
              border: '1px solid #2a3f5f'
            }}>
              <div style={{
                fontWeight: 'bold',
                marginBottom: '0.5rem',
                color: '#7bc62d',
                textTransform: 'capitalize'
              }}>
                {agentName} ({analysis.processing_time_ms}ms)
              </div>
              <div style={{ fontSize: '0.9em', marginBottom: '0.5rem' }}>
                <strong>Confidence:</strong> {(analysis.confidence * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '0.9em', marginBottom: '0.5rem' }}>
                <strong>Analysis:</strong> {analysis.analysis}
              </div>
              {analysis.key_findings && analysis.key_findings.length > 0 && (
                <div style={{ fontSize: '0.9em', marginBottom: '0.5rem' }}>
                  <strong>Key Findings:</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    {analysis.key_findings.map((finding, idx) => (
                      <li key={idx}>{finding}</li>
                    ))}
                  </ul>
                </div>
              )}
              {analysis.recommendations && analysis.recommendations.length > 0 && (
                <div style={{ fontSize: '0.9em' }}>
                  <strong>Recommendations:</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    {analysis.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

          {/* Investigation Timeline Section */}
          {threat.investigation_timeline && threat.investigation_timeline.events && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.75rem', color: '#646cff' }}>
                📅 Investigation Timeline ({threat.investigation_timeline.events.length} events, {threat.investigation_timeline.duration_ms}ms)
              </h4>
              <div style={{
                padding: '1rem',
                background: '#0a0e27',
                borderRadius: '8px',
                border: '1px solid #2a3f5f',
                maxHeight: '400px',
                overflowY: 'auto'
              }}>
                <div className="timeline-container">
                  {threat.investigation_timeline.events.map((event, idx) => (
                    <div key={idx} className={`timeline-event event-type-${event.event_type}`}>
                      <div className="timeline-marker">
                        <div className={`timeline-dot event-${event.event_type}`}></div>
                        {idx < threat.investigation_timeline.events.length - 1 && (
                          <div className="timeline-line"></div>
                        )}
                      </div>
                      <div className="timeline-content">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.25rem' }}>
                          <div>
                            <span className={`event-type-badge event-${event.event_type}`}>
                              {event.event_type}
                            </span>
                            <span style={{ marginLeft: '0.5rem', fontWeight: 'bold' }}>
                              {event.title}
                            </span>
                          </div>
                          <span style={{ fontSize: '0.75em', color: 'rgba(255,255,255,0.5)' }}>
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.7)', marginBottom: '0.25rem' }}>
                          {event.description}
                        </div>
                        <div style={{ fontSize: '0.75em', color: 'rgba(255,255,255,0.5)' }}>
                          Source: {event.source}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {threat.mitre_tactics && threat.mitre_tactics.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <h4 style={{ marginBottom: '0.5rem', color: '#646cff' }}>MITRE ATT&CK Tactics</h4>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {threat.mitre_tactics.map((tactic, idx) => (
                  <span key={idx} style={{
                    background: '#1a1f3a',
                    padding: '0.3rem 0.6rem',
                    borderRadius: '4px',
                    fontSize: '0.85em',
                    border: '1px solid #646cff'
                  }}>
                    {tactic.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {threat.mitre_techniques && threat.mitre_techniques.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <h4 style={{ marginBottom: '0.5rem', color: '#646cff' }}>MITRE ATT&CK Techniques</h4>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {threat.mitre_techniques.map((technique, idx) => (
                  <span key={idx} style={{
                    background: '#1a1f3a',
                    padding: '0.3rem 0.6rem',
                    borderRadius: '4px',
                    fontSize: '0.85em',
                    border: '1px solid #7bc62d'
                  }}>
                    {technique.id}: {technique.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ marginBottom: '0.5rem', color: '#646cff' }}>Signal Metadata</h4>
            <pre style={{ 
              background: '#0a0e27', 
              padding: '0.75rem', 
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '0.85em',
              border: '1px solid #2a3f5f'
            }}>
              {JSON.stringify(threat.signal.metadata, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default ThreatItem

