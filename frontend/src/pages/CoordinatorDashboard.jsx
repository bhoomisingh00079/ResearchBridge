import React, { useState, useEffect } from 'react';

/**
 * Coordinator / Administrator Dashboard (FR-034, PLAN Section 6).
 *
 * Implements the four mandated screen states:
 *   1. loading
 *   2. empty
 *   3. error / unavailable
 *   4. access-denied
 *
 * Testability: All elements have `data-testid="coord-dashboard-<element>"`.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function CoordinatorDashboard({ token }) {
  const [data, setData] = useState(null);
  const [screenState, setScreenState] = useState('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    async function fetchCoordinatorData() {
      setScreenState('loading');
      try {
        const res = await fetch(`${API_BASE}/dashboard/coordinator`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (res.status === 401 || res.status === 403) {
          setScreenState('access-denied');
          return;
        }

        if (!res.ok) {
          setScreenState('error');
          setErrorMsg('Failed to load coordinator analytics.');
          return;
        }

        const json = await res.json();
        setData(json);

        const totalUsers = Object.values(json.metrics.users_by_role || {}).reduce((a, b) => a + b, 0);
        if (totalUsers === 0) {
          setScreenState('empty');
        } else {
          setScreenState('ready');
        }
      } catch (err) {
        setScreenState('error');
        setErrorMsg('Network error connecting to platform.');
      }
    }

    if (token) fetchCoordinatorData();
    else setScreenState('access-denied');
  }, [token]);

  if (screenState === 'loading') {
    return (
      <div data-testid="coord-dashboard-loading" style={{ padding: '24px', textAlign: 'center' }}>
        <h2>Loading Platform Metrics...</h2>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div
        data-testid="coord-dashboard-access-denied"
        style={{ padding: '24px', backgroundColor: '#fef2f2', border: '1px solid #f87171', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#991b1b' }}>Access Denied</h2>
        <p>Coordinator or Administrator permissions are required to access institutional analytics.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div
        data-testid="coord-dashboard-error"
        style={{ padding: '24px', backgroundColor: '#fff7ed', border: '1px solid #fdba74', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#c2410c' }}>Error</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  return (
    <div data-testid="coord-dashboard-container" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <header style={{ marginBottom: '20px' }}>
        <h1 data-testid="coord-dashboard-title">Institutional Overview</h1>
        <p>System-wide collaboration analytics and participant summary.</p>
      </header>

      {screenState === 'empty' ? (
        <div
          data-testid="coord-dashboard-empty"
          style={{ padding: '32px', textAlign: 'center', backgroundColor: '#f9fafb', borderRadius: '8px' }}
        >
          <h3>No activity recorded yet</h3>
          <p>User accounts and research opportunities will appear here once registered.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          {/* User distribution */}
          <div
            data-testid="coord-dashboard-users-card"
            style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}
          >
            <h3>Users by Role</h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {Object.entries(data?.metrics?.users_by_role || {}).map(([role, count]) => (
                <li key={role} style={{ marginBottom: '4px' }}>
                  <strong>{role}:</strong> {count}
                </li>
              ))}
            </ul>
          </div>

          {/* Opportunities summary */}
          <div
            data-testid="coord-dashboard-opps-card"
            style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}
          >
            <h3>Opportunities</h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {Object.entries(data?.metrics?.opportunities_by_status || {}).map(([st, count]) => (
                <li key={st} style={{ marginBottom: '4px' }}>
                  <strong>{st}:</strong> {count}
                </li>
              ))}
            </ul>
          </div>

          {/* Projects summary */}
          <div
            data-testid="coord-dashboard-projects-card"
            style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}
          >
            <h3>Projects</h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {Object.entries(data?.metrics?.projects_by_status || {}).map(([st, count]) => (
                <li key={st} style={{ marginBottom: '4px' }}>
                  <strong>{st}:</strong> {count}
                </li>
              ))}
            </ul>
          </div>

          {/* Applications summary */}
          <div
            data-testid="coord-dashboard-apps-card"
            style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}
          >
            <h3>Applications</h3>
            <p style={{ fontSize: '1.8rem', fontWeight: 'bold', margin: '8px 0', color: '#2563eb' }}>
              {data?.metrics?.total_applications}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

