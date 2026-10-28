import React, { useState, useEffect } from 'react';

/**
 * Faculty Dashboard (FR-033, PLAN Section 6).
 *
 * Implements the four mandated screen states:
 *   1. loading
 *   2. empty
 *   3. error / unavailable
 *   4. access-denied
 *
 * Testability: All elements have `data-testid="faculty-dashboard-<element>"`.
 */
const rawBase = import.meta.env.VITE_API_BASE_URL || "https://researchbridge-r327.onrender.com";
const API_BASE = rawBase.replace(/\/+$/, "");

export default function FacultyDashboard({ token }) {
  const [data, setData] = useState(null);
  const [screenState, setScreenState] = useState('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    async function fetchDashboard() {
      setScreenState('loading');
      try {
        const res = await fetch(`${API_BASE}/dashboard/faculty`, {
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
          setErrorMsg('Failed to load faculty dashboard.');
          return;
        }

        const json = await res.json();
        setData(json);

        const hasApps = json.pending_applicants_count > 0;
        const hasProjects = json.active_projects && json.active_projects.length > 0;
        const hasAlerts = json.agent_alerts && json.agent_alerts.length > 0;
        if (!hasApps && !hasProjects && !hasAlerts && json.opportunities_count === 0) {
          setScreenState('empty');
        } else {
          setScreenState('ready');
        }
      } catch (err) {
        setScreenState('error');
        setErrorMsg('Network error connecting to backend.');
      }
    }

    if (token) fetchDashboard();
    else setScreenState('access-denied');
  }, [token]);

  if (screenState === 'loading') {
    return (
      <div data-testid="faculty-dashboard-loading" className="state-card state-loading">
        <span className="state-mark" aria-hidden="true">◌</span>
        <h2>Loading Faculty Dashboard…</h2>
        <p>Gathering applicant submissions, research proposals, and milestone statuses.</p>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div data-testid="faculty-dashboard-access-denied" className="state-card state-denied">
        <span className="state-mark" aria-hidden="true">⌑</span>
        <h2>Faculty Privileges Required</h2>
        <p>Faculty credentials are required to access this portal.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div data-testid="faculty-dashboard-error" className="state-card state-error">
        <span className="state-mark" aria-hidden="true">!</span>
        <h2>Dashboard Error</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  return (
    <div data-testid="faculty-dashboard-container" className="dashboard-shell">
      {/* 1. Header */}
      <header className="dashboard-header">
        <div>
          <div className="dashboard-kicker">Faculty Mentor Workspace</div>
          <h1 className="dashboard-title" data-testid="faculty-dashboard-title">
            Faculty Portal: {data?.user?.name}
          </h1>
          <p className="dashboard-subtitle">
            Review applicant submissions, oversee research projects, and monitor progress milestones.
          </p>
        </div>
        <div className="dashboard-actions">
          <a href="#/create" className="button" style={{ textDecoration: 'none' }}>
            <span>＋ Post Opportunity</span>
          </a>
        </div>
      </header>

      {/* 2. Metrics Strip */}
      <section className="metrics-strip" aria-label="Faculty overview metrics">
        <div className="metric-card metric-card-accent" data-testid="faculty-dashboard-pending-count">
          <div className="metric-eyebrow">
            <span>Pending Applicants</span>
            <span aria-hidden="true">⏳</span>
          </div>
          <div className="metric-value">{data?.pending_applicants_count ?? 0}</div>
          <div className="metric-caption">Awaiting faculty review</div>
        </div>

        <div className="metric-card metric-card-sage">
          <div className="metric-eyebrow">
            <span>Active Projects</span>
            <span aria-hidden="true">◫</span>
          </div>
          <div className="metric-value">{data?.active_projects?.length ?? 0}</div>
          <div className="metric-caption">Mentored lab groups</div>
        </div>

        <div className="metric-card" data-testid="faculty-dashboard-overdue-count">
          <div className="metric-eyebrow">
            <span>Overdue Milestones</span>
            <span aria-hidden="true">⚠️</span>
          </div>
          <div className="metric-value" style={{ color: (data?.overdue_milestones_total ?? 0) > 0 ? 'var(--color-error)' : 'var(--color-teal)' }}>
            {data?.overdue_milestones_total ?? 0}
          </div>
          <div className="metric-caption">Past scheduled due dates</div>
        </div>

        <div className="metric-card metric-card-lime">
          <div className="metric-eyebrow">
            <span>Posted Opportunities</span>
            <span aria-hidden="true">★</span>
          </div>
          <div className="metric-value">{data?.opportunities_count ?? 0}</div>
          <div className="metric-caption">Published research listings</div>
        </div>
      </section>

      {/* 3. Advisory Agent Alerts */}
      {data?.agent_alerts?.length > 0 && (
        <section
          data-testid="faculty-dashboard-alerts-section"
          style={{
            backgroundColor: '#fbf5ea',
            border: '1px solid #eed8b8',
            borderLeft: '4px solid var(--color-orange)',
            borderRadius: '10px',
            padding: '18px 20px',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{ color: 'var(--color-orange)', fontSize: '14px' }}>✦</span>
            <h3 style={{ margin: 0, color: '#7a4216', fontSize: '14px', fontWeight: 700 }}>
              AI Research Alerts (FR-035)
            </h3>
          </div>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '6px' }}>
            {data.agent_alerts.map((alert) => (
              <li
                key={alert.id}
                data-testid={`faculty-dashboard-alert-${alert.id}`}
                style={{
                  fontSize: '13px',
                  color: '#493729',
                  background: 'rgb(255 255 255 / 75%)',
                  padding: '9px 13px',
                  borderRadius: '6px',
                  border: '1px solid #fae6cf'
                }}
              >
                {alert.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 4. Main Body */}
      {screenState === 'empty' ? (
        <div data-testid="faculty-dashboard-empty" className="state-card state-empty">
          <span className="state-mark" aria-hidden="true">✦</span>
          <h2>No research opportunities posted yet</h2>
          <p>Create and publish research opportunities to receive student applications and begin mentoring.</p>
          <a href="#/create" className="button" style={{ textDecoration: 'none', marginTop: '10px' }}>
            Create first opportunity
          </a>
        </div>
      ) : (
        <div className="dashboard-split">
          {/* Pending Applicants */}
          <section data-testid="faculty-dashboard-applicants-section" className="dashboard-section">
            <div className="dashboard-section-header">
              <h2 className="dashboard-section-title">
                Pending Applicants
                <span className="badge-count">{data?.pending_applicants?.length ?? 0}</span>
              </h2>
            </div>

            <ul data-testid="faculty-dashboard-applicants-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {(data?.pending_applicants || []).map((app) => (
                <li
                  key={app.application_id}
                  data-testid={`faculty-dashboard-applicant-${app.application_id}`}
                  className="feed-card"
                >
                  <div className="feed-card-header">
                    <div>
                      <h3 className="feed-card-title">{app.student_name}</h3>
                      <div className="feed-card-meta">
                        <span>Opportunity: <strong>{app.opportunity_title}</strong></span>
                      </div>
                    </div>
                    <span className="status-pill status-warm">
                      {app.status}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #ebede5' }}>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      Submitted: {app.submitted_at ? new Date(app.submitted_at).toLocaleDateString() : 'Recent'}
                    </span>
                    <a
                      href={`#/review/${app.opportunity_id}`}
                      className="button button-secondary"
                      style={{ minHeight: '30px', padding: '0 10px', fontSize: '11px', textDecoration: 'none' }}
                    >
                      Review Applicant →
                    </a>
                  </div>
                </li>
              ))}
              {(!data?.pending_applicants || data.pending_applicants.length === 0) && (
                <div style={{ padding: '24px', textAlign: 'center', background: 'var(--color-cream)', borderRadius: '12px', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontSize: '13px' }}>
                  No pending applicants to review at this moment.
                </div>
              )}
            </ul>
          </section>

          {/* Active Projects */}
          <section data-testid="faculty-dashboard-projects-section" className="dashboard-section">
            <div className="dashboard-section-header">
              <h2 className="dashboard-section-title">
                Active Projects
                <span className="badge-count">{data?.active_projects?.length ?? 0}</span>
              </h2>
              <a href="/workspace" target="_blank" rel="noopener noreferrer" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-teal)', textDecoration: 'none' }}>
                Open workspace ↗
              </a>
            </div>

            <ul data-testid="faculty-dashboard-projects-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {(data?.active_projects || []).map((proj) => (
                <li
                  key={proj.id}
                  data-testid={`faculty-dashboard-project-${proj.id}`}
                  className="feed-card"
                >
                  <div className="feed-card-header">
                    <div>
                      <h3 className="feed-card-title">{proj.title}</h3>
                      <div className="feed-card-meta">
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          background: 'var(--color-sage-pale)',
                          color: 'var(--color-teal)',
                          fontSize: '11px',
                          fontWeight: 600
                        }}>
                          {proj.domain || 'General Research'}
                        </span>
                      </div>
                    </div>
                    {proj.overdue_milestones > 0 && (
                      <span className="status-pill status-warm" style={{ color: 'var(--color-error)', background: '#fae8df' }}>
                        ! {proj.overdue_milestones} overdue
                      </span>
                    )}
                  </div>
                </li>
              ))}
              {(!data?.active_projects || data.active_projects.length === 0) && (
                <div style={{ padding: '24px', textAlign: 'center', background: 'var(--color-cream)', borderRadius: '12px', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontSize: '13px' }}>
                  No active research projects currently in progress.
                </div>
              )}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
