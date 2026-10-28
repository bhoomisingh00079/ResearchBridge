import React, { useState, useEffect } from 'react';

/**
 * Coordinator / Administrator Dashboard — "The Institutional Observatory" (FR-034, PLAN Section 6).
 *
 * Implements the four mandated screen states:
 *   1. loading
 *   2. empty
 *   3. error / unavailable
 *   4. access-denied
 *
 * Testability: All elements have `data-testid="coord-dashboard-<element>"`.
 */
const rawBase = import.meta.env.VITE_API_BASE_URL || "https://researchbridge-r327.onrender.com";
const API_BASE = rawBase.replace(/\/+$/, "");

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
      <div data-testid="coord-dashboard-loading" className="state-card state-loading">
        <span className="state-mark" aria-hidden="true">◌</span>
        <h2>Consulting The Institutional Observatory…</h2>
        <p>Aggregating academy census data, active submissions, and ongoing expedition registries.</p>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div data-testid="coord-dashboard-access-denied" className="state-card state-denied">
        <span className="state-mark" aria-hidden="true">⌑</span>
        <h2>Observatory Privileges Required</h2>
        <p>Coordinator or Administrator permissions are required to view institutional analytics.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div data-testid="coord-dashboard-error" className="state-card state-error">
        <span className="state-mark" aria-hidden="true">!</span>
        <h2>Observatory Telescope Clouded</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  const totalUsers = Object.values(data?.metrics?.users_by_role || {}).reduce((a, b) => a + b, 0);
  const totalOpps = Object.values(data?.metrics?.opportunities_by_status || {}).reduce((a, b) => a + b, 0);
  const totalProjects = Object.values(data?.metrics?.projects_by_status || {}).reduce((a, b) => a + b, 0);
  const totalApps = data?.metrics?.total_applications ?? 0;

  return (
    <div data-testid="coord-dashboard-container" className="dashboard-shell">
      {/* 1. Header — The Institutional Observatory */}
      <header className="dashboard-header">
        <div>
          <div className="dashboard-kicker">✦ ACADEMY OVERSIGHT</div>
          <h1 className="dashboard-title" data-testid="coord-dashboard-title">
            The Institutional Observatory
          </h1>
          <p className="dashboard-subtitle">
            A wider view of research, participation, and progress across the academy.
          </p>
        </div>
        <div className="dashboard-actions">
          <a href="#/opportunities" className="button button-secondary" style={{ textDecoration: 'none' }}>
            <span>Explore Archive</span>
          </a>
        </div>
      </header>

      {/* 2. Metrics Strip */}
      <section className="metrics-strip" aria-label="Institutional KPI Strip">
        <div className="metric-card">
          <div className="metric-eyebrow">
            <span>Research Community</span>
            <span aria-hidden="true">👥</span>
          </div>
          <div className="metric-value">{totalUsers}</div>
          <div className="metric-caption">Enrolled scholars & faculty</div>
        </div>

        <div className="metric-card metric-card-lime">
          <div className="metric-eyebrow">
            <span>The Research Archive</span>
            <span aria-hidden="true">✦</span>
          </div>
          <div className="metric-value">{totalOpps}</div>
          <div className="metric-caption">Total recorded questions</div>
        </div>

        <div className="metric-card metric-card-sage">
          <div className="metric-eyebrow">
            <span>Ongoing Expeditions</span>
            <span aria-hidden="true">◫</span>
          </div>
          <div className="metric-value">{totalProjects}</div>
          <div className="metric-caption">Active lab teams</div>
        </div>

        <div className="metric-card metric-card-accent">
          <div className="metric-eyebrow">
            <span>Application Register</span>
            <span aria-hidden="true">✉</span>
          </div>
          <div className="metric-value">{totalApps}</div>
          <div className="metric-caption">Student scholar submissions</div>
        </div>
      </section>

      {/* 3. Empty State or Analytics Grid */}
      {screenState === 'empty' ? (
        <div data-testid="coord-dashboard-empty" className="state-card state-empty">
          <span className="state-mark" aria-hidden="true">✦</span>
          <h2>The Academy Is Newly Founded</h2>
          <p>Scholar accounts and faculty opportunities will appear here once registered.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px' }}>
          {/* User distribution */}
          <div
            data-testid="coord-dashboard-users-card"
            className="feed-card"
            style={{ margin: 0 }}
          >
            <div className="feed-card-header">
              <h3 className="feed-card-title">The Research Community</h3>
              <span className="badge-count">{totalUsers}</span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '14px 0 0', display: 'grid', gap: '8px' }}>
              {Object.entries(data?.metrics?.users_by_role || {}).map(([role, count]) => {
                const pct = totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0;
                return (
                  <li key={role} style={{ background: '#EDE5D5', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--color-divider)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '13px', color: 'var(--color-academy-deep)' }}>{role}</strong>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-ink-secondary)' }}>
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div style={{ height: '5px', background: '#DBD0BD', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: 'var(--color-gold-antique)', borderRadius: '3px' }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Opportunities summary */}
          <div
            data-testid="coord-dashboard-opps-card"
            className="feed-card"
            style={{ margin: 0 }}
          >
            <div className="feed-card-header">
              <h3 className="feed-card-title">Research Archive by Status</h3>
              <span className="badge-count">{totalOpps}</span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '14px 0 0', display: 'grid', gap: '8px' }}>
              {Object.entries(data?.metrics?.opportunities_by_status || {}).map(([st, count]) => (
                <li
                  key={st}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    background: '#EDE5D5',
                    borderRadius: '8px',
                    border: '1px solid var(--color-divider)'
                  }}
                >
                  <strong style={{ fontSize: '13px', color: 'var(--color-academy-deep)' }}>{st}</strong>
                  <span className={`status-pill ${st === 'Published' ? 'status-good' : st === 'Closed' ? 'status-muted' : 'status-warm'}`}>
                    {count}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Projects summary */}
          <div
            data-testid="coord-dashboard-projects-card"
            className="feed-card"
            style={{ margin: 0 }}
          >
            <div className="feed-card-header">
              <h3 className="feed-card-title">Ongoing Expeditions</h3>
              <span className="badge-count">{totalProjects}</span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '14px 0 0', display: 'grid', gap: '8px' }}>
              {Object.entries(data?.metrics?.projects_by_status || {}).map(([st, count]) => (
                <li
                  key={st}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    background: '#EDE5D5',
                    borderRadius: '8px',
                    border: '1px solid var(--color-divider)'
                  }}
                >
                  <strong style={{ fontSize: '13px', color: 'var(--color-academy-deep)' }}>{st}</strong>
                  <span className={`status-pill ${st === 'Active' ? 'status-good' : 'status-muted'}`}>
                    {count}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Applications summary card */}
          <div
            data-testid="coord-dashboard-apps-card"
            className="feed-card"
            style={{ margin: 0 }}
          >
            <div className="feed-card-header">
              <h3 className="feed-card-title">Application Register</h3>
              <span className="badge-count">{totalApps}</span>
            </div>
            <div style={{ marginTop: '14px', padding: '16px', background: '#EDE5D5', borderRadius: '8px', border: '1px solid var(--color-divider)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700, color: 'var(--color-moss)' }}>
                Total Student Submissions
              </div>
              <p style={{ fontSize: '34px', fontWeight: 700, margin: '6px 0', color: 'var(--color-academy-deep)', fontFamily: 'var(--font-display)' }}>
                {data?.metrics?.total_applications ?? 0}
              </p>
              <div style={{ fontSize: '12px', color: 'var(--color-ink-secondary)' }}>
                Recorded across active and past academy terms
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
