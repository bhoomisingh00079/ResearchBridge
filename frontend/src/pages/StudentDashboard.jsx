import React, { useState, useEffect } from 'react';
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
export default function StudentDashboard({ token }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [screenState, setScreenState] = useState('loading'); // 'loading' | 'ready' | 'empty' | 'error' | 'access-denied'
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    async function loadDashboard() {
      setScreenState('loading');
      try {
        const res = await fetch('/dashboard/student', {
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

  if (screenState === 'loading') {
    return (
      <div data-testid="student-dashboard-loading" style={{ padding: '24px', textAlign: 'center' }}>
        <h2>Loading your research workspace...</h2>
      </div>
    );
  }

  if (screenState === 'access-denied') {
    return (
      <div
        data-testid="student-dashboard-access-denied"
        style={{ padding: '24px', backgroundColor: '#fef2f2', border: '1px solid #f87171', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#991b1b' }}>Access Denied</h2>
        <p>You must be signed in with a verified Student account to view this dashboard.</p>
      </div>
    );
  }

  if (screenState === 'error') {
    return (
      <div
        data-testid="student-dashboard-error"
        style={{ padding: '24px', backgroundColor: '#fff7ed', border: '1px solid #fdba74', borderRadius: '8px' }}
      >
        <h2 style={{ color: '#c2410c' }}>Service Unavailable</h2>
        <p>{errorMsg}</p>
      </div>
    );
  }

  return (
    <div data-testid="student-dashboard-container" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <header style={{ marginBottom: '20px' }}>
        <h1 data-testid="student-dashboard-welcome">Welcome, {dashboardData?.user?.name}</h1>
        <p style={{ color: '#4b5563' }}>Manage your applications, active projects, and research milestones.</p>
      </header>

      {/* Advisory recommendations panel loads independently (NFR-002, 3.1.1) */}
      <AgentPanel token={token} apiUrl="/agent/recommendations" />

      {screenState === 'empty' ? (
        <div
          data-testid="student-dashboard-empty"
          style={{ padding: '32px', textAlign: 'center', backgroundColor: '#f9fafb', borderRadius: '8px' }}
        >
          <h3>No research activities yet</h3>
          <p>Explore opportunities and submit applications to start collaborating.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Applications list */}
          <section data-testid="student-dashboard-applications-section">
            <h2>My Applications ({dashboardData.applications.length})</h2>
            <ul data-testid="student-dashboard-applications-list" style={{ listStyle: 'none', padding: 0 }}>
              {dashboardData.applications.map((app) => (
                <li
                  key={app.id}
                  data-testid={`student-dashboard-app-${app.id}`}
                  style={{
                    padding: '12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    marginBottom: '8px',
                  }}
                >
                  <strong>{app.opportunity_title}</strong>
                  <div>
                    Status: <span data-testid={`student-dashboard-app-status-${app.id}`}>{app.status}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {/* Active Projects & Milestones */}
          <section data-testid="student-dashboard-projects-section">
            <h2>Active Projects ({dashboardData.projects.length})</h2>
            <ul data-testid="student-dashboard-projects-list" style={{ listStyle: 'none', padding: 0 }}>
              {dashboardData.projects.map((proj) => (
                <li
                  key={proj.project_id}
                  data-testid={`student-dashboard-proj-${proj.project_id}`}
                  style={{
                    padding: '12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    marginBottom: '8px',
                  }}
                >
                  <strong>{proj.title}</strong> ({proj.role_in_project})
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Domain: {proj.domain}</div>
                  {proj.milestones.length > 0 && (
                    <ul style={{ marginTop: '8px', paddingLeft: '16px' }}>
                      {proj.milestones.map((ms) => (
                        <li key={ms.id}>
                          {ms.description} - Due: {ms.target_date} ({ms.status})
                        </li>
                      ))}
                    </ul>
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

