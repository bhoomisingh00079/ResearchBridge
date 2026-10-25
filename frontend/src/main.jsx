import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, json } from "./api.js";
import "./styles.css";

function currentRoute() {
  const parts = window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
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
  return <label className="field" htmlFor={id}>
    <span>{label}</span>
    {as === "textarea" ? <textarea id={id} {...controlProps} /> :
      as === "select" ? <select id={id} {...controlProps}>{children}</select> :
        <input id={id} {...controlProps} />}
  </label>;
}

function PageState({ kind = "loading", title, message, onRetry }) {
  const labels = {
    loading: ["Loading", "Gathering your research workspace…"],
    empty: ["Nothing here yet", "When there is something to show, it will appear here."],
    error: ["We couldn’t load this", "Please try again in a moment."],
    denied: ["Access restricted", "Your account does not have permission to view this content."],
  };
  const [defaultTitle, defaultMessage] = labels[kind] || labels.error;
  return <section className={`state-card state-${kind}`} role={kind === "error" ? "alert" : "status"}>
    <span className="state-mark" aria-hidden="true">{kind === "loading" ? "◌" : kind === "empty" ? "✦" : kind === "denied" ? "⌑" : "!"}</span>
    <h2>{title || defaultTitle}</h2>
    <p>{message || defaultMessage}</p>
    {onRetry && <Button variant="quiet" onClick={onRetry} data-testid="state-retry">Try again</Button>}
  </section>;
}

function App() {
  const [route, setRoute] = useState(currentRoute);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(Boolean(sessionStorage.getItem("rb-token")));

  useEffect(() => {
    const change = () => setRoute(currentRoute());
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);

  useEffect(() => {
    let live = true;
    if (!sessionStorage.getItem("rb-token")) { setAuthLoading(false); return () => { live = false; }; }
    api("/me").then((data) => { if (live) setUser(data); })
      .catch(() => { sessionStorage.removeItem("rb-token"); if (live) setUser(null); })
      .finally(() => { if (live) setAuthLoading(false); });
    return () => { live = false; };
  }, []);

  async function signedIn(token) {
    sessionStorage.setItem("rb-token", token);
    const data = await api("/me");
    setUser(data);
    go("opportunities");
  }

  function signOut() {
    sessionStorage.removeItem("rb-token");
    setUser(null);
    go("home");
  }

  const page = useMemo(() => {
    if (authLoading) return <PageState kind="loading" title="Opening your account" />;
    if (route.page === "home") return <Home user={user} />;
    if (route.page === "login" || route.page === "register") return <AuthPage mode={route.page} onSignedIn={signedIn} />;
    if (route.page === "verify") return <VerifyPage token={route.token} />;
    if (route.page === "opportunities") return <OpportunityList user={user} />;
    if (route.page === "my-opportunities") return <MyOpportunities user={user} />;
    if (route.page === "my-applications") return <MyApplications user={user} />;
    if (route.page === "opportunity") return <OpportunityDetail id={route.id} user={user} />;
    if (route.page === "edit") return <EditOpportunity id={route.id} user={user} />;
    if (route.page === "profile") return <ProfilePage user={user} />;
    if (route.page === "create") return <CreateOpportunity user={user} />;
    if (route.page === "review") return <ApplicantReview id={route.id} user={user} />;
    if (route.page === "admin") return <AdminUsers user={user} />;
    return <PageState kind="empty" title="Page not found" message="Use the navigation to find a ResearchBridge workspace." />;
  }, [authLoading, route, user]);

  return <div className="app-shell">
    <a href="#main" className="skip-link">Skip to content</a>
    <aside className="sidebar">
      <a className="brand" href="#/" aria-label="ResearchBridge home">
        <span className="brand-mark" aria-hidden="true">R</span><span>Research<span className="brand-light">Bridge</span><small>Curiosity, connected.</small></span>
      </a>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation" className="side-nav">
        <a href="#/opportunities" data-testid="nav-opportunities"><span aria-hidden="true">⌕</span> Explore research</a>
        {user?.role === "Faculty" && <a href="#/create" data-testid="nav-create"><span aria-hidden="true">＋</span> New opportunity</a>}
        {user?.role === "Faculty" && <a href="#/my-opportunities" data-testid="nav-my-opportunities"><span aria-hidden="true">▤</span> My opportunities</a>}
        {user?.role === "Student" && <a href="#/my-applications" data-testid="nav-my-applications"><span aria-hidden="true">◷</span> My applications</a>}
        {user && <a href="#/profile" data-testid="nav-profile"><span aria-hidden="true">◉</span> My profile</a>}
        {user?.role === "Administrator" && <a href="#/admin" data-testid="nav-admin"><span aria-hidden="true">▤</span> User administration</a>}
      </nav>
      <div className="sidebar-note"><span className="note-orbit" aria-hidden="true">✳</span><strong>Good research grows together.</strong><p>Find a question worth asking, then find your people.</p></div>
      <div className="sidebar-bottom">
        <span className="status-dot" /> <span>ResearchBridge platform</span>
      </div>
    </aside>
    <div className="main-column">
      <header className="topbar">
        <div className="mobile-brand"><span className="brand-mark">R</span> ResearchBridge</div>
        <div className="breadcrumb">Research workspace <span>/</span> {route.page === "home" ? "Welcome" : route.page.replaceAll("-", " ")}</div>
        <div className="top-actions">
          {user ? <><span className="user-chip"><span className="avatar">{user.name?.slice(0, 1).toUpperCase()}</span><span>{user.name}<small>{user.role}</small></span></span>
            <Button variant="quiet" onClick={signOut} data-testid="nav-signout">Sign out</Button></> :
            <><a className="top-login" href="#/login" data-testid="nav-login">Sign in</a><Button onClick={() => go("register")} data-testid="nav-register">Join ResearchBridge</Button></>}
        </div>
      </header>
      <main id="main" className="page-content" tabIndex="-1">{page}</main>
      <footer className="footer"><span>ResearchBridge</span><span>Built for careful questions and shared discovery.</span></footer>
    </div>
  </div>;
}

function Home({ user }) {
  return <div className="landing">
    <section className="hero-panel">
      <div className="hero-copy">
        <div className="eyebrow"><span className="eyebrow-line" /> STUDENT RESEARCH, CONNECTED</div>
        <h1>Big questions need <em>good company.</em></h1>
        <p>Find faculty-led research, bring your skills to a new question, and build something meaningful with your campus community.</p>
        <div className="hero-actions">
          <Button onClick={() => go("opportunities")} data-testid="home-explore">Explore opportunities <span aria-hidden="true">→</span></Button>
          {!user && <a href="#/register" className="text-action" data-testid="home-join">Create your account <span aria-hidden="true">↗</span></a>}
        </div>
        <div className="hero-proof"><span className="proof-stars" aria-hidden="true">✳ ✳ ✳</span><span>For students and faculty who want to move research forward.</span></div>
      </div>
      <ResearchMap />
    </section>
    <section className="landing-section">
      <div><div className="eyebrow">A PLACE TO BEGIN</div><h2>From a first idea to a shared result.</h2></div>
      <div className="feature-grid">
        <Feature number="01" title="Find your question" text="Browse open projects by research area, skill, and timeline." icon="⌕" />
        <Feature number="02" title="Meet your team" text="Apply with your interests and experience, then connect with a faculty mentor." icon="◉" />
        <Feature number="03" title="Make progress" text="Keep your work visible and move each milestone forward together." icon="↗" />
      </div>
    </section>
  </div>;
}

function ResearchMap() {
  return <div className="research-map" role="img" aria-label="Illustration of a small research campus">
    <div className="map-label"><span className="map-pulse" /> CAMPUS OF IDEAS</div>
    <div className="map-sun" />
    <div className="map-ground ground-back" />
    <div className="map-ground ground-front" />
    <div className="campus-path path-one" /><div className="campus-path path-two" />
    <div className="building building-main"><div className="roof" /><div className="building-front"><span className="windows">▥ ▥ ▥<br />▥ ▥ ▥</span><span className="door" /></div></div>
    <div className="building building-lab"><div className="roof" /><div className="building-front"><span className="windows">▥ ▥<br />▥ ▥</span></div></div>
    <div className="building building-library"><div className="roof" /><div className="building-front"><span className="windows">▥ ▥ ▥<br />▥ ▥ ▥</span></div></div>
    <div className="tree tree-a"><i /><b /></div><div className="tree tree-b"><i /><b /></div><div className="tree tree-c"><i /><b /></div>
    <div className="map-pin pin-one"><span>01</span><small>Ideas</small></div><div className="map-pin pin-two"><span>02</span><small>People</small></div>
    <div className="floating-note"><span className="note-icon">✳</span><span>New perspectives<br /><b>make better research.</b></span></div>
    <div className="map-caption">A campus where curiosity finds its people.</div>
  </div>;
}

function Feature({ number, title, text, icon }) {
  return <article className="feature-card"><div className="feature-top"><span>{number}</span><span className="feature-icon" aria-hidden="true">{icon}</span></div><h3>{title}</h3><p>{text}</p><span className="feature-rule" /></article>;
}

function AuthPage({ mode, onSignedIn }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [verificationToken, setVerificationToken] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(event) {
    event.preventDefault(); setError(""); setNotice(""); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      if (mode === "register") {
        const data = await api("/auth/register", json("POST", {
          name: form.get("name"), email: form.get("email"), password: form.get("password"), role: form.get("role"),
        }));
        if (data.dev_verify_token) setVerificationToken(data.dev_verify_token);
        else setNotice("Account created. Check your institutional inbox to verify your email before signing in.");
      } else {
        const data = await api("/auth/login", json("POST", { email: form.get("email"), password: form.get("password") }));
        await onSignedIn(data.token);
      }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function verifyLocal() {
    setBusy(true); setError("");
    try {
      await api(`/auth/verify/${encodeURIComponent(verificationToken)}`, { method: "POST" });
      setVerificationToken(""); setNotice("Your account is verified. You can sign in now."); go("login");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <div className="auth-layout">
    <aside className="auth-aside"><span className="auth-kicker">RESEARCH STARTS HERE</span><h1>Make room for a new question.</h1><p>ResearchBridge brings students and faculty together around projects that matter.</p><div className="auth-aside-illustration"><span>✳</span><i /><b /><small>Curiosity has a place here.</small></div></aside>
    <section className="auth-card">
      <span className="eyebrow">{mode === "register" ? "JOIN THE COMMUNITY" : "WELCOME BACK"}</span>
      <h2>{mode === "register" ? "Create your account" : "Sign in to continue"}</h2>
      <p className="auth-subtitle">{mode === "register" ? "Use your institutional email to get started." : "Pick up where your research left off."}</p>
      <div className="auth-tabs"><a className={mode === "login" ? "selected" : ""} href="#/login" data-testid="auth-tab-login">Sign in</a><a className={mode === "register" ? "selected" : ""} href="#/register" data-testid="auth-tab-register">Create account</a></div>
      {verificationToken ? <div className="notice-box"><strong>One more step</strong><p>Development mode returned a local verification token.</p><Button onClick={verifyLocal} disabled={busy} data-testid="register-verify">Verify account</Button></div> :
        <form onSubmit={submit} className="stack-form" noValidate>
          {mode === "register" && <>
            <FormField label="Full name" id="auth-name" name="name" type="text" autoComplete="name" required minLength="1" maxLength="160" data-testid="auth-name" />
            <FormField label="I am joining as" id="auth-role" name="role" as="select" data-testid="auth-role"><option value="Student">Student researcher</option><option value="Faculty">Faculty mentor</option></FormField>
          </>}
          <FormField label="Institutional email" id="auth-email" name="email" type="email" autoComplete="email" required data-testid="auth-email" />
          <FormField label="Password" id="auth-password" name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={mode === "register" ? 8 : undefined} data-testid="auth-password" />
          {error && <p className="form-message form-error" role="alert" data-testid="auth-error">{error}</p>}
          {notice && <p className="form-message form-success" role="status">{notice}</p>}
          <Button type="submit" disabled={busy} data-testid={mode === "register" ? "auth-register-submit" : "auth-login-submit"}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}<span aria-hidden="true">→</span></Button>
          <p className="form-footnote">By continuing, you agree to use ResearchBridge for respectful academic collaboration.</p>
        </form>}
      {notice && !verificationToken && <p className="form-message form-success" role="status">{notice}</p>}
      <a href="#/opportunities" className="back-link" data-testid="auth-back-explore">← Explore public opportunities</a>
    </section>
  </div>;
}

function VerifyPage({ token }) {
  const [state, setState] = useState("ready");
  const [message, setMessage] = useState("Use the button below to verify your institutional account.");
  async function verify() {
    setState("loading");
    try { await api(`/auth/verify/${encodeURIComponent(token)}`, { method: "POST" }); setMessage("Your account is verified. You can sign in now."); setState("success"); }
    catch (error) { setMessage(error.message); setState("error"); }
  }
  return <div className="auth-layout"><aside className="auth-aside"><span className="auth-kicker">ACCOUNT VERIFICATION</span><h1>One small step to begin.</h1><p>We verify institutional accounts to keep the research community connected.</p></aside>
    <section className="auth-card"><span className="eyebrow">RESEARCHBRIDGE ACCOUNT</span><h2>Verify your email</h2><p className="auth-subtitle">{message}</p>
      {state === "ready" && <Button onClick={verify} data-testid="verify-submit">Verify account <span aria-hidden="true">→</span></Button>}
      {state === "loading" && <PageState kind="loading" title="Verifying your account" />}
      {state === "error" && <p className="form-message form-error" role="alert">{message}</p>}
      {state === "error" && <Button variant="secondary" onClick={verify} data-testid="verify-retry">Try again</Button>}
      {state === "success" && <p className="form-message form-success" role="status">{message}</p>}
      {state === "success" && <Button onClick={() => go("login")} data-testid="verify-login">Continue to sign in</Button>}
    </section>
  </div>;
}

function OpportunityList({ user }) {
  const [filters, setFilters] = useState({ q: "", domain: "", skill: "", duration: "", available: false });
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");

  async function load(next = filters) {
    setState("loading"); setError("");
    const query = new URLSearchParams();
    for (const key of ["q", "domain", "skill", "duration"]) if (next[key].trim()) query.set(key, next[key].trim());
    if (next.available) query.set("available", "true");
    try { const result = await api(`/opportunities?${query}`); setData(result.items || []); setState(result.items?.length ? "ready" : "empty"); }
    catch (err) { setError(err.message); setState(err.status === 403 ? "denied" : "error"); }
  }
  useEffect(() => { load(); }, []);

  function update(key, value) { setFilters((previous) => ({ ...previous, [key]: value })); }

  return <div className="content-wrap">
    <PageHeading eyebrow="OPPORTUNITY EXCHANGE" title="Find a question worth asking." text="Explore faculty-led work, filter by your interests, and find a team to learn with." />
    <form className="filter-panel" onSubmit={(event) => { event.preventDefault(); load(); }}>
      <FormField label="Search projects" id="search-q" name="q" value={filters.q} onChange={(e) => update("q", e.target.value)} placeholder="Title or research topic" data-testid="opportunities-search" />
      <FormField label="Research area" id="search-domain" name="domain" value={filters.domain} onChange={(e) => update("domain", e.target.value)} placeholder="e.g. AI, public health" data-testid="opportunities-domain" />
      <FormField label="Skill" id="search-skill" name="skill" value={filters.skill} onChange={(e) => update("skill", e.target.value)} placeholder="e.g. Python" data-testid="opportunities-skill" />
      <div className="filter-bottom"><FormField label="Duration" id="search-duration" name="duration" value={filters.duration} onChange={(e) => update("duration", e.target.value)} placeholder="e.g. 10 weeks" data-testid="opportunities-duration" />
        <label className="check-field"><input type="checkbox" checked={filters.available} onChange={(e) => update("available", e.target.checked)} data-testid="opportunities-available" /> Has open places</label>
        <Button type="submit" data-testid="opportunities-filter-submit">Update results <span aria-hidden="true">→</span></Button></div>
    </form>
    {state === "loading" && <PageState kind="loading" title="Finding open research" />}
    {state === "empty" && <PageState kind="empty" title="No opportunities match yet" message="Try a broader research area or clear a filter." />}
    {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={() => load()} />}
    {state === "ready" && <div className="result-heading"><strong>{data.length} {data.length === 1 ? "opportunity" : "opportunities"}</strong><span>Open research projects</span></div>}
    {state === "ready" && <div className="opportunity-grid">{data.map((item) => <OpportunityCard key={item.id} item={item} />)}</div>}
    {!user && <div className="inline-callout"><div><strong>Have a skill to share?</strong><span>Create a student account to apply and join a team.</span></div><a href="#/register" data-testid="opportunities-join">Join ResearchBridge ↗</a></div>}
  </div>;
}

function PageHeading({ eyebrow, title, text, action }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p></div>{action}</div>;
}

function OpportunityCard({ item }) {
  return <article className="opportunity-card">
    <div className="card-topline"><span className="status-pill status-open">Open opportunity</span><span className="card-id">RB-{String(item.id).padStart(4, "0")}</span></div>
    <h2><a href={`#/opportunities/${item.id}`} data-testid={`opportunity-title-${item.id}`}>{item.title}</a></h2>
    <p className="card-description">{item.description}</p>
    <div className="opportunity-meta"><span><b>Research area</b>{item.domain}</span><span><b>Duration</b>{item.duration || "Flexible"}</span><span><b>Places</b>{item.available_places} of {item.capacity}</span></div>
    <div className="skill-list">{(item.required_skills || []).slice(0, 4).map((skill) => <span className="skill-chip" key={skill}>{skill}</span>)}</div>
    <a className="card-link" href={`#/opportunities/${item.id}`} data-testid={`opportunity-open-${item.id}`}>View opportunity <span aria-hidden="true">→</span></a>
  </article>;
}

function MyOpportunities({ user }) {
  const [items, setItems] = useState([]); const [state, setState] = useState("loading"); const [error, setError] = useState("");
  async function load() {
    setState("loading"); setError("");
    try { const result = await api("/opportunities/mine?offset=0&limit=100"); setItems(result.items || []); setState(result.items?.length ? "ready" : "empty"); }
    catch (err) { setError(err.message); setState(err.status === 403 ? "denied" : "error"); }
  }
  useEffect(() => { if (user?.role === "Faculty") load(); }, [user?.role]);
  if (user?.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="Faculty access is required to manage opportunities." /></div>;
  return <div className="content-wrap"><PageHeading eyebrow="FACULTY WORKSPACE" title="Your research opportunities." text="Keep drafts moving, review applicants, and update project details." action={<Button onClick={() => go("create")} data-testid="my-opportunities-create">New opportunity</Button>} />
    {state === "loading" && <PageState kind="loading" title="Loading your opportunities" />}
    {state === "empty" && <PageState kind="empty" title="No opportunities yet" message="Create a draft to invite students into your research." />}
    {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}
    {state === "ready" && <div className="opportunity-grid">{items.map((item) => <article className="opportunity-card" key={item.id}>
      <div className="card-topline"><StatusBadge status={item.status} /><span className="card-id">RB-{String(item.id).padStart(4, "0")}</span></div>
      <h2><a href={`#/opportunities/${item.id}`} data-testid={`managed-title-${item.id}`}>{item.title}</a></h2>
      <p className="card-description">{item.description}</p>
      <div className="opportunity-meta"><span><b>Research area</b>{item.domain}</span><span><b>Duration</b>{item.duration || "Flexible"}</span><span><b>Places</b>{item.available_places} of {item.capacity}</span></div>
      <div className="managed-actions"><a className="card-link" href={`#/opportunities/${item.id}`} data-testid={`managed-open-${item.id}`}>Manage details <span aria-hidden="true">→</span></a><a className="card-link" href={`#/review/${item.id}`} data-testid={`managed-review-${item.id}`}>Review applicants <span aria-hidden="true">→</span></a></div>
    </article>)}</div>}
  </div>;
}

function MyApplications({ user }) {
  const [items, setItems] = useState([]); const [state, setState] = useState("loading"); const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);
  async function load() {
    setState("loading"); setError("");
    try { const result = await api("/applications/mine"); setItems(result); setState(result.length ? "ready" : "empty"); }
    catch (err) { setError(err.message); setState(err.status === 403 ? "denied" : "error"); }
  }
  useEffect(() => { if (user?.role === "Student") load(); }, [user?.role]);
  async function withdraw(applicationId) {
    setBusy(applicationId); setError("");
    try { const updated = await api(`/applications/${applicationId}/withdraw`, { method: "POST" });
      setItems((old) => old.map((item) => item.id === applicationId ? { ...item, ...updated } : item)); }
    catch (err) { setError(err.message); }
    finally { setBusy(null); }
  }
  if (user?.role !== "Student") return <div className="content-wrap"><PageState kind="denied" message="Sign in with a student account to view your applications." /></div>;
  return <div className="content-wrap"><PageHeading eyebrow="STUDENT WORKSPACE" title="Your research applications." text="Follow the status of each application and return to the research that caught your attention." />
    {state === "loading" && <PageState kind="loading" title="Loading your applications" />}
    {state === "empty" && <PageState kind="empty" title="No applications yet" message="Explore open projects to find a research team." />}
    {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}
      {state === "ready" && error && <p className="form-message form-error" role="alert">{error}</p>}
    {state === "ready" && <div className="application-list">{items.map((item) => <article className="application-card" key={item.id}>
      <div className="application-header"><div><span className="eyebrow">APPLICATION RB-A{String(item.id).padStart(4, "0")}</span><h2><a href={`#/opportunities/${item.opportunity_id}`} data-testid={`my-application-title-${item.id}`}>{item.opportunity_title}</a></h2></div><StatusBadge status={item.status} /></div>
      <p className="application-domain">{item.domain} · Submitted {new Date(item.submitted_at).toLocaleDateString()}</p>
      <div className="application-copy"><strong>Your motivation</strong><p>{item.motivation}</p></div>
      {item.faculty_comment && <div className="application-copy"><strong>Faculty comment</strong><p>{item.faculty_comment}</p></div>}
      {["Submitted", "Shortlisted"].includes(item.status) && <Button variant="quiet" disabled={busy === item.id} onClick={() => withdraw(item.id)} data-testid={`my-application-withdraw-${item.id}`}>{busy === item.id ? "Withdrawing…" : "Withdraw application"}</Button>}
    </article>)}</div>}
  </div>;
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
    api(`/opportunities/${id}`).then((data) => { if (live) { setItem(data); setState("ready"); } })
      .catch((err) => { if (live) { setError(err.message); setState(err.status === 403 ? "denied" : err.status === 404 ? "empty" : "error"); } });
    if (user?.role === "Student") api("/applications/mine").then((rows) => {
      if (live) setCurrentApplication(rows.find((row) => String(row.opportunity_id) === String(id) && row.status !== "Withdrawn") || null);
    }).catch(() => {});
    return () => { live = false; };
  }, [id, user?.role]);

  async function apply(event) {
    event.preventDefault(); setMessage(""); setError(""); setBusy(true);
    try {
      const submitted = await api(`/opportunities/${id}/apply`, json("POST", { motivation: new FormData(event.currentTarget).get("motivation") }));
      setCurrentApplication(submitted);
      setMessage("Your application was submitted. You can follow its status in your account.");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function changeState(action) {
    setBusy(true); setError("");
    const label = { publish: "published", close: "closed", archive: "archived" }[action];
    try { const updated = await api(`/opportunities/${id}/state/${action}`, { method: "POST" }); setItem(updated); setMessage(`Opportunity ${label}.`); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  if (state !== "ready") return <div className="content-wrap"><PageHeading eyebrow="OPPORTUNITY" title="Research opportunity" text="Review the project details and next steps." />
    <PageState kind={state} message={error} onRetry={() => { setState("loading"); api(`/opportunities/${id}`).then((data) => { setItem(data); setState("ready"); }).catch((err) => { setError(err.message); setState("error"); }); }} /></div>;

  return <div className="content-wrap detail-page">
    <a href="#/opportunities" className="back-link" data-testid="opportunity-back">← Back to opportunities</a>
    <div className="detail-layout"><article className="detail-main">
      <StatusBadge status={item.status} /><span className="detail-code">RB-{String(item.id).padStart(4, "0")}</span>
      <h1>{item.title}</h1><p className="detail-intro">{item.description}</p>
      <div className="detail-section"><h2>Research area</h2><p>{item.domain}</p></div>
      <div className="detail-section"><h2>What you’ll bring</h2><div className="skill-list">{item.required_skills?.length ? item.required_skills.map((skill) => <span className="skill-chip" key={skill}>{skill}</span>) : <span className="muted">Discuss relevant skills with the faculty mentor.</span>}</div></div>
      <div className="detail-section"><h2>Project description</h2><p>{item.description}</p></div>
      {message && <p className="form-message form-success" role="status">{message}</p>}
      {error && <p className="form-message form-error" role="alert">{error}</p>}
      {currentApplication && <div className="apply-panel"><h2>Application status</h2><p>Your application is <strong>{currentApplication.status}</strong>. Track updates on your applications page.</p><a href="#/my-applications" data-testid="opportunity-my-applications">View my applications →</a></div>}
      {user?.role === "Student" && !currentApplication && item.status === "Published" && <form className="apply-panel" onSubmit={apply}>
        <h2>Tell the team what interests you</h2><FormField label="Your motivation" id="apply-motivation" name="motivation" as="textarea" rows="5" required maxLength="10000" placeholder="What draws you to this research question?" data-testid="apply-motivation" />
        <Button type="submit" disabled={busy} data-testid="apply-submit">{busy ? "Submitting…" : "Submit application"} <span aria-hidden="true">→</span></Button>
      </form>}
      {!user && <div className="apply-panel"><h2>Interested in joining?</h2><p>Sign in with your student account to apply for this project.</p><Button onClick={() => go("login")} data-testid="opportunity-login">Sign in to apply</Button></div>}
    </article><aside className="detail-aside">
      <div className="aside-card"><span className="eyebrow">AT A GLANCE</span><dl><div><dt>Research area</dt><dd>{item.domain}</dd></div><div><dt>Timeframe</dt><dd>{item.duration || "Flexible"}</dd></div><div><dt>Open places</dt><dd>{item.available_places} of {item.capacity}</dd></div><div><dt>Application deadline</dt><dd>{item.deadline || "To be discussed"}</dd></div></dl>
      {user?.role === "Faculty" && user.id === item.faculty_id && <div className="faculty-actions"><Button variant="secondary" onClick={() => go(`edit/${item.id}`)} data-testid="opportunity-edit">Edit details</Button><Button variant="secondary" onClick={() => go(`review/${item.id}`)} data-testid="opportunity-review-applicants">Review applicants</Button>
          {item.status === "Draft" && <Button onClick={() => changeState("publish")} disabled={busy} data-testid="opportunity-publish">Publish opportunity</Button>}
          {item.status === "Published" && <Button variant="secondary" onClick={() => changeState("close")} disabled={busy} data-testid="opportunity-close">Close opportunity</Button>}
          {item.status !== "Archived" && <Button variant="quiet" onClick={() => changeState("archive")} disabled={busy} data-testid="opportunity-archive">Archive</Button>}</div>}
      </div>
      <div className="mentor-note"><span className="note-orbit">✳</span><strong>Research is a conversation.</strong><p>Bring your curiosity, questions, and willingness to learn.</p></div>
    </aside></div>
  </div>;
}

function ProfilePage({ user }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [profile, setProfile] = useState(null); const [loadState, setLoadState] = useState("loading");
  const student = user?.role === "Student";
  useEffect(() => {
    if (!user || (!student && user.role !== "Faculty")) { setLoadState("denied"); return; }
    let live = true;
    api(`/profile/${student ? "student" : "faculty"}`).then((data) => { if (live) { setProfile(data); setLoadState("ready"); } })
      .catch((err) => { if (live) { setError(err.message); setLoadState(err.status === 403 ? "denied" : "error"); } });
    return () => { live = false; };
  }, [user, student]);
  if (!user) return <div className="content-wrap"><PageState kind="denied" message="Sign in to manage your profile." /></div>;
  if (!student && user.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="This role does not have a research profile form." /></div>;
  if (loadState !== "ready") return <div className="content-wrap"><PageHeading eyebrow="YOUR RESEARCH PROFILE" title="Share what you’re curious about." text="A clear profile helps research teams understand the skills and interests you bring." /><PageState kind={loadState} message={error} onRetry={() => { setLoadState("loading"); api(`/profile/${student ? "student" : "faculty"}`).then((data) => { setProfile(data); setLoadState("ready"); }).catch((err) => { setError(err.message); setLoadState("error"); }); }} /></div>;
  async function save(event) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    const form = new FormData(event.currentTarget);
    const payload = student ? { research_experience: form.get("experience"), skills: splitTags(form.get("skills")), interests: splitTags(form.get("interests")) }
      : { bio: form.get("bio"), expertise: splitTags(form.get("expertise")) };
    try { await api(`/profile/${student ? "student" : "faculty"}`, json("PUT", payload)); setNotice("Your profile has been saved."); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="content-wrap narrow-content"><PageHeading eyebrow="YOUR RESEARCH PROFILE" title="Share what you’re curious about." text="A clear profile helps research teams understand the skills and interests you bring." />
    <form className="surface-card stack-form" onSubmit={save}>
      <div className="profile-identity"><span className="avatar avatar-large">{user.name.slice(0, 1).toUpperCase()}</span><div><strong>{user.name}</strong><span>{user.email} · {user.role}</span></div></div>
      {student ? <><FormField label="Research experience" id="profile-experience" name="experience" as="textarea" rows="5" maxLength="10000" defaultValue={profile?.research_experience || ""} placeholder="Share projects, coursework, or questions you have explored." data-testid="profile-experience" />
        <FormField label="Skills (comma-separated)" id="profile-skills" name="skills" type="text" defaultValue={profile?.skills?.join(", ") || ""} placeholder="Python, statistics, interviewing" data-testid="profile-skills" />
        <FormField label="Research interests (comma-separated)" id="profile-interests" name="interests" type="text" defaultValue={profile?.interests?.join(", ") || ""} placeholder="Climate, public health, machine learning" data-testid="profile-interests" /></> : <>
        <FormField label="Faculty biography" id="profile-bio" name="bio" as="textarea" rows="6" maxLength="10000" defaultValue={profile?.bio || ""} placeholder="Your research areas, approach, and mentorship interests." data-testid="profile-bio" />
        <FormField label="Areas of expertise (comma-separated)" id="profile-expertise" name="expertise" type="text" defaultValue={profile?.expertise?.join(", ") || ""} placeholder="AI, data science, public policy" data-testid="profile-expertise" /></>}
      {error && <p className="form-message form-error" role="alert" data-testid="profile-error">{error}</p>}{notice && <p className="form-message form-success" role="status">{notice}</p>}
      <Button type="submit" disabled={busy} data-testid="profile-save">{busy ? "Saving…" : "Save profile"} <span aria-hidden="true">→</span></Button>
    </form>
  </div>;
}

function splitTags(value) { return String(value || "").split(",").map((item) => item.trim()).filter(Boolean); }

function CreateOpportunity({ user }) {
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  if (user?.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="Only faculty members can create an opportunity." /></div>;
  async function submit(event) {
    event.preventDefault(); setError(""); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const item = await api("/opportunities", json("POST", {
        title: form.get("title"), description: form.get("description"), domain: form.get("domain"), duration: form.get("duration"),
        capacity: Number(form.get("capacity")), deadline: form.get("deadline") || null, required_skills: splitTags(form.get("skills")),
      }));
      go(`opportunities/${item.id}`);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="content-wrap narrow-content"><PageHeading eyebrow="FACULTY WORKSPACE" title="Open a new research question." text="Describe the work clearly so students can decide whether it is right for them." />
    <form className="surface-card stack-form" onSubmit={submit}>
      <FormField label="Opportunity title" id="opp-title" name="title" required maxLength="200" placeholder="A clear, specific research question" data-testid="create-title" />
      <FormField label="Project description" id="opp-description" name="description" as="textarea" rows="7" required maxLength="20000" placeholder="What will the student explore or contribute?" data-testid="create-description" />
      <div className="form-row"><FormField label="Research area" id="opp-domain" name="domain" required maxLength="120" placeholder="e.g. AI and society" data-testid="create-domain" />
        <FormField label="Expected duration" id="opp-duration" name="duration" maxLength="120" placeholder="e.g. 10 weeks" data-testid="create-duration" /></div>
      <div className="form-row"><FormField label="Student capacity" id="opp-capacity" name="capacity" type="number" min="1" max="10000" required defaultValue="1" data-testid="create-capacity" />
        <FormField label="Application deadline" id="opp-deadline" name="deadline" type="date" data-testid="create-deadline" /></div>
      <FormField label="Required skills (comma-separated)" id="opp-skills" name="skills" placeholder="Python, statistics, literature review" data-testid="create-skills" />
      {error && <p className="form-message form-error" role="alert" data-testid="create-error">{error}</p>}
      <div className="form-actions"><Button type="submit" disabled={busy} data-testid="create-submit">{busy ? "Saving…" : "Save as draft"} <span aria-hidden="true">→</span></Button><span>New opportunities begin as drafts. You can publish from the detail page.</span></div>
    </form>
  </div>;
}

function EditOpportunity({ id, user }) {
  const [item, setItem] = useState(null); const [state, setState] = useState("loading"); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    api(`/opportunities/${id}`).then((data) => { if (live) { setItem(data); setState("ready"); } })
      .catch((err) => { if (live) { setError(err.message); setState(err.status === 403 ? "denied" : err.status === 404 ? "empty" : "error"); } });
    return () => { live = false; };
  }, [id]);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api(`/opportunities/${id}`, json("PUT", {
        title: form.get("title"), description: form.get("description"), domain: form.get("domain"),
        duration: form.get("duration"), capacity: Number(form.get("capacity")), deadline: form.get("deadline") || null,
        required_skills: splitTags(form.get("skills")),
      }));
      go(`opportunities/${id}`);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  if (user?.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="Faculty access is required to edit an opportunity." /></div>;
  if (state !== "ready") return <div className="content-wrap"><PageHeading eyebrow="FACULTY WORKSPACE" title="Edit opportunity details." text="Update the requirements while preserving the application-time version." /><PageState kind={state} message={error} onRetry={() => { setState("loading"); api(`/opportunities/${id}`).then((data) => { setItem(data); setState("ready"); }).catch((err) => { setError(err.message); setState("error"); }); }} /></div>;
  return <div className="content-wrap narrow-content"><a href={`#/opportunities/${id}`} className="back-link" data-testid="edit-back">← Opportunity details</a>
    <PageHeading eyebrow="FACULTY WORKSPACE" title="Edit opportunity details." text="Changes are recorded as a new requirements version." />
    <form className="surface-card stack-form" onSubmit={submit}>
      <FormField label="Opportunity title" id="edit-title" name="title" required maxLength="200" defaultValue={item.title} data-testid="edit-title" />
      <FormField label="Project description" id="edit-description" name="description" as="textarea" rows="7" required maxLength="20000" defaultValue={item.description} data-testid="edit-description" />
      <div className="form-row"><FormField label="Research area" id="edit-domain" name="domain" required maxLength="120" defaultValue={item.domain} data-testid="edit-domain" />
        <FormField label="Expected duration" id="edit-duration" name="duration" maxLength="120" defaultValue={item.duration} data-testid="edit-duration" /></div>
      <div className="form-row"><FormField label="Student capacity" id="edit-capacity" name="capacity" type="number" min="1" max="10000" required defaultValue={item.capacity} data-testid="edit-capacity" />
        <FormField label="Application deadline" id="edit-deadline" name="deadline" type="date" defaultValue={item.deadline || ""} data-testid="edit-deadline" /></div>
      <FormField label="Required skills (comma-separated)" id="edit-skills" name="skills" defaultValue={item.required_skills?.join(", ") || ""} data-testid="edit-skills" />
      {error && <p className="form-message form-error" role="alert" data-testid="edit-error">{error}</p>}
      <Button type="submit" disabled={busy} data-testid="edit-submit">{busy ? "Saving…" : "Save changes"} <span aria-hidden="true">→</span></Button>
    </form>
  </div>;
}

function ApplicantReview({ id, user }) {
  const [items, setItems] = useState([]); const [state, setState] = useState("loading"); const [error, setError] = useState(""); const [busyId, setBusyId] = useState(null);
  async function load() {
    setState("loading"); setError("");
    try { const data = await api(`/opportunities/${id}/applications`); setItems(data); setState(data.length ? "ready" : "empty"); }
    catch (err) { setError(err.message); setState(err.status === 403 ? "denied" : "error"); }
  }
  useEffect(() => { if (user?.role === "Faculty") load(); }, [id, user?.role]);
  async function decide(applicationId, status, comment) {
    setBusyId(applicationId); setError("");
    try { const updated = await api(`/applications/${applicationId}/decide`, json("POST", { status, faculty_comment: comment || "" }));
      setItems((old) => old.map((item) => item.id === applicationId ? { ...item, ...updated } : item)); }
    catch (err) { setError(err.message); }
    finally { setBusyId(null); }
  }
  if (user?.role !== "Faculty") return <div className="content-wrap"><PageState kind="denied" message="Only faculty members can review applicants." /></div>;
  return <div className="content-wrap"><a href={`#/opportunities/${id}`} className="back-link" data-testid="review-back">← Opportunity details</a>
    <PageHeading eyebrow="FACULTY WORKSPACE" title="Applicant review" text="Review each application and record a clear decision for the student." />
    {error && <p className="form-message form-error" role="alert">{error}</p>}
    {state === "loading" && <PageState kind="loading" title="Gathering applications" />}
    {state === "empty" && <PageState kind="empty" title="No applications yet" message="Applications will appear here when students apply." />}
    {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}
    {state === "ready" && <div className="application-list">{items.map((item) => <ApplicationCard key={item.id} item={item} busy={busyId === item.id} onDecision={decide} />)}</div>}
  </div>;
}

function ApplicationCard({ item, busy, onDecision }) {
  const [comment, setComment] = useState(item.faculty_comment || "");
  return <article className="application-card">
    <div className="application-header"><div><span className="eyebrow">APPLICATION RB-A{String(item.id).padStart(4, "0")}</span><h2>Student researcher</h2></div><StatusBadge status={item.status} /></div>
    <div className="application-copy"><strong>Motivation</strong><p>{item.motivation}</p></div>
    {item.profile_snapshot && <div className="snapshot-grid"><div><strong>Research experience</strong><p>{item.profile_snapshot.research_experience || "Not provided"}</p></div><div><strong>Skills</strong><p>{item.profile_snapshot.skills?.join(", ") || "Not provided"}</p></div><div><strong>Interests</strong><p>{item.profile_snapshot.interests?.join(", ") || "Not provided"}</p></div></div>}
    <FormField label="Private faculty comment" id={`comment-${item.id}`} as="textarea" rows="2" value={comment} onChange={(event) => setComment(event.target.value)} maxLength="5000" placeholder="Optional note for the student" data-testid={`application-comment-${item.id}`} />
    {!["Accepted", "Rejected", "Withdrawn"].includes(item.status) && <div className="application-actions">
      {item.status === "Submitted" && <Button variant="secondary" disabled={busy} onClick={() => onDecision(item.id, "Shortlisted", comment)} data-testid={`application-shortlist-${item.id}`}>Shortlist</Button>}
      <Button disabled={busy} onClick={() => onDecision(item.id, "Accepted", comment)} data-testid={`application-accept-${item.id}`}>Accept</Button>
      <Button variant="quiet" disabled={busy} onClick={() => onDecision(item.id, "Rejected", comment)} data-testid={`application-reject-${item.id}`}>Decline</Button>
    </div>}
    <div className="application-date">Submitted {new Date(item.submitted_at).toLocaleDateString()}</div>
  </article>;
}

function StatusBadge({ status }) {
  const kind = status === "Accepted" || status === "Published" ? "good" : status === "Rejected" || status === "Closed" ? "muted" : status === "Shortlisted" ? "accent" : "warm";
  return <span className={`status-pill status-${kind}`}>{status}</span>;
}

function AdminUsers({ user }) {
  const [items, setItems] = useState([]); const [state, setState] = useState("loading"); const [error, setError] = useState(""); const [busy, setBusy] = useState(null);
  async function load() {
    setState("loading"); setError("");
    try { const data = await api("/admin/users?offset=0&limit=100"); setItems(data); setState(data.length ? "ready" : "empty"); }
    catch (err) { setError(err.message); setState(err.status === 403 ? "denied" : "error"); }
  }
  useEffect(() => { if (user?.role === "Administrator") load(); }, [user?.role]);
  async function update(id, patch) {
    setBusy(id); setError("");
    try { const updated = await api(`/admin/users/${id}`, json("PATCH", patch)); setItems((old) => old.map((item) => item.id === id ? { ...item, ...updated } : item)); }
    catch (err) { setError(err.message); }
    finally { setBusy(null); }
  }
  if (user?.role !== "Administrator") return <div className="content-wrap"><PageState kind="denied" message="Administrator access is required to manage platform accounts." /></div>;
  return <div className="content-wrap"><PageHeading eyebrow="ADMINISTRATION" title="Manage the research community." text="Account role and status changes are enforced by the API and written to the audit log." />
    {error && <p className="form-message form-error" role="alert">{error}</p>}
    {state === "loading" && <PageState kind="loading" title="Loading accounts" />}
    {state === "empty" && <PageState kind="empty" title="No accounts found" />}
    {(state === "error" || state === "denied") && <PageState kind={state} message={error} onRetry={load} />}
    {state === "ready" && <div className="table-card"><div className="table-caption"><strong>Platform accounts</strong><span>{items.length} shown</span></div><div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}>
      <td><strong>{item.name}</strong><small>Account #{item.id}</small></td><td>{item.email}</td>
      <td><select aria-label={`Role for ${item.name}`} value={item.role} disabled={busy === item.id} onChange={(e) => update(item.id, { role: e.target.value })} data-testid={`admin-role-${item.id}`}>
        {['Student', 'Faculty', 'Coordinator', 'Administrator'].map((role) => <option key={role}>{role}</option>)}</select></td>
      <td><StatusBadge status={item.status} /></td><td><Button variant="quiet" disabled={busy === item.id} onClick={() => update(item.id, { status: item.status === "Active" ? "Disabled" : "Active" })} data-testid={`admin-status-${item.id}`}>{item.status === "Active" ? "Disable" : "Activate"}</Button></td>
    </tr>)}</tbody></table></div></div>}
  </div>;
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
