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
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
      <div data-testid="faculty-dashboard-loading" style={{ padding: '24px', textAlign: 'center' }}>
        <h2>Loading Faculty Dashboard...</h2>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div
        data-testid="faculty-dashboard-access-denied"
        style={{ padding: '24px', backgroundColor: '#fef2f2', border: '1px solid #f87171', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#991b1b' }}>Access Denied</h2>
        <p>Faculty privileges are required to access this portal.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div
        data-testid="faculty-dashboard-error"
        style={{ padding: '24px', backgroundColor: '#fff7ed', border: '1px solid #fdba74', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#c2410c' }}>Error</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  return (
    <div data-testid="faculty-dashboard-container" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <header style={{ marginBottom: '20px' }}>
        <h1 data-testid="faculty-dashboard-title">Faculty Portal: {data?.user?.name}</h1>
        <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
          <div
            style={{ padding: '12px', background: '#eff6ff', borderRadius: '6px' }}
            data-testid="faculty-dashboard-pending-count"
          >
            <strong>Pending Applicants:</strong> {data?.pending_applicants_count}
          </div>
          <div
            style={{ padding: '12px', background: '#fef2f2', borderRadius: '6px' }}
            data-testid="faculty-dashboard-overdue-count"
          >
            <strong>Overdue Milestones:</strong> {data?.overdue_milestones_total}
          </div>
        </div>
      </header>

      {/* Advisory Agent Alerts */}
      {data?.agent_alerts?.length > 0 && (
        <section
          data-testid="faculty-dashboard-alerts-section"
          style={{
            backgroundColor: '#fefce8',
            border: '1px solid #fef08a',
            borderRadius: '6px',
            padding: '16px',
            marginBottom: '20px',
          }}
        >
          <h3 style={{ margin: 0, color: '#854d0e' }}>⚠️ AI Research Alerts (FR-035)</h3>
          <ul style={{ listStyle: 'none', padding: 0, marginTop: '8px' }}>
            {data.agent_alerts.map((alert) => (
              <li
                key={alert.id}
                data-testid={`faculty-dashboard-alert-${alert.id}`}
                style={{ marginBottom: '6px', fontSize: '0.9rem' }}
              >
                {alert.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      {screenState === 'empty' ? (
        <div
          data-testid="faculty-dashboard-empty"
          style={{ padding: '32px', textAlign: 'center', backgroundColor: '#f9fafb', borderRadius: '8px' }}
        >
          <h3>No research opportunities posted yet</h3>
          <p>Create and publish research opportunities to receive student applications.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Pending applicants */}
          <section data-testid="faculty-dashboard-applicants-section">
            <h2>Pending Applicants ({data?.pending_applicants?.length})</h2>
            <ul data-testid="faculty-dashboard-applicants-list" style={{ listStyle: 'none', padding: 0 }}>
              {data?.pending_applicants?.map((app) => (
                <li
                  key={app.application_id}
                  data-testid={`faculty-dashboard-applicant-${app.application_id}`}
                  style={{
                    padding: '12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    marginBottom: '8px',
                  }}
                >
                  <strong>{app.student_name}</strong> - {app.opportunity_title}
                  <div>Status: {app.status}</div>
                </li>
              ))}
            </ul>
          </section>

          {/* Active Projects */}
          <section data-testid="faculty-dashboard-projects-section">
            <h2>Active Projects ({data?.active_projects?.length})</h2>
            <ul data-testid="faculty-dashboard-projects-list" style={{ listStyle: 'none', padding: 0 }}>
              {data?.active_projects?.map((proj) => (
                <li
                  key={proj.id}
                  data-testid={`faculty-dashboard-project-${proj.id}`}
                  style={{
                    padding: '12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    marginBottom: '8px',
                  }}
                >
                  <strong>{proj.title}</strong>
                  {proj.overdue_milestones > 0 && (
                    <span style={{ color: '#dc2626', marginLeft: '8px', fontSize: '0.85rem' }}>
                      ({proj.overdue_milestones} overdue)
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

