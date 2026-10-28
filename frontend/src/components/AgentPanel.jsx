import React, { useState, useEffect } from 'react';

/**
 * Agent Advisory Panel — "The Seer's Compass" (FR-026, FR-031, NFR-002).
 *
 * Requirements:
 *  - Visually distinct styling (Scholarium academic parchment & antique gold, advisory only).
 *  - Displays reason text and match score clearly.
 *  - One-click dismiss button with data-testid="agent-dismiss" (FR-031).
 *  - Loads independently from the main dashboard (NFR-002).
 *  - Supports four distinct states: loading, empty, error/unavailable, ready.
 */
const rawBase = import.meta.env.VITE_API_BASE_URL || "https://researchbridge-r327.onrender.com";
const API_BASE = rawBase.replace(/\/+$/, "");

export default function AgentPanel({ token, apiUrl = '/agent/recommendations' }) {
  const [recommendations, setRecommendations] = useState([]);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ready' | 'empty' | 'unavailable'
  const [errorMessage, setErrorMessage] = useState('');

  const normalizedApiUrl = apiUrl.startsWith('/') ? apiUrl : `/${apiUrl}`;
  const resolvedApiUrl = apiUrl.startsWith('http') ? apiUrl : `${API_BASE}${normalizedApiUrl}`;

  const fetchRecommendations = async () => {
    setStatus('loading');
    try {
      const response = await fetch(resolvedApiUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        setStatus('unavailable');
        setErrorMessage('The advisory compass is currently resting.');
        return;
      }

      const data = await response.json();
      if (!Array.isArray(data) || data.length === 0) {
        setRecommendations([]);
        setStatus('empty');
      } else {
        setRecommendations(data);
        setStatus('ready');
      }
    } catch (err) {
      setStatus('unavailable');
      setErrorMessage('The advisory compass is currently unavailable.');
    }
  };

  useEffect(() => {
    if (token) {
      fetchRecommendations();
    }
  }, [token, apiUrl]);

  const handleDismiss = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/agent/recommendations/${id}/dismiss`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        setRecommendations((prev) => {
          const updated = prev.filter((r) => r.id !== id);
          if (updated.length === 0) setStatus('empty');
          return updated;
        });
      }
    } catch (err) {
      console.error('Failed to dismiss recommendation', err);
    }
  };

  return (
    <div
      data-testid="agent-panel"
      className="advisor-panel-custom"
    >
      <div className="advisor-head">
        <div>
          <div className="advisor-tagline">
            <span className="advisor-sparkle" aria-hidden="true">✦</span>
            <span>The Seer’s Compass · Advisory Intelligence</span>
          </div>
          <h3 className="advisor-title" data-testid="agent-panel-title">
            AI Research Advisor <span className="advisor-advisory-pill">(Advisory Only)</span>
          </h3>
        </div>
        <button
          onClick={fetchRecommendations}
          data-testid="agent-refresh-btn"
          className="button button-secondary"
          style={{ minHeight: '34px', padding: '0 12px', fontSize: '11px' }}
          type="button"
        >
          <span aria-hidden="true">↻</span> Consult Compass
        </button>
      </div>

      {status === 'loading' && (
        <div data-testid="agent-panel-loading" style={{ padding: '16px', textAlign: 'center', color: 'var(--color-moss)', fontSize: '12.5px' }}>
          Aligning scholar interests with active research questions…
        </div>
      )}

      {status === 'unavailable' && (
        <div
          data-testid="agent-panel-unavailable"
          style={{
            padding: '12px 14px',
            borderRadius: '8px',
            backgroundColor: '#F8E6E4',
            border: '1px solid #E6B6B2',
            color: '#792A2A',
            fontSize: '12px'
          }}
        >
          <p style={{ margin: 0, fontWeight: 600 }}>{errorMessage}</p>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#68453c' }}>
            The academy chambers remain fully operational. You can consult the compass again later.
          </p>
        </div>
      )}

      {status === 'empty' && (
        <div data-testid="agent-panel-empty" style={{ padding: '16px', textAlign: 'center', color: 'var(--color-ink-secondary)', fontSize: '12.5px' }}>
          No new advisory alignments right now. Expand your Scholar’s Codex with more methodological skills to receive tailored question recommendations.
        </div>
      )}

      {status === 'ready' && (
        <ul data-testid="agent-recommendations-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {recommendations.map((rec) => (
            <li
              key={rec.id}
              data-testid={`agent-rec-item-${rec.id}`}
              className="advisor-item-card"
            >
              <div className="advisor-item-content">
                <span
                  className="advisor-score-badge"
                  data-testid={`agent-score-${rec.id}`}
                >
                  Affinity Score: {rec.score}
                </span>
                <span className="advisor-reason-text" data-testid={`agent-reason-${rec.id}`}>
                  {rec.reason_text}
                </span>
              </div>
              <button
                onClick={() => handleDismiss(rec.id)}
                data-testid="agent-dismiss"
                className="advisor-dismiss-btn"
                title="Dismiss suggestion"
                type="button"
              >
                Dismiss ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
