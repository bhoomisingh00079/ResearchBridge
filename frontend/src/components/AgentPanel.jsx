import React, { useState, useEffect } from 'react';

/**
 * Agent Advisory Panel (FR-026, FR-031, NFR-002, PLAN Section 6).
 *
 * Requirements:
 *  - Visually distinct styling (clearly marked as automated AI advice, not binding).
 *  - Displays reason text and match score.
 *  - One-click dismiss button with data-testid="agent-dismiss" (FR-031).
 *  - Loads independently from the main dashboard (NFR-002).
 *  - Supports four distinct states: loading, empty, error/unavailable, ready.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function AgentPanel({ token, apiUrl = '/agent/recommendations' }) {
  const [recommendations, setRecommendations] = useState([]);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ready' | 'empty' | 'unavailable'
  const [errorMessage, setErrorMessage] = useState('');

  const resolvedApiUrl = apiUrl.startsWith('http') ? apiUrl : `${API_BASE}${apiUrl}`;

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
        setErrorMessage('AI Recommendation service is currently unavailable.');
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
      setErrorMessage('AI Recommendation service is currently unavailable.');
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
      style={{
        border: '2px dashed #4f46e5',
        backgroundColor: '#f5f3ff',
        borderRadius: '8px',
        padding: '16px',
        margin: '16px 0',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ margin: 0, color: '#4338ca' }} data-testid="agent-panel-title">
          🤖 AI Research Advisor <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>(Advisory Only)</span>
        </h3>
        <button
          onClick={fetchRecommendations}
          data-testid="agent-refresh-btn"
          style={{ cursor: 'pointer', padding: '4px 8px', fontSize: '0.8rem' }}
        >
          Refresh
        </button>
      </div>

      {status === 'loading' && (
        <div data-testid="agent-panel-loading" style={{ padding: '16px', textAlign: 'center', color: '#6b7280' }}>
          Analyzing research profiles and opportunities...
        </div>
      )}

      {status === 'unavailable' && (
        <div data-testid="agent-panel-unavailable" style={{ padding: '16px', color: '#b91c1c' }}>
          <p>{errorMessage}</p>
          <small>The dashboard remains fully functional. You can try refreshing later.</small>
        </div>
      )}

      {status === 'empty' && (
        <div data-testid="agent-panel-empty" style={{ padding: '16px', textAlign: 'center', color: '#6b7280' }}>
          No new suggestions at this moment. Complete more profile skills to receive tailored matches.
        </div>
      )}

      {status === 'ready' && (
        <ul data-testid="agent-recommendations-list" style={{ listStyle: 'none', padding: 0, marginTop: '12px' }}>
          {recommendations.map((rec) => (
            <li
              key={rec.id}
              data-testid={`agent-rec-item-${rec.id}`}
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #e0e7ff',
                borderRadius: '6px',
                padding: '12px',
                marginBottom: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span
                  style={{
                    backgroundColor: '#e0e7ff',
                    color: '#3730a3',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    marginRight: '8px',
                  }}
                  data-testid={`agent-score-${rec.id}`}
                >
                  Score: {rec.score}
                </span>
                <span style={{ fontSize: '0.9rem', color: '#1f2937' }} data-testid={`agent-reason-${rec.id}`}>
                  {rec.reason_text}
                </span>
              </div>
              <button
                onClick={() => handleDismiss(rec.id)}
                data-testid="agent-dismiss"
                style={{
                  backgroundColor: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  marginLeft: '12px',
                }}
              >
                Dismiss
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

