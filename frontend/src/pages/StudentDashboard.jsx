import React, { useState, useEffect, useMemo } from 'react';
import AgentPanel from '../components/AgentPanel';

/**
 * Student Dashboard (FR-032, PLAN Section 6).
 *
 * Implements the four mandated screen states:
 *   1. loading
 *   2. empty
 *   3. error / unavailable
 *   4. access-denied
 *
 * Testability: All interactive and key structural elements have `data-testid="student-dashboard-<element>"`.
 */
const rawBase = import.meta.env.VITE_API_BASE_URL || "https://researchbridge-r327.onrender.com";
const API_BASE = rawBase.replace(/\/+$/, "");

export default function StudentDashboard({ token }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [screenState, setScreenState] = useState('loading'); // 'loading' | 'ready' | 'empty' | 'error' | 'access-denied'
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    async function loadDashboard() {
      setScreenState('loading');
      try {
        const res = await fetch(`${API_BASE}/dashboard/student`, {
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
          setErrorMsg('Failed to fetch dashboard data. Please try again.');
          return;
        }

        const data = await res.json();
        setDashboardData(data);

        const hasApps = data.applications && data.applications.length > 0;
        const hasProjects = data.projects && data.projects.length > 0;
        if (!hasApps && !hasProjects) {
          setScreenState('empty');
        } else {
          setScreenState('ready');
        }
      } catch (err) {
        setScreenState('error');
        setErrorMsg('Network error connecting to ResearchBridge backend.');
      }
    }

    if (token) {
      loadDashboard();
    } else {
      setScreenState('access-denied');
    }
  }, [token]);

  // Derived real metrics from real data (no fabrication)
  const metrics = useMemo(() => {
    if (!dashboardData) return { activeApps: 0, acceptedApps: 0, activeProjects: 0, pendingMilestones: 0 };
    const apps = dashboardData.applications || [];
    const projs = dashboardData.projects || [];
    const activeApps = apps.filter(a => ['Submitted', 'Shortlisted'].includes(a.status)).length;
    const acceptedApps = apps.filter(a => a.status === 'Accepted').length;
    const activeProjects = projs.length;
    let pendingMilestones = 0;
    projs.forEach(p => {
      (p.milestones || []).forEach(m => {
        if (m.status !== 'Completed') pendingMilestones += 1;
      });
    });
    return { activeApps, acceptedApps, activeProjects, pendingMilestones };
  }, [dashboardData]);

  if (screenState === 'loading') {
    return (
      <div data-testid="student-dashboard-loading" className="state-card state-loading">
        <span className="state-mark" aria-hidden="true">◌</span>
        <h2>Gathering your research workspace…</h2>
        <p>Loading your active applications, milestones, and project teams.</p>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div data-testid="student-dashboard-access-denied" className="state-card state-denied">
        <span className="state-mark" aria-hidden="true">⌑</span>
        <h2>Student Access Required</h2>
        <p>You must be signed in with a verified Student account to view this dashboard.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div data-testid="student-dashboard-error" className="state-card state-error">
        <span className="state-mark" aria-hidden="true">!</span>
        <h2>Service Unavailable</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  return (
    <div data-testid="student-dashboard-container" className="dashboard-shell">
      {/* 1. Redesigned Page Header */}
      <header className="dashboard-header">
        <div>
          <div className="dashboard-kicker">Student Researcher Workspace</div>
          <h1 className="dashboard-title" data-testid="student-dashboard-welcome">
            Welcome, {dashboardData?.user?.name}
          </h1>
          <p className="dashboard-subtitle">
            Manage your applications, collaborate on active research projects, and track upcoming milestones.
          </p>
        </div>
        <div className="dashboard-actions">
          <a href="#/opportunities" className="button" style={{ textDecoration: 'none' }}>
            <span>Explore Opportunities</span> <span aria-hidden="true">→</span>
          </a>
        </div>
      </header>

      {/* 2. Restrained Real Metrics Strip */}
      <section className="metrics-strip" aria-label="Research overview metrics">
        <div className="metric-card">
          <div className="metric-eyebrow">
            <span>In-Review Applications</span>
            <span aria-hidden="true">⏳</span>
          </div>
          <div className="metric-value">{metrics.activeApps}</div>
          <div className="metric-caption">Submitted or shortlisted</div>
        </div>

        <div className="metric-card metric-card-lime">
          <div className="metric-eyebrow">
            <span>Accepted Offers</span>
            <span aria-hidden="true">✓</span>
          </div>
          <div className="metric-value">{metrics.acceptedApps}</div>
          <div className="metric-caption">Ready for active research</div>
        </div>

        <div className="metric-card metric-card-sage">
          <div className="metric-eyebrow">
            <span>Active Projects</span>
            <span aria-hidden="true">◫</span>
          </div>
          <div className="metric-value">{metrics.activeProjects}</div>
          <div className="metric-caption">Enrolled lab teams</div>
        </div>

        <div className="metric-card metric-card-accent">
          <div className="metric-eyebrow">
            <span>Pending Milestones</span>
            <span aria-hidden="true">◷</span>
          </div>
          <div className="metric-value">{metrics.pendingMilestones}</div>
          <div className="metric-caption">Deliverables in progress</div>
        </div>
      </section>

      {/* 3. Redesigned AI Research Advisor */}
      <AgentPanel token={token} apiUrl="/agent/recommendations" />

      {/* 4. Empty State or Split Layout */}
      {screenState === 'empty' ? (
        <div data-testid="student-dashboard-empty" className="state-card state-empty">
          <span className="state-mark" aria-hidden="true">✦</span>
          <h2>No research activities yet</h2>
          <p>Explore open research opportunities and submit applications to start collaborating with faculty mentors.</p>
          <a href="#/opportunities" className="button" style={{ textDecoration: 'none', marginTop: '8px' }}>
            Browse open opportunities
          </a>
        </div>
      ) : (
        <div className="dashboard-split">
          {/* Applications Section */}
          <section data-testid="student-dashboard-applications-section" className="dashboard-section">
            <div className="dashboard-section-header">
              <h2 className="dashboard-section-title">
                My Applications
                <span className="badge-count">{dashboardData.applications.length}</span>
              </h2>
              <a href="#/my-applications" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-teal)', textDecoration: 'none' }}>
                View all →
              </a>
            </div>

            <ul data-testid="student-dashboard-applications-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {dashboardData.applications.map((app) => {
                const isAccepted = app.status === 'Accepted';
                const isShortlisted = app.status === 'Shortlisted';
                const isRejected = app.status === 'Rejected';
                const isWithdrawn = app.status === 'Withdrawn';

                const statusClass = isAccepted ? 'status-good'
                  : isShortlisted ? 'status-accent'
                  : isRejected || isWithdrawn ? 'status-muted'
                  : 'status-warm';

                const statusSymbol = isAccepted ? '✓ '
                  : isShortlisted ? '★ '
                  : isRejected ? '✕ '
                  : isWithdrawn ? '— '
                  : '⏳ ';

                return (
                  <li
                    key={app.id}
                    data-testid={`student-dashboard-app-${app.id}`}
                    className="feed-card"
                  >
                    <div className="feed-card-header">
                      <h3 className="feed-card-title">
                        <a href={`#/opportunities/${app.opportunity_id}`}>
                          {app.opportunity_title}
                        </a>
                      </h3>
                      <span
                        className={`status-pill ${statusClass}`}
                        data-testid={`student-dashboard-app-status-${app.id}`}
                      >
                        {statusSymbol}{app.status}
                      </span>
                    </div>

                    <div className="feed-card-meta">
                      {app.submitted_at && (
                        <span className="feed-card-meta-item">
                          <span>Submitted:</span>
                          <strong>{new Date(app.submitted_at).toLocaleDateString()}</strong>
                        </span>
                      )}
                      <span className="feed-card-meta-item">
                        <span>Application:</span>
                        <strong>#RB-A{String(app.id).padStart(4, '0')}</strong>
                      </span>
                    </div>

                    {app.faculty_comment && (
                      <div className="faculty-quote">
                        <strong>Faculty Note:</strong>
                        {app.faculty_comment}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Active Projects & Milestones Section */}
          <section data-testid="student-dashboard-projects-section" className="dashboard-section">
            <div className="dashboard-section-header">
              <h2 className="dashboard-section-title">
                Active Projects
                <span className="badge-count">{dashboardData.projects.length}</span>
              </h2>
              <a href="/workspace" target="_blank" rel="noopener noreferrer" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-teal)', textDecoration: 'none' }}>
                Open workspace ↗
              </a>
            </div>

            <ul data-testid="student-dashboard-projects-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {dashboardData.projects.map((proj) => {
                const totalMs = (proj.milestones || []).length;
                const completedMs = (proj.milestones || []).filter(m => m.status === 'Completed').length;
                const progressPct = totalMs > 0 ? Math.round((completedMs / totalMs) * 100) : 0;
                const todayStr = new Date().toISOString().slice(0, 10);

                return (
                  <li
                    key={proj.project_id}
                    data-testid={`student-dashboard-proj-${proj.project_id}`}
                    className="feed-card"
                  >
                    <div className="feed-card-header">
                      <div>
                        <h3 className="feed-card-title">{proj.title}</h3>
                        <div className="feed-card-meta" style={{ marginTop: '4px' }}>
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
                            {proj.domain || 'Research'}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                            Role: <strong>{proj.role_in_project || 'Member'}</strong>
                          </span>
                        </div>
                      </div>
                    </div>

                    {totalMs > 0 && (
                      <div className="milestones-box">
                        <div className="milestones-box-title">
                          <span>Milestones Progress</span>
                          <span style={{ color: 'var(--color-teal)' }}>{completedMs} of {totalMs} completed ({progressPct}%)</span>
                        </div>

                        {/* Progress Bar */}
                        <div style={{
                          height: '5px',
                          background: '#e3e9de',
                          borderRadius: '4px',
                          overflow: 'hidden',
                          marginBottom: '10px'
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${progressPct}%`,
                            background: 'var(--color-teal)',
                            borderRadius: '4px',
                            transition: 'width 0.3s ease'
                          }} />
                        </div>

                        {/* Structured Milestone Items */}
                        <div className="milestone-list" style={{ display: 'grid', gap: '8px', marginTop: '12px' }}>
                          {proj.milestones.map((ms, index) => {
                            const isDone = ms.status === 'Completed';
                            const isOverdue = !isDone && ms.target_date && ms.target_date < todayStr;
                            let formattedDate = 'No deadline';
                            if (ms.target_date) {
                              try {
                                const [y, m, d] = ms.target_date.split('-');
                                const dateObj = new Date(Number(y), Number(m) - 1, Number(d));
                                formattedDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                              } catch {
                                formattedDate = ms.target_date;
                              }
                            }

                            return (
                              <div
                                key={ms.id}
                                className={`milestone-card-item ${isDone ? 'is-done' : isOverdue ? 'is-overdue' : 'is-pending'}`}
                              >
                                <div className="milestone-card-header">
                                  <div className="milestone-step-pill">
                                    <span className="milestone-step-marker">{isDone ? '✓' : isOverdue ? '!' : (index + 1)}</span>
                                    <span className="milestone-step-text">Milestone {index + 1}</span>
                                  </div>
                                  <span className={`milestone-status-tag ${isDone ? 'tag-completed' : isOverdue ? 'tag-overdue' : 'tag-pending'}`}>
                                    {isDone ? 'Completed' : isOverdue ? 'Overdue' : 'In Progress'}
                                  </span>
                                </div>
                                <p className="milestone-card-desc">{ms.description}</p>
                                <div className="milestone-card-footer">
                                  <span className="milestone-card-date">
                                    {isDone ? `Completed: ${formattedDate}` : isOverdue ? `Overdue since: ${formattedDate}` : `Target: ${formattedDate}`}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
