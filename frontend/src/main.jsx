import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, json } from "./api.js";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import FacultyDashboard from "./pages/FacultyDashboard.jsx";
import CoordinatorDashboard from "./pages/CoordinatorDashboard.jsx";
import "./styles.css";

function currentRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const path = window.location.pathname.replace(/^\//, "");
  const routeString = hash || path;
  const parts = routeString.split("/").filter(Boolean);
  if (!parts.length) return { page: "home" };
  if (parts[0] === "opportunities" && parts[1]) return { page: "opportunity", id: parts[1] };
  if (parts[0] === "edit" && parts[1]) return { page: "edit", id: parts[1] };
  if (parts[0] === "review" && parts[1]) return { page: "review", id: parts[1] };
  if (parts[0] === "verify" && parts[1]) return { page: "verify", token: parts[1] };
  return { page: parts[0] };
}

function go(path) {
  window.location.hash = `/${path}`;
}

function Button({ children, variant = "primary", ...props }) {
  return <button className={`button button-${variant}`} {...props}>{children}</button>;
}

function FormField({ label, id, ...props }) {
  const { as, children, ...controlProps } = props;
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      {as === "textarea" ? <textarea id={id} {...controlProps} /> :
        as === "select" ? <select id={id} {...controlProps}>{children}</select> :
          <input id={id} {...controlProps} />}
    </label>
  );
}

function PageState({ kind = "loading", title, message, onRetry }) {
  const labels = {
    loading: ["Gathering the Codex", "Consulting the academy archives and research records…"],
    empty: ["The Archive Is Still", "When a question is posed or an expedition begins, it will appear here."],
    error: ["A Disturbance in the Records", "We could not access the requested archive. Please try again in a moment."],
    denied: ["Restricted Quarters", "Your scholar credentials do not grant access to this academy chamber."],
  };
  const [defaultTitle, defaultMessage] = labels[kind] || labels.error;
  return (
    <section className={`state-card state-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span className="state-mark" aria-hidden="true">
        {kind === "loading" ? "◌" : kind === "empty" ? "✦" : kind === "denied" ? "⌑" : "!"}
      </span>
      <h2>{title || defaultTitle}</h2>
      <p>{message || defaultMessage}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry} data-testid="state-retry">Try again</Button>}
    </section>
  );
}

/* Original Scholarium Insignia SVG */
function AcademyEmblem() {
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true">
      {/* Outer celestial circle */}
      <circle cx="20" cy="20" r="18" fill="none" stroke="#C7A45A" strokeWidth="1.5" strokeDasharray="3 2" opacity="0.75" />
      {/* Inner ring */}
      <circle cx="20" cy="20" r="15" fill="none" stroke="#E4CC8A" strokeWidth="1" opacity="0.9" />
      {/* Open Book Base */}
      <path d="M12 25 C15 22 18 23 20 25 C22 23 25 22 28 25 L28 17 C25 15 22 15.5 20 17.5 C18 15.5 15 15 12 17 Z" fill="#102A24" stroke="#C7A45A" strokeWidth="1.2" />
      {/* Center Spine */}
      <line x1="20" y1="17.5" x2="20" y2="25" stroke="#C7A45A" strokeWidth="1" />
      {/* Arch Bridge beneath */}
      <path d="M14 28 Q20 22 26 28" fill="none" stroke="#C7A45A" strokeWidth="1.5" strokeLinecap="round" />
      {/* Guiding Star above */}
      <path d="M20 9 L21 12 L24 13 L21 14 L20 17 L19 14 L16 13 L19 12 Z" fill="#E4CC8A" />
    </svg>
  );
}

function App() {
  const [route, setRoute] = useState(currentRoute);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(Boolean(sessionStorage.getItem("rb-token")));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const change = () => {
      setRoute(currentRoute());
      setMobileNavOpen(false);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);

  useEffect(() => {
    let live = true;
    if (!sessionStorage.getItem("rb-token")) {
      setAuthLoading(false);
      return () => { live = false; };
    }
    api("/me")
      .then((data) => { if (live) setUser(data); })
      .catch(() => {
        sessionStorage.removeItem("rb-token");
        if (live) setUser(null);
      })
      .finally(() => { if (live) setAuthLoading(false); });
    return () => { live = false; };
  }, []);

  async function signedIn(token) {
    sessionStorage.setItem("rb-token", token);
    const data = await api("/me");
    setUser(data);
    go("dashboard");
  }

  function signOut() {
    sessionStorage.removeItem("rb-token");
    setUser(null);
    go("home");
  }

  const page = useMemo(() => {
    if (authLoading) return <PageState kind="loading" title="Entering the Scholarium" />;
    if (route.page === "home") return <Home user={user} />;
    if (route.page === "login" || route.page === "register") return <AuthPage mode={route.page} onSignedIn={signedIn} />;
    if (route.page === "verify") return <VerifyPage token={route.token} />;
    if (route.page === "dashboard") {
      const token = sessionStorage.getItem("rb-token");
      if (!user) return <PageState kind="denied" message="Please enter the academy to view your research chamber." />;
      if (user.role === "Student") return <StudentDashboard token={token} />;
      if (user.role === "Faculty") return <FacultyDashboard token={token} />;
      if (user.role === "Coordinator" || user.role === "Administrator") return <CoordinatorDashboard token={token} />;
      return <PageState kind="denied" message="Dashboard is not available for this role." />;
    }
    if (route.page === "opportunities") return <OpportunityList user={user} />;
    if (route.page === "my-opportunities") return <MyOpportunities user={user} />;
    if (route.page === "my-applications") return <MyApplications user={user} />;
    if (route.page === "opportunity") return <OpportunityDetail id={route.id} user={user} />;
    if (route.page === "edit") return <EditOpportunity id={route.id} user={user} />;
    if (route.page === "profile") return <ProfilePage user={user} />;
    if (route.page === "create") return <CreateOpportunity user={user} />;
    if (route.page === "review") return <ApplicantReview id={route.id} user={user} />;
    if (route.page === "admin") return <AdminUsers user={user} />;
    return <PageState kind="empty" title="Uncharted Chamber" message="Use the navigation rail to return to a known academy chamber." />;
  }, [authLoading, route, user]);

  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">Skip to content</a>

      {/* Sidebar Navigation Rail — Hogwarts Carved Oak & Gold */}
      <aside className={`sidebar ${mobileNavOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-sticky-head">
          <a className="brand" href="#/" aria-label="The Scholarium home">
            <span className="brand-mark" aria-hidden="true"><AcademyEmblem /></span>
            <div className="brand-title-wrap">
              <span className="brand-name">Research<span>Bridge</span></span>
              <span className="brand-tagline">✦ THE SCHOLARIUM ✦</span>
            </div>
          </a>
        </div>

        <div className="sidebar-scrollable-content">
          <div className="nav-group">
            <div className="nav-label">✦ THE GREAT HALLS</div>
            <nav aria-label="Great halls navigation" className="side-nav">
              <a href="#/" className={route.page === "home" ? "is-active" : ""}>
                <span className="nav-icon" aria-hidden="true">🏛️</span> Academy Portal
              </a>
              {user && (
                <a href="#/dashboard" data-testid="nav-dashboard" className={route.page === "dashboard" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">✧</span>
                  {user.role === "Student" ? "The Scholar's Chamber" : user.role === "Faculty" ? "The Faculty Chamber" : "The Observatory"}
                </a>
              )}
              <a href="#/opportunities" data-testid="nav-opportunities" className={route.page === "opportunities" ? "is-active" : ""}>
                <span className="nav-icon" aria-hidden="true">📜</span> The Great Archive
              </a>
            </nav>
          </div>

          <div className="nav-group">
            <div className="nav-label">✦ EXPEDITION LEDGER</div>
            <nav aria-label="Expedition navigation" className="side-nav">
              {user?.role === "Student" && (
                <a href="#/my-applications" data-testid="nav-my-applications" className={route.page === "my-applications" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">⌛</span> My Applications
                </a>
              )}
              {user?.role === "Faculty" && (
                <a href="#/create" data-testid="nav-create" className={route.page === "create" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">✦</span> New Research Question
                </a>
              )}
              {user?.role === "Faculty" && (
                <a href="#/my-opportunities" data-testid="nav-my-opportunities" className={route.page === "my-opportunities" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">📖</span> My Portfolio
                </a>
              )}
              {user && (
                <a href="/workspace" target="_blank" rel="noopener noreferrer" data-testid="nav-workspace">
                  <span className="nav-icon" aria-hidden="true">🗺️</span> Research Expedition ↗
                </a>
              )}
              {user?.role === "Administrator" && (
                <a href="#/admin" data-testid="nav-admin" className={route.page === "admin" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">⚜️</span> Academy Registry
                </a>
              )}
            </nav>
          </div>

          <div className="nav-group">
            <div className="nav-label">✦ THE SCHOLAR’S CODEX</div>
            <nav aria-label="Codex navigation" className="side-nav">
              {user && (
                <a href="#/profile" data-testid="nav-profile" className={route.page === "profile" ? "is-active" : ""}>
                  <span className="nav-icon" aria-hidden="true">🖋️</span> Scholar Profile & Codex
                </a>
              )}
            </nav>
          </div>

          <div className="sidebar-note">
            <div className="sidebar-note-kicker">EX UMBRA IN SOLEM</div>
            <strong>Good research grows together.</strong>
            <p>Find a question worth asking, then find your people.</p>
          </div>

          <div className="sidebar-bottom">
            <span className="status-dot" aria-hidden="true" />
            <span>The Scholarium · Sanctuary of Questions</span>
          </div>
        </div>
      </aside>

      {/* Main Content Column */}
      <div className="main-column">
        <header className="topbar">
          <button
            className="mobile-nav-toggle"
            type="button"
            onClick={() => setMobileNavOpen((o) => !o)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
          <div className="mobile-brand">
            <span className="brand-mark" style={{ width: 28, height: 28 }}><AcademyEmblem /></span>
            <span>The Scholarium</span>
          </div>
          <div className="breadcrumb">
            <span className="crumb-academy">The Scholarium</span>
            <span>/</span>
            <span>{route.page === "home" ? "Welcome" : route.page.replaceAll("-", " ")}</span>
          </div>
          <div className="top-actions">
            {user ? (
              <>
                <span className="user-chip">
                  <span className="avatar">{user.name?.slice(0, 1).toUpperCase()}</span>
                  <span>
                    {user.name}
                    <small>{user.role}</small>
                  </span>
                </span>
                <Button variant="quiet" onClick={signOut} data-testid="nav-signout">Sign out</Button>
              </>
            ) : (
              <>
                <a className="top-login" href="#/login" data-testid="nav-login">Sign in</a>
                <Button onClick={() => go("register")} data-testid="nav-register">Join ResearchBridge</Button>
              </>
            )}
          </div>
        </header>

        <main id="main" className="page-content" tabIndex="-1">
          {page}
        </main>

        <footer className="footer">
          <span>ResearchBridge · The Scholarium</span>
          <span>An academy for questions that change the world.</span>
        </footer>
      </div>
    </div>
  );
}

/* Original Scholarium Twilight Academy Illustration */
function ScholariumHeroIllustration() {
  return (
    <div className="scholarium-illustration" role="img" aria-label="Illustration of The Scholarium twilight grand library and observatory">
      <svg viewBox="0 0 540 480" fill="none" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="skyGlow" cx="60%" cy="30%" r="60%">
            <stop offset="0%" stopColor="#1C453B" />
            <stop offset="60%" stopColor="#102A24" />
            <stop offset="100%" stopColor="#0B1C18" />
          </radialGradient>
          <linearGradient id="windowGlow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFEBB0" />
            <stop offset="70%" stopColor="#E4CC8A" />
            <stop offset="100%" stopColor="#986B27" />
          </linearGradient>
          <linearGradient id="wallGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1B3830" />
            <stop offset="100%" stopColor="#102520" />
          </linearGradient>
        </defs>

        {/* Sky Base */}
        <rect width="540" height="480" fill="url(#skyGlow)" />

        {/* Constellation Network Lines */}
        <g stroke="#C7A45A" strokeWidth="0.8" opacity="0.38">
          <line x1="80" y1="60" x2="150" y2="90" />
          <line x1="150" y1="90" x2="220" y2="50" />
          <line x1="220" y1="50" x2="310" y2="70" />
          <line x1="310" y1="70" x2="410" y2="40" />
          <line x1="410" y1="40" x2="490" y2="95" />
          <line x1="150" y1="90" x2="180" y2="150" />
          <line x1="310" y1="70" x2="340" y2="130" />
        </g>

        {/* Constellation Star Nodes */}
        <g fill="#E4CC8A">
          <circle cx="80" cy="60" r="2.5" />
          <circle cx="150" cy="90" r="3.5" />
          <circle cx="220" cy="50" r="2" />
          <circle cx="310" cy="70" r="4" />
          <circle cx="410" cy="40" r="3" />
          <circle cx="490" cy="95" r="2.5" />
          <circle cx="180" cy="150" r="2" />
          <circle cx="340" cy="130" r="2.5" />
        </g>

        {/* Distant Spire silhouettes */}
        <polygon points="60,480 60,260 85,160 110,260 110,480" fill="#0E211D" />
        <polygon points="430,480 430,240 455,140 480,240 480,480" fill="#0E211D" />

        {/* Main Scholarium Grand Library Central Mass */}
        <rect x="130" y="210" width="280" height="270" fill="url(#wallGradient)" stroke="#C7A45A" strokeWidth="0.8" strokeOpacity="0.3" />

        {/* Gothic Arched Central Tower Roof */}
        <polygon points="120,210 270,110 420,210" fill="#143029" stroke="#C7A45A" strokeWidth="1" strokeOpacity="0.4" />
        <line x1="270" y1="110" x2="270" y2="80" stroke="#C7A45A" strokeWidth="1.5" />
        <circle cx="270" cy="78" r="4" fill="#E4CC8A" />

        {/* Gothic Arched Windows - Left */}
        <path d="M165 320 C165 270 205 270 205 320 L205 380 L165 380 Z" fill="url(#windowGlow)" opacity="0.9" />
        <path d="M165 320 Q185 275 205 320" fill="none" stroke="#102A24" strokeWidth="2" />
        <line x1="185" y1="275" x2="185" y2="380" stroke="#102A24" strokeWidth="1.5" />
        <line x1="165" y1="330" x2="205" y2="330" stroke="#102A24" strokeWidth="1.5" />

        {/* Gothic Arched Windows - Center Grand Rose Window */}
        <circle cx="270" cy="270" r="32" fill="url(#windowGlow)" opacity="0.95" />
        <circle cx="270" cy="270" r="32" fill="none" stroke="#102A24" strokeWidth="2.5" />
        <circle cx="270" cy="270" r="14" fill="none" stroke="#102A24" strokeWidth="1.5" />
        <line x1="270" y1="238" x2="270" y2="302" stroke="#102A24" strokeWidth="1.5" />
        <line x1="238" y1="270" x2="302" y2="270" stroke="#102A24" strokeWidth="1.5" />
        <line x1="247" y1="247" x2="293" y2="293" stroke="#102A24" strokeWidth="1.2" />
        <line x1="247" y1="293" x2="293" y2="247" stroke="#102A24" strokeWidth="1.2" />

        {/* Gothic Arched Windows - Right */}
        <path d="M335 320 C335 270 375 270 375 320 L375 380 L335 380 Z" fill="url(#windowGlow)" opacity="0.9" />
        <path d="M335 320 Q355 275 375 320" fill="none" stroke="#102A24" strokeWidth="2" />
        <line x1="355" y1="275" x2="355" y2="380" stroke="#102A24" strokeWidth="1.5" />
        <line x1="335" y1="330" x2="375" y2="330" stroke="#102A24" strokeWidth="1.5" />

        {/* Grand Stone Entrance Portal */}
        <path d="M235 480 L235 410 C235 380 305 380 305 410 L305 480 Z" fill="#0B1C18" stroke="#C7A45A" strokeWidth="1.5" />
        <path d="M245 480 L245 420 C245 400 295 400 295 420 L295 480 Z" fill="#E4CC8A" opacity="0.3" />

        {/* Floating Illuminated Manuscripts */}
        <g transform="translate(100, 170) rotate(-12)" opacity="0.85">
          <rect width="26" height="34" rx="2" fill="#F4EBDD" stroke="#C7A45A" strokeWidth="0.8" />
          <line x1="4" y1="8" x2="22" y2="8" stroke="#102A24" strokeWidth="1" />
          <line x1="4" y1="14" x2="18" y2="14" stroke="#102A24" strokeWidth="0.8" />
          <line x1="4" y1="20" x2="20" y2="20" stroke="#102A24" strokeWidth="0.8" />
        </g>
        <g transform="translate(415, 185) rotate(15)" opacity="0.85">
          <rect width="24" height="32" rx="2" fill="#F4EBDD" stroke="#C7A45A" strokeWidth="0.8" />
          <line x1="4" y1="7" x2="20" y2="7" stroke="#102A24" strokeWidth="1" />
          <line x1="4" y1="13" x2="16" y2="13" stroke="#102A24" strokeWidth="0.8" />
          <line x1="4" y1="19" x2="18" y2="19" stroke="#102A24" strokeWidth="0.8" />
        </g>
      </svg>
      <div className="illustration-overlay-tag">✦ The Scholarium Archives</div>
      <div className="illustration-overlay-quote">
        <b>An Academy for Questions That Change the World</b>
        <span>Where curious minds cross thresholds into discovery together.</span>
      </div>
    </div>
  );
}

function Home({ user }) {
  const [previewOpps, setPreviewOpps] = useState([]);
  const [previewState, setPreviewState] = useState("loading");

  useEffect(() => {
    let live = true;
    api("/opportunities?available=true")
      .then((data) => {
        if (live) {
          setPreviewOpps(data.items?.slice(0, 4) || []);
          setPreviewState("ready");
        }
      })
      .catch(() => {
        if (live) setPreviewState("error");
      });
    return () => { live = false; };
  }, []);

  return (
    <div className="landing">
      {/* 1. Cinematic Hero Section */}
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="hero-eyebrow">
            <span>✦</span> WELCOME TO THE SCHOLARIUM
          </div>
          <h1>Great discoveries begin with <em>a question.</em></h1>
          <p>
            Find faculty-led research, discover collaborators who share your curiosity,
            and turn ambitious ideas into work that matters.
          </p>
          <div className="hero-actions">
            <Button onClick={() => go(user ? "dashboard" : "opportunities")} data-testid="home-explore">
              Enter the Academy <span aria-hidden="true">→</span>
            </Button>
            {!user && (
              <a href="#/opportunities" className="text-action" data-testid="home-join">
                Discover Your Research Path <span aria-hidden="true">↗</span>
              </a>
            )}
          </div>
          <div className="hero-proof">
            <span className="proof-stars" aria-hidden="true">✦ ✦ ✦</span>
            <span>Where students and faculty move research forward together.</span>
          </div>
        </div>
        <ScholariumHeroIllustration />
      </section>

      {/* 2. Editorial Section: A Question Can Take You Anywhere */}
      <section className="landing-section">
        <div className="landing-section-header">
          <div className="eyebrow">A QUESTION CAN TAKE YOU ANYWHERE</div>
          <h2>Your Journey Through The Scholarium</h2>
          <p>From an initial spark of curiosity to meaningful collaborative results.</p>
        </div>
        <div className="stages-grid">
          <article className="stage-card">
            <div className="stage-numeral">
              <span>EXPEDITION STAGE I</span>
              <span className="stage-icon">⌕</span>
            </div>
            <h3>Find Your Question</h3>
            <p>Explore faculty-led opportunities categorized by research domain, methodological skills, and active timelines.</p>
          </article>
          <article className="stage-card">
            <div className="stage-numeral">
              <span>EXPEDITION STAGE II</span>
              <span className="stage-icon">◉</span>
            </div>
            <h3>Find Your Research Circle</h3>
            <p>Submit structured applications, share your motivation and prior experience, and connect directly with mentors.</p>
          </article>
          <article className="stage-card">
            <div className="stage-numeral">
              <span>EXPEDITION STAGE III</span>
              <span className="stage-icon">↗</span>
            </div>
            <h3>Turn Discovery Into Progress</h3>
            <p>Work across milestones, document progress in dedicated research workspaces, and build lasting scholarship.</p>
          </article>
        </div>
      </section>

      {/* 3. The Research Archive: Real Data Preview */}
      <section className="landing-section">
        <div className="landing-section-header">
          <div className="eyebrow">THE RESEARCH ARCHIVE</div>
          <h2>Open Questions Seeking Scholars</h2>
          <p>Real faculty-led projects currently accepting student researchers across domains.</p>
        </div>

        {previewState === "loading" && <PageState kind="loading" title="Surveying open questions" />}
        {previewState === "error" && (
          <div className="state-card state-empty">
            <p>The archive catalogue is refreshing. You can browse all projects directly.</p>
            <Button variant="secondary" onClick={() => go("opportunities")}>Open Research Archive →</Button>
          </div>
        )}
        {previewState === "ready" && previewOpps.length > 0 && (
          <div className="opportunity-grid">
            {previewOpps.map((opp) => (
              <OpportunityCard key={opp.id} item={opp} />
            ))}
          </div>
        )}
      </section>

      {/* 4. Advisory Intelligence Banner */}
      <section className="scholarium-intel-banner">
        <div>
          <div className="scholarium-intel-badge">✦ Intelligence, With Human Judgment</div>
          <h3>The Seer’s Compass: Advisory AI That Respects Scholarship</h3>
          <p>
            Our intelligent recommendation engine provides advisory insight by connecting student interests
            and skills with active research questions. Advisory insights never make authoritative admissions
            or team decisions; our mentors retain full review authority.
          </p>
        </div>
        <div>
          <Button variant="secondary" onClick={() => go("opportunities")}>Explore Opportunities</Button>
        </div>
      </section>

      {/* 5. Final Call To Action */}
      <section className="scholarium-cta-banner">
        <div className="eyebrow">EVERY GREAT DISCOVERY HAS A BEGINNING</div>
        <h2>Begin Your Research Journey</h2>
        <p>Join the community of students and mentors who turn curiosity into discovery.</p>
        <div style={{ display: "flex", justifyContent: "center", gap: 12 }}>
          <Button onClick={() => go(user ? "dashboard" : "register")}>
            {user ? "Enter Your Chamber" : "Enter the Academy"} <span aria-hidden="true">→</span>
          </Button>
        </div>
      </section>
    </div>
  );
}

function AuthPage({ mode, onSignedIn }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [verificationToken, setVerificationToken] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      if (mode === "register") {
        const data = await api("/auth/register", json("POST", {
          name: form.get("name"),
          email: form.get("email"),
          password: form.get("password"),
          role: form.get("role"),
        }));
        if (data.dev_verify_token) setVerificationToken(data.dev_verify_token);
        else setNotice("Account created. Check your institutional inbox to verify your email before signing in.");
      } else {
        const data = await api("/auth/login", json("POST", {
          email: form.get("email"),
          password: form.get("password"),
        }));
        await onSignedIn(data.token);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyLocal() {
    setBusy(true);
    setError("");
    try {
      await api(`/auth/verify/${encodeURIComponent(verificationToken)}`, { method: "POST" });
      setVerificationToken("");
      setNotice("Your account is verified. You can enter the Scholarium now.");
      go("login");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <aside className="auth-aside">
        <div>
          <span className="auth-kicker">✦ YOUR NEXT CHAPTER BEGINS HERE</span>
          <h1>There is room for your curiosity.</h1>
          <p>Join a community of students and faculty moving research forward together.</p>
        </div>
        <div className="auth-aside-illustration">
          <span aria-hidden="true">✦</span>
          <small>
            Scholarly collaboration guided by thoughtful mentors and shared questions.
          </small>
        </div>
      </aside>

      <section className="auth-card">
        <span className="eyebrow">{mode === "register" ? "BEGIN YOUR JOURNEY" : "THE SCHOLARIUM"}</span>
        <h2>{mode === "register" ? "Begin Your Research Journey" : "Return to the Scholarium"}</h2>
        <p className="auth-subtitle">
          {mode === "register"
            ? "Create your account and find your place in the research community."
            : "Your research journey is waiting."}
        </p>

        <div className="auth-tabs">
          <a className={mode === "login" ? "selected" : ""} href="#/login" data-testid="auth-tab-login">
            Sign in
          </a>
          <a className={mode === "register" ? "selected" : ""} href="#/register" data-testid="auth-tab-register">
            Create account
          </a>
        </div>

        {verificationToken ? (
          <div className="notice-box">
            <strong>One more step</strong>
            <p>Development mode returned an accreditation verification token.</p>
            <Button onClick={verifyLocal} disabled={busy} data-testid="register-verify">Verify account</Button>
          </div>
        ) : (
          <form onSubmit={submit} className="stack-form" noValidate>
            {mode === "register" && (
              <>
                <FormField
                  label="Full name"
                  id="auth-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  required
                  minLength="1"
                  maxLength="160"
                  data-testid="auth-name"
                />
                <FormField
                  label="I am joining as"
                  id="auth-role"
                  name="role"
                  as="select"
                  data-testid="auth-role"
                >
                  <option value="Student">Student researcher</option>
                  <option value="Faculty">Faculty mentor</option>
                </FormField>
              </>
            )}
            <FormField
              label="Institutional email"
              id="auth-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              data-testid="auth-email"
            />
            <FormField
              label="Password"
              id="auth-password"
              name="password"
              type="password"
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              required
              minLength={mode === "register" ? 8 : undefined}
              data-testid="auth-password"
            />

            {error && <p className="form-message form-error" role="alert" data-testid="auth-error">{error}</p>}
            {notice && <p className="form-message form-success" role="status">{notice}</p>}

            <Button
              type="submit"
              disabled={busy}
              data-testid={mode === "register" ? "auth-register-submit" : "auth-login-submit"}
            >
              {busy ? "Please wait…" : mode === "register" ? "Create My Account" : "Enter the Academy"}
              <span aria-hidden="true">→</span>
            </Button>
            <p className="form-footnote">
              By entering, you commit to rigorous and respectful academic inquiry within The Scholarium.
            </p>
          </form>
        )}

        {notice && !verificationToken && <p className="form-message form-success" role="status">{notice}</p>}
        <a href="#/opportunities" className="back-link" style={{ marginTop: 18 }} data-testid="auth-back-explore">
          ← Explore public opportunities
        </a>
      </section>
    </div>
  );
}

function VerifyPage({ token }) {
  const [state, setState] = useState("ready");
  const [message, setMessage] = useState("Use the button below to verify your institutional account.");

  async function verify() {
    setState("loading");
    try {
      await api(`/auth/verify/${encodeURIComponent(token)}`, { method: "POST" });
      setMessage("Your scholar account is verified. You may enter the academy now.");
      setState("success");
    } catch (error) {
      setMessage(error.message);
      setState("error");
    }
  }

  return (
    <div className="auth-layout">
      <aside className="auth-aside">
        <span className="auth-kicker">✦ RESEARCH ACCREDITATION</span>
        <h1>One step into the academy.</h1>
        <p>We verify institutional accounts to protect the integrity of collaborative scholarship.</p>
      </aside>
      <section className="auth-card">
        <span className="eyebrow">THE SCHOLARIUM</span>
        <h2>Your Entry Is Being Verified</h2>
        <p className="auth-subtitle">{message}</p>
        {state === "ready" && (
          <Button onClick={verify} data-testid="verify-submit">
            Verify account <span aria-hidden="true">→</span>
          </Button>
        )}
        {state === "loading" && <PageState kind="loading" title="Verifying your scholar credentials" />}
        {state === "error" && <p className="form-message form-error" role="alert">{message}</p>}
        {state === "error" && (
          <Button variant="secondary" onClick={verify} data-testid="verify-retry">Try again</Button>
        )}
        {state === "success" && <p className="form-message form-success" role="status">{message}</p>}
        {state === "success" && (
          <Button onClick={() => go("login")} data-testid="verify-login">Continue to sign in</Button>
        )}
      </section>
    </div>
  );
}

function OpportunityList({ user }) {
  const [filters, setFilters] = useState({ q: "", domain: "", skill: "", duration: "", available: false });
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");

  async function load(next = filters) {
    setState("loading");
    setError("");
    const query = new URLSearchParams();
    for (const key of ["q", "domain", "skill", "duration"]) {
      if (next[key].trim()) query.set(key, next[key].trim());
    }
    if (next.available) query.set("available", "true");
    try {
      const result = await api(`/opportunities?${query}`);
      setData(result.items || []);
      setState(result.items?.length ? "ready" : "empty");
    } catch (err) {
      setError(err.message);
      setState(err.status === 403 ? "denied" : "error");
    }
  }

  useEffect(() => { load(); }, []);

  function update(key, value) {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="EXPLORE THE ACADEMY"
        title="The Great Research Archive"
        text="Discover open questions, find your research interests, and meet the faculty guiding them."
      />

      <form className="filter-panel" onSubmit={(event) => { event.preventDefault(); load(); }}>
        <FormField
          label="Search projects"
          id="search-q"
          name="q"
          value={filters.q}
          onChange={(e) => update("q", e.target.value)}
          placeholder="Title, research question, or concept"
          data-testid="opportunities-search"
        />
        <FormField
          label="Research area"
          id="search-domain"
          name="domain"
          value={filters.domain}
          onChange={(e) => update("domain", e.target.value)}
          placeholder="e.g. AI, Biotechnology, Physics"
          data-testid="opportunities-domain"
        />
        <FormField
          label="Required skill"
          id="search-skill"
          name="skill"
          value={filters.skill}
          onChange={(e) => update("skill", e.target.value)}
          placeholder="e.g. Python, Fieldwork, PyTorch"
          data-testid="opportunities-skill"
        />
        <div className="filter-bottom">
          <FormField
            label="Duration"
            id="search-duration"
            name="duration"
            value={filters.duration}
            onChange={(e) => update("duration", e.target.value)}
            placeholder="e.g. 10 weeks, Semester"
            data-testid="opportunities-duration"
          />
          <label className="check-field">
            <input
              type="checkbox"
              checked={filters.available}
              onChange={(e) => update("available", e.target.checked)}
              data-testid="opportunities-available"
            />
            Has open places
          </label>
          <Button type="submit" data-testid="opportunities-filter-submit">
            Search Archive <span aria-hidden="true">→</span>
          </Button>
        </div>
      </form>

      {state === "loading" && <PageState kind="loading" title="Consulting the Research Archive" />}
      {state === "empty" && (
        <PageState
          kind="empty"
          title="No open questions match your inquiry"
          message="Try broadening your research area or clearing active filter constraints."
        />
      )}
      {(state === "error" || state === "denied") && (
        <PageState kind={state} message={error} onRetry={() => load()} />
      )}
      {state === "ready" && (
        <div className="result-heading">
          <strong>{data.length} {data.length === 1 ? "Active Expedition" : "Active Expeditions"}</strong>
          <span>Recorded in the Scholarium catalogue</span>
        </div>
      )}
      {state === "ready" && (
        <div className="opportunity-grid">
          {data.map((item) => <OpportunityCard key={item.id} item={item} />)}
        </div>
      )}

      {!user && (
        <div className="state-card" style={{ marginTop: 28, background: "#EFE8DC" }}>
          <h2>Ready to pursue a question?</h2>
          <p>Join ResearchBridge as a student researcher to submit applications and join active research groups.</p>
          <a href="#/register" className="button" data-testid="opportunities-join">
            Join ResearchBridge ↗
          </a>
        </div>
      )}
    </div>
  );
}

function PageHeading({ eyebrow, title, text, action }) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      {action}
    </div>
  );
}

function OpportunityCard({ item }) {
  return (
    <article className="opportunity-card">
      <div>
        <div className="card-topline">
          <StatusBadge status={item.status || "Published"} />
          <span className="card-id">RB-A{String(item.id).padStart(4, "0")}</span>
        </div>
        <h2>
          <a href={`#/opportunities/${item.id}`} data-testid={`opportunity-title-${item.id}`}>
            {item.title}
          </a>
        </h2>
        <p className="card-description">{item.description}</p>
      </div>

      <div>
        <div className="opportunity-meta">
          <span><b>Domain</b>{item.domain}</span>
          <span><b>Duration</b>{item.duration || "Flexible"}</span>
          <span><b>Places</b>{item.available_places} of {item.capacity}</span>
        </div>
        <div className="skill-list">
          {(item.required_skills || []).slice(0, 4).map((skill) => (
            <span className="skill-chip" key={skill}>{skill}</span>
          ))}
        </div>
        <a className="card-link" href={`#/opportunities/${item.id}`} data-testid={`opportunity-open-${item.id}`}>
          Explore This Question <span aria-hidden="true">→</span>
        </a>
      </div>
    </article>
  );
}

function MyOpportunities({ user }) {
  const [items, setItems] = useState([]);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setError("");
    try {
      const result = await api("/opportunities/mine?offset=0&limit=100");
      setItems(result.items || []);
      setState(result.items?.length ? "ready" : "empty");
    } catch (err) {
      setError(err.message);
      setState(err.status === 403 ? "denied" : "error");
    }
  }

  useEffect(() => {
    if (user?.role === "Faculty") load();
  }, [user?.role]);

  if (user?.role !== "Faculty") {
    return (
      <div className="content-wrap">
        <PageState kind="denied" message="Faculty credentials are required to manage research opportunities." />
      </div>
    );
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="THE FACULTY LEDGER"
        title="Your Research Portfolio"
        text="Keep drafts moving, review applicants, and refine project requirements."
        action={
          <Button onClick={() => go("create")} data-testid="my-opportunities-create">
            New opportunity
          </Button>
        }
      />

      {state === "loading" && <PageState kind="loading" title="Consulting your faculty ledger" />}
      {state === "empty" && (
        <PageState
          kind="empty"
          title="No opportunities posted yet"
          message="Create a new draft to invite curious student researchers into your work."
        />
      )}
      {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}

      {state === "ready" && (
        <div className="opportunity-grid">
          {items.map((item) => (
            <article className="opportunity-card" key={item.id}>
              <div>
                <div className="card-topline">
                  <StatusBadge status={item.status} />
                  <span className="card-id">RB-A{String(item.id).padStart(4, "0")}</span>
                </div>
                <h2>
                  <a href={`#/opportunities/${item.id}`} data-testid={`managed-title-${item.id}`}>
                    {item.title}
                  </a>
                </h2>
                <p className="card-description">{item.description}</p>
              </div>

              <div>
                <div className="opportunity-meta">
                  <span><b>Domain</b>{item.domain}</span>
                  <span><b>Duration</b>{item.duration || "Flexible"}</span>
                  <span><b>Places</b>{item.available_places} of {item.capacity}</span>
                </div>
                <div className="managed-actions">
                  <a className="card-link" href={`#/opportunities/${item.id}`} data-testid={`managed-open-${item.id}`}>
                    Manage details →
                  </a>
                  <a className="card-link" href={`#/review/${item.id}`} data-testid={`managed-review-${item.id}`}>
                    Review applicants →
                  </a>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function MyApplications({ user }) {
  const [items, setItems] = useState([]);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  async function load() {
    setState("loading");
    setError("");
    try {
      const result = await api("/applications/mine");
      setItems(result);
      setState(result.length ? "ready" : "empty");
    } catch (err) {
      setError(err.message);
      setState(err.status === 403 ? "denied" : "error");
    }
  }

  useEffect(() => {
    if (user?.role === "Student") load();
  }, [user?.role]);

  async function withdraw(applicationId) {
    setBusy(applicationId);
    setError("");
    try {
      const updated = await api(`/applications/${applicationId}/withdraw`, { method: "POST" });
      setItems((old) => old.map((item) => (item.id === applicationId ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  if (user?.role !== "Student") {
    return (
      <div className="content-wrap">
        <PageState kind="denied" message="Sign in with a student account to view your applications." />
      </div>
    );
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="YOUR RESEARCH JOURNEY"
        title="Your Application Ledger"
        text="Follow every application from submission to its current faculty decision."
      />

      {state === "loading" && <PageState kind="loading" title="Retrieving your application dossier" />}
      {state === "empty" && (
        <div className="state-card state-empty">
          <span className="state-mark" aria-hidden="true">✦</span>
          <h2>Your first research chapter awaits.</h2>
          <p>Explore the Research Archive to find a question worth pursuing.</p>
          <Button onClick={() => go("opportunities")} style={{ marginTop: 8 }}>
            Explore Research Opportunities
          </Button>
        </div>
      )}
      {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}
      {state === "ready" && error && <p className="form-message form-error" role="alert">{error}</p>}

      {state === "ready" && (
        <div className="application-list">
          {items.map((item) => (
            <article className="application-card" key={item.id}>
              <div className="application-header">
                <div>
                  <span className="eyebrow">APPLICATION RB-A{String(item.id).padStart(4, "0")}</span>
                  <h2>
                    <a href={`#/opportunities/${item.opportunity_id}`} data-testid={`my-application-title-${item.id}`}>
                      {item.opportunity_title}
                    </a>
                  </h2>
                </div>
                <StatusBadge status={item.status} />
              </div>
              <p className="application-domain">
                {item.domain} · Submitted {new Date(item.submitted_at).toLocaleDateString()}
              </p>
              <div className="application-copy">
                <strong>Your Motivation</strong>
                <p>{item.motivation}</p>
              </div>
              {item.faculty_comment && (
                <div className="faculty-quote">
                  <strong>Faculty Feedback:</strong>
                  {item.faculty_comment}
                </div>
              )}
              {["Submitted", "Shortlisted"].includes(item.status) && (
                <div style={{ marginTop: 12 }}>
                  <Button
                    variant="quiet"
                    disabled={busy === item.id}
                    onClick={() => withdraw(item.id)}
                    data-testid={`my-application-withdraw-${item.id}`}
                  >
                    {busy === item.id ? "Withdrawing…" : "Withdraw application"}
                  </Button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function OpportunityDetail({ id, user }) {
  const [item, setItem] = useState(null);
  const [currentApplication, setCurrentApplication] = useState(null);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    api(`/opportunities/${id}`)
      .then((data) => {
        if (live) {
          setItem(data);
          setState("ready");
        }
      })
      .catch((err) => {
        if (live) {
          setError(err.message);
          setState(err.status === 403 ? "denied" : err.status === 404 ? "empty" : "error");
        }
      });

    if (user?.role === "Student") {
      api("/applications/mine")
        .then((rows) => {
          if (live) {
            setCurrentApplication(rows.find((row) => String(row.opportunity_id) === String(id) && row.status !== "Withdrawn") || null);
          }
        })
        .catch(() => {});
    }
    return () => { live = false; };
  }, [id, user?.role]);

  async function apply(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    setBusy(true);
    try {
      const submitted = await api(`/opportunities/${id}/apply`, json("POST", {
        motivation: new FormData(event.currentTarget).get("motivation"),
      }));
      setCurrentApplication(submitted);
      setMessage("Your application was submitted to the faculty mentor.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function changeState(action) {
    setBusy(true);
    setError("");
    const label = { publish: "published", close: "closed", archive: "archived" }[action];
    try {
      const updated = await api(`/opportunities/${id}/state/${action}`, { method: "POST" });
      setItem(updated);
      setMessage(`Opportunity ${label}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (state !== "ready") {
    return (
      <div className="content-wrap">
        <PageHeading eyebrow="RESEARCH DOSSIER" title="Research Question" text="Review the requirements and project scope." />
        <PageState
          kind={state}
          message={error}
          onRetry={() => {
            setState("loading");
            api(`/opportunities/${id}`)
              .then((data) => { setItem(data); setState("ready"); })
              .catch((err) => { setError(err.message); setState("error"); });
          }}
        />
      </div>
    );
  }

  return (
    <div className="content-wrap detail-page">
      <a href="#/opportunities" className="back-link" data-testid="opportunity-back">
        ← Back to opportunities
      </a>
      <div className="detail-layout">
        <article className="detail-main">
          <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
            <StatusBadge status={item.status} />
            <span className="detail-code">RB-A{String(item.id).padStart(4, "0")}</span>
          </div>
          <h1>{item.title}</h1>
          <p className="detail-intro">{item.description}</p>

          <div className="detail-section">
            <h2>Research Domain</h2>
            <p>{item.domain}</p>
          </div>

          <div className="detail-section">
            <h2>Desired Scholar Skills</h2>
            <div className="skill-list">
              {item.required_skills?.length ? (
                item.required_skills.map((skill) => <span className="skill-chip" key={skill}>{skill}</span>)
              ) : (
                <span className="muted">Discuss relevant skills directly with the faculty mentor.</span>
              )}
            </div>
          </div>

          <div className="detail-section">
            <h2>Project Scope & Methodology</h2>
            <p>{item.description}</p>
          </div>

          {message && <p className="form-message form-success" role="status">{message}</p>}
          {error && <p className="form-message form-error" role="alert">{error}</p>}

          {currentApplication && (
            <div className="apply-panel">
              <h2>Application Status: {currentApplication.status}</h2>
              <p>Your application is on record. Follow updates on your application ledger.</p>
              <a href="#/my-applications" className="card-link" data-testid="opportunity-my-applications">
                View my applications →
              </a>
            </div>
          )}

          {user?.role === "Student" && !currentApplication && item.status === "Published" && (
            <form className="apply-panel" onSubmit={apply}>
              <h2>Begin Your Application</h2>
              <p>Share what draws you to this question and how you hope to contribute.</p>
              <FormField
                label="Your Motivation"
                id="apply-motivation"
                name="motivation"
                as="textarea"
                rows="5"
                required
                maxLength="10000"
                placeholder="What draws you to this research question and what relevant background do you bring?"
                data-testid="apply-motivation"
              />
              <Button type="submit" disabled={busy} data-testid="apply-submit" style={{ marginTop: 12 }}>
                {busy ? "Submitting…" : "Submit Application"} <span aria-hidden="true">→</span>
              </Button>
            </form>
          )}

          {!user && (
            <div className="apply-panel">
              <h2>Interested in joining this expedition?</h2>
              <p>Sign in with your student account to apply for this project.</p>
              <Button onClick={() => go("login")} data-testid="opportunity-login">
                Sign in to apply
              </Button>
            </div>
          )}
        </article>

        <aside className="detail-aside">
          <div className="aside-card">
            <span className="eyebrow">RESEARCH BRIEF</span>
            <dl>
              <div>
                <dt>Research Domain</dt>
                <dd>{item.domain}</dd>
              </div>
              <div>
                <dt>Expected Duration</dt>
                <dd>{item.duration || "Flexible"}</dd>
              </div>
              <div>
                <dt>Available Places</dt>
                <dd>{item.available_places} of {item.capacity}</dd>
              </div>
              <div>
                <dt>Application Deadline</dt>
                <dd>{item.deadline || "Rolling consideration"}</dd>
              </div>
            </dl>

            {user?.role === "Faculty" && user.id === item.faculty_id && (
              <div className="faculty-actions">
                <Button variant="secondary" onClick={() => go(`edit/${item.id}`)} data-testid="opportunity-edit">
                  Edit details
                </Button>
                <Button variant="secondary" onClick={() => go(`review/${item.id}`)} data-testid="opportunity-review-applicants">
                  Review applicants
                </Button>
                {item.status === "Draft" && (
                  <Button onClick={() => changeState("publish")} disabled={busy} data-testid="opportunity-publish">
                    Publish opportunity
                  </Button>
                )}
                {item.status === "Published" && (
                  <Button variant="secondary" onClick={() => changeState("close")} disabled={busy} data-testid="opportunity-close">
                    Close opportunity
                  </Button>
                )}
                {item.status !== "Archived" && (
                  <Button variant="quiet" onClick={() => changeState("archive")} disabled={busy} data-testid="opportunity-archive">
                    Archive
                  </Button>
                )}
              </div>
            )}
          </div>

          <div className="mentor-note">
            <strong>Scholarly Inquiry</strong>
            <p>Every breakthrough begins with asking the right question and listening carefully to the data.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function ProfilePage({ user }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [profile, setProfile] = useState(null);
  const [loadState, setLoadState] = useState("loading");
  const student = user?.role === "Student";

  useEffect(() => {
    if (!user || (!student && user.role !== "Faculty")) {
      setLoadState("denied");
      return;
    }
    let live = true;
    api(`/profile/${student ? "student" : "faculty"}`)
      .then((data) => { if (live) { setProfile(data); setLoadState("ready"); } })
      .catch((err) => { if (live) { setError(err.message); setLoadState(err.status === 403 ? "denied" : "error"); } });
    return () => { live = false; };
  }, [user, student]);

  if (!user) return <div className="content-wrap"><PageState kind="denied" message="Sign in to manage your profile." /></div>;
  if (!student && user.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="This role does not have a research profile form." /></div>;
  if (loadState !== "ready") {
    return (
      <div className="content-wrap">
        <PageHeading eyebrow="YOUR ACADEMIC IDENTITY" title="Your Scholar’s Codex" text="Share your research interests, methodology skills, and questions." />
        <PageState
          kind={loadState}
          message={error}
          onRetry={() => {
            setLoadState("loading");
            api(`/profile/${student ? "student" : "faculty"}`)
              .then((data) => { setProfile(data); setLoadState("ready"); })
              .catch((err) => { setError(err.message); setLoadState("error"); });
          }}
        />
      </div>
    );
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData(event.currentTarget);
    const payload = student
      ? {
          research_experience: form.get("experience"),
          skills: splitTags(form.get("skills")),
          interests: splitTags(form.get("interests")),
        }
      : {
          bio: form.get("bio"),
          expertise: splitTags(form.get("expertise")),
        };

    try {
      await api(`/profile/${student ? "student" : "faculty"}`, json("PUT", payload));
      setNotice("Your Scholar’s Codex has been updated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="content-wrap narrow-content">
      <PageHeading
        eyebrow="YOUR ACADEMIC IDENTITY"
        title="Your Scholar’s Codex"
        text="A clear codex helps mentors and colleagues recognize the capabilities you bring."
      />

      <form className="surface-card stack-form" onSubmit={save}>
        <div className="profile-identity">
          <span className="avatar avatar-large">{user.name.slice(0, 1).toUpperCase()}</span>
          <div>
            <strong>{user.name}</strong>
            <span>{user.email} · {user.role}</span>
          </div>
        </div>

        {student ? (
          <>
            <FormField
              label="Research Experience & Coursework"
              id="profile-experience"
              name="experience"
              as="textarea"
              rows="5"
              maxLength="10000"
              defaultValue={profile?.research_experience || ""}
              placeholder="Share lab work, independent studies, or methodological experience."
              data-testid="profile-experience"
            />
            <FormField
              label="Methodological Skills (comma-separated)"
              id="profile-skills"
              name="skills"
              type="text"
              defaultValue={profile?.skills?.join(", ") || ""}
              placeholder="Python, Statistics, Lab assays, Literature review"
              data-testid="profile-skills"
            />
            <FormField
              label="Research Interests (comma-separated)"
              id="profile-interests"
              name="interests"
              type="text"
              defaultValue={profile?.interests?.join(", ") || ""}
              placeholder="Computational Biology, Machine Learning, Cognitive Science"
              data-testid="profile-interests"
            />
          </>
        ) : (
          <>
            <FormField
              label="Faculty Biography & Research Focus"
              id="profile-bio"
              name="bio"
              as="textarea"
              rows="6"
              maxLength="10000"
              defaultValue={profile?.bio || ""}
              placeholder="Your lab's core questions, methodological approach, and mentorship philosophy."
              data-testid="profile-bio"
            />
            <FormField
              label="Areas of Expertise (comma-separated)"
              id="profile-expertise"
              name="expertise"
              type="text"
              defaultValue={profile?.expertise?.join(", ") || ""}
              placeholder="Artificial Intelligence, Bioinformatics, Applied Optics"
              data-testid="profile-expertise"
            />
          </>
        )}

        {error && <p className="form-message form-error" role="alert" data-testid="profile-error">{error}</p>}
        {notice && <p className="form-message form-success" role="status">{notice}</p>}

        <Button type="submit" disabled={busy} data-testid="profile-save">
          {busy ? "Saving…" : "Update My Codex"} <span aria-hidden="true">→</span>
        </Button>
      </form>
    </div>
  );
}

function splitTags(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function CreateOpportunity({ user }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user?.role !== "Faculty") {
    return <div className="content-wrap"><PageState kind="denied" message="Only faculty members can open a new research question." /></div>;
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const item = await api("/opportunities", json("POST", {
        title: form.get("title"),
        description: form.get("description"),
        domain: form.get("domain"),
        duration: form.get("duration"),
        capacity: Number(form.get("capacity")),
        deadline: form.get("deadline") || null,
        required_skills: splitTags(form.get("skills")),
      }));
      go(`opportunities/${item.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="content-wrap narrow-content">
      <PageHeading
        eyebrow="THE FACULTY LEDGER"
        title="Open a New Research Question"
        text="Describe the challenge, define the scope, and invite the right collaborators."
      />

      <form className="surface-card stack-form" onSubmit={submit}>
        <FormField
          label="Opportunity Title"
          id="opp-title"
          name="title"
          required
          maxLength="200"
          placeholder="A clear, compelling research question"
          data-testid="create-title"
        />
        <FormField
          label="Project Description & Scope"
          id="opp-description"
          name="description"
          as="textarea"
          rows="7"
          required
          maxLength="20000"
          placeholder="What core problem will the student investigate or contribute toward?"
          data-testid="create-description"
        />
        <div className="form-row">
          <FormField
            label="Research Domain"
            id="opp-domain"
            name="domain"
            required
            maxLength="120"
            placeholder="e.g. AI Ethics, Molecular Genetics"
            data-testid="create-domain"
          />
          <FormField
            label="Expected Duration"
            id="opp-duration"
            name="duration"
            maxLength="120"
            placeholder="e.g. 12 weeks, Academic Year"
            data-testid="create-duration"
          />
        </div>
        <div className="form-row">
          <FormField
            label="Student Capacity"
            id="opp-capacity"
            name="capacity"
            type="number"
            min="1"
            max="10000"
            required
            defaultValue="1"
            data-testid="create-capacity"
          />
          <FormField
            label="Application Deadline"
            id="opp-deadline"
            name="deadline"
            type="date"
            data-testid="create-deadline"
          />
        </div>
        <FormField
          label="Required Skills (comma-separated)"
          id="opp-skills"
          name="skills"
          placeholder="Python, Linear Algebra, Literature Review"
          data-testid="create-skills"
        />

        {error && <p className="form-message form-error" role="alert" data-testid="create-error">{error}</p>}

        <div className="form-actions">
          <Button type="submit" disabled={busy} data-testid="create-submit">
            {busy ? "Saving…" : "Save Research Draft"} <span aria-hidden="true">→</span>
          </Button>
          <span>New opportunities begin as drafts. You can publish from the detail page.</span>
        </div>
      </form>
    </div>
  );
}

function EditOpportunity({ id, user }) {
  const [item, setItem] = useState(null);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    api(`/opportunities/${id}`)
      .then((data) => { if (live) { setItem(data); setState("ready"); } })
      .catch((err) => { if (live) { setError(err.message); setState(err.status === 403 ? "denied" : err.status === 404 ? "empty" : "error"); } });
    return () => { live = false; };
  }, [id]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api(`/opportunities/${id}`, json("PUT", {
        title: form.get("title"),
        description: form.get("description"),
        domain: form.get("domain"),
        duration: form.get("duration"),
        capacity: Number(form.get("capacity")),
        deadline: form.get("deadline") || null,
        required_skills: splitTags(form.get("skills")),
      }));
      go(`opportunities/${id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (user?.role !== "Faculty") {
    return <div className="content-wrap"><PageState kind="denied" message="Faculty access is required to edit an opportunity." /></div>;
  }
  if (state !== "ready") {
    return (
      <div className="content-wrap">
        <PageHeading eyebrow="THE FACULTY LEDGER" title="Revise the Research Dossier" text="Update requirements while preserving existing application integrity." />
        <PageState
          kind={state}
          message={error}
          onRetry={() => {
            setState("loading");
            api(`/opportunities/${id}`)
              .then((data) => { setItem(data); setState("ready"); })
              .catch((err) => { setError(err.message); setState("error"); });
          }}
        />
      </div>
    );
  }

  return (
    <div className="content-wrap narrow-content">
      <a href={`#/opportunities/${id}`} className="back-link" data-testid="edit-back">
        ← Opportunity details
      </a>
      <PageHeading
        eyebrow="THE FACULTY LEDGER"
        title="Revise the Research Dossier"
        text="Changes are recorded as a new requirements revision."
      />

      <form className="surface-card stack-form" onSubmit={submit}>
        <FormField
          label="Opportunity Title"
          id="edit-title"
          name="title"
          required
          maxLength="200"
          defaultValue={item.title}
          data-testid="edit-title"
        />
        <FormField
          label="Project Description"
          id="edit-description"
          name="description"
          as="textarea"
          rows="7"
          required
          maxLength="20000"
          defaultValue={item.description}
          data-testid="edit-description"
        />
        <div className="form-row">
          <FormField
            label="Research Domain"
            id="edit-domain"
            name="domain"
            required
            maxLength="120"
            defaultValue={item.domain}
            data-testid="edit-domain"
          />
          <FormField
            label="Expected Duration"
            id="edit-duration"
            name="duration"
            maxLength="120"
            defaultValue={item.duration}
            data-testid="edit-duration"
          />
        </div>
        <div className="form-row">
          <FormField
            label="Student Capacity"
            id="edit-capacity"
            name="capacity"
            type="number"
            min="1"
            max="10000"
            required
            defaultValue={item.capacity}
            data-testid="edit-capacity"
          />
          <FormField
            label="Application Deadline"
            id="edit-deadline"
            name="deadline"
            type="date"
            defaultValue={item.deadline || ""}
            data-testid="edit-deadline"
          />
        </div>
        <FormField
          label="Required Skills (comma-separated)"
          id="edit-skills"
          name="skills"
          defaultValue={item.required_skills?.join(", ") || ""}
          data-testid="edit-skills"
        />

        {error && <p className="form-message form-error" role="alert" data-testid="edit-error">{error}</p>}

        <Button type="submit" disabled={busy} data-testid="edit-submit">
          {busy ? "Saving…" : "Save changes"} <span aria-hidden="true">→</span>
        </Button>
      </form>
    </div>
  );
}

function ApplicantReview({ id, user }) {
  const [items, setItems] = useState([]);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function load() {
    setState("loading");
    setError("");
    try {
      const data = await api(`/opportunities/${id}/applications`);
      setItems(data);
      setState(data.length ? "ready" : "empty");
    } catch (err) {
      setError(err.message);
      setState(err.status === 403 ? "denied" : "error");
    }
  }

  useEffect(() => {
    if (user?.role === "Faculty") load();
  }, [id, user?.role]);

  async function decide(applicationId, status, comment) {
    setBusyId(applicationId);
    setError("");
    try {
      const updated = await api(`/applications/${applicationId}/decide`, json("POST", {
        status,
        faculty_comment: comment || "",
      }));
      setItems((old) => old.map((item) => (item.id === applicationId ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (user?.role !== "Faculty") {
    return <div className="content-wrap"><PageState kind="denied" message="Only faculty members can review applicants." /></div>;
  }

  return (
    <div className="content-wrap">
      <a href={`#/opportunities/${id}`} className="back-link" data-testid="review-back">
        ← Opportunity details
      </a>
      <PageHeading
        eyebrow="THE FACULTY REVIEW DESK"
        title="Applicant Review"
        text="Review each applicant's dossier and record a decision."
      />

      {error && <p className="form-message form-error" role="alert">{error}</p>}
      {state === "loading" && <PageState kind="loading" title="Gathering applicant dossiers" />}
      {state === "empty" && (
        <PageState
          kind="empty"
          title="No applications submitted yet"
          message="Applications will appear here when student scholars apply."
        />
      )}
      {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}

      {state === "ready" && (
        <div className="application-list">
          {items.map((item) => (
            <ApplicationCard
              key={item.id}
              item={item}
              busy={busyId === item.id}
              onDecision={decide}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ApplicationCard({ item, busy, onDecision }) {
  const [comment, setComment] = useState(item.faculty_comment || "");

  return (
    <article className="application-card">
      <div className="application-header">
        <div>
          <span className="eyebrow">APPLICATION RB-A{String(item.id).padStart(4, "0")}</span>
          <h2>Student Researcher</h2>
        </div>
        <StatusBadge status={item.status} />
      </div>

      <div className="application-copy">
        <strong>Applicant Motivation</strong>
        <p>{item.motivation}</p>
      </div>

      {item.profile_snapshot && (
        <div className="snapshot-grid">
          <div>
            <strong>Research Experience</strong>
            <p>{item.profile_snapshot.research_experience || "Not provided"}</p>
          </div>
          <div>
            <strong>Skills</strong>
            <p>{item.profile_snapshot.skills?.join(", ") || "Not provided"}</p>
          </div>
          <div>
            <strong>Interests</strong>
            <p>{item.profile_snapshot.interests?.join(", ") || "Not provided"}</p>
          </div>
        </div>
      )}

      <FormField
        label="Private Faculty Note"
        id={`comment-${item.id}`}
        as="textarea"
        rows="2"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        maxLength="5000"
        placeholder="Optional comment or guidance for the student"
        data-testid={`application-comment-${item.id}`}
      />

      {!["Accepted", "Rejected", "Withdrawn"].includes(item.status) && (
        <div className="application-actions">
          {item.status === "Submitted" && (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => onDecision(item.id, "Shortlisted", comment)}
              data-testid={`application-shortlist-${item.id}`}
            >
              Shortlist
            </Button>
          )}
          <Button
            disabled={busy}
            onClick={() => onDecision(item.id, "Accepted", comment)}
            data-testid={`application-accept-${item.id}`}
          >
            Accept
          </Button>
          <Button
            variant="quiet"
            disabled={busy}
            onClick={() => onDecision(item.id, "Rejected", comment)}
            data-testid={`application-reject-${item.id}`}
          >
            Decline
          </Button>
        </div>
      )}

      <div className="application-date">
        Submitted {new Date(item.submitted_at).toLocaleDateString()}
      </div>
    </article>
  );
}

function StatusBadge({ status }) {
  const isGood = status === "Accepted" || status === "Published" || status === "Active";
  const isMuted = status === "Rejected" || status === "Closed" || status === "Withdrawn" || status === "Archived" || status === "Disabled";
  const isAccent = status === "Shortlisted";
  const kind = isGood ? "good" : isMuted ? "muted" : isAccent ? "accent" : "warm";
  return <span className={`status-pill status-${kind}`}>{status}</span>;
}

function AdminUsers({ user }) {
  const [items, setItems] = useState([]);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  async function load() {
    setState("loading");
    setError("");
    try {
      const data = await api("/admin/users?offset=0&limit=100");
      setItems(data);
      setState(data.length ? "ready" : "empty");
    } catch (err) {
      setError(err.message);
      setState(err.status === 403 ? "denied" : "error");
    }
  }

  useEffect(() => {
    if (user?.role === "Administrator") load();
  }, [user?.role]);

  async function update(id, patch) {
    setBusy(id);
    setError("");
    try {
      const updated = await api(`/admin/users/${id}`, json("PATCH", patch));
      setItems((old) => old.map((item) => (item.id === id ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  if (user?.role !== "Administrator") {
    return (
      <div className="content-wrap">
        <PageState kind="denied" message="Administrator access is required to manage platform accounts." />
      </div>
    );
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="ADMINISTRATION"
        title="The Academy Registry"
        text="Maintain the integrity and membership of the research community."
      />

      {error && <p className="form-message form-error" role="alert">{error}</p>}
      {state === "loading" && <PageState kind="loading" title="Consulting the Academy Registry" />}
      {state === "empty" && <PageState kind="empty" title="No accounts registered" />}
      {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}

      {state === "ready" && (
        <div className="table-card">
          <div className="table-caption">
            <strong>Registered Scholars & Faculty</strong>
            <span>{items.length} accounts on record</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Identity</th>
                  <th>Institutional Email</th>
                  <th>Academy Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.name}</strong>
                      <small>Scholar #{item.id}</small>
                    </td>
                    <td>{item.email}</td>
                    <td>
                      <select
                        aria-label={`Role for ${item.name}`}
                        value={item.role}
                        disabled={busy === item.id}
                        onChange={(e) => update(item.id, { role: e.target.value })}
                        data-testid={`admin-role-${item.id}`}
                      >
                        {["Student", "Faculty", "Coordinator", "Administrator"].map((role) => (
                          <option key={role}>{role}</option>
                        ))}
                      </select>
                    </td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <Button
                        variant="quiet"
                        disabled={busy === item.id}
                        onClick={() => update(item.id, { status: item.status === "Active" ? "Disabled" : "Active" })}
                        data-testid={`admin-status-${item.id}`}
                      >
                        {item.status === "Active" ? "Disable" : "Activate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
