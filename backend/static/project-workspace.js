const root = document.querySelector("#workspace");
const urlParams = new URLSearchParams(location.search);
let token = urlParams.get("token") || sessionStorage.getItem("rb-token") || localStorage.getItem("rb-token");
if (token) {
  sessionStorage.setItem("rb-token", token);
  localStorage.setItem("rb-token", token);
}
if (urlParams.has("token")) {
  urlParams.delete("token");
  const newSearch = urlParams.toString();
  const newUrl = location.pathname + (newSearch ? `?${newSearch}` : "") + location.hash;
  history.replaceState(null, "", newUrl);
}

let projectId = urlParams.get("project") || (location.hash.includes("project=") ? new URLSearchParams(location.hash.split("?")[1] || "").get("project") : "") || root.dataset.projectId;
const apiBase = (localStorage.getItem("rb_api_base") || "https://researchbridge-r327.onrender.com").replace(/\/$/, "");
const notice = document.querySelector("#notice");
const activityPageSize = 20;
let activityPage = 1;
let activePanel = "milestones";

function setNotice(message, kind = "info") {
  notice.innerHTML = message;
  notice.dataset.kind = kind;
  notice.hidden = !message;
}

function authHeaders(extra = {}) {
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

async function api(path, options = {}) {
  if (!token) throw new Error("Sign in to view this project workspace.");
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: authHeaders(options.headers || {}) });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || (response.status === 403 ? "You do not have access to this project." : `Request failed (${response.status}).`);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

function showFailure(error, container) {
  container.replaceChildren();
  const box = document.createElement("div");
  box.className = "empty";
  box.textContent = error.message || "This information is temporarily unavailable.";
  container.append(box);
  setNotice(error.status === 403 ? "Access denied for this project." : error.message, "error");
}

function empty(container, message) {
  container.innerHTML = "";
  const box = document.createElement("div");
  box.className = "empty";
  box.textContent = message;
  container.append(box);
}

function card(className = "list-card") {
  const element = document.createElement("article");
  element.className = className;
  return element;
}

function badge(text, kind = "") {
  const element = document.createElement("span");
  element.className = `badge ${kind}`.trim();
  element.textContent = text;
  return element;
}

function formatDate(value) {
  if (!value) return "Date not set";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

function statusClass(status) {
  if (status === "Completed" || status === "Issued") return "badge-complete";
  if (status === "Blocked" || status === "Declined") return "badge-warning";
  return "";
}

async function loadMilestones() {
  const list = document.querySelector("#milestone-list");
  try {
    const rows = await api(`/projects/${encodeURIComponent(projectId)}/milestones`);
    if (!rows.length) return empty(list, "No milestones yet. Add the first one to plan your research progress.");
    list.replaceChildren();
    let completed = 0;
    for (const item of rows) {
      if (item.status === "Completed") completed += 1;
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3"); title.textContent = item.description;
      const due = document.createElement("p"); due.textContent = `Target date · ${formatDate(item.target_date)}`;
      copy.append(title, due);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(item.status, statusClass(item.status)));
      const overdue = item.status !== "Completed" && item.target_date < new Date().toISOString().slice(0, 10);
      if (overdue) meta.append(badge("Overdue", "badge-warning"));
      row.append(copy, meta); wrapper.append(row);
      if (item.status !== "Completed") {
        const actions = document.createElement("div"); actions.className = "row-actions";
        const next = item.status === "Not Started" ? "In Progress" : "Completed";
        const update = document.createElement("button"); update.className = "small-button"; update.type = "button";
        update.textContent = `Mark ${next.toLowerCase()}`;
        update.addEventListener("click", async () => {
          update.disabled = true;
          try { await api(`/milestones/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: next }) }); setNotice("Milestone updated.", "success"); await Promise.all([loadMilestones(), loadActivity()]); }
          catch (error) { setNotice(error.message, "error"); update.disabled = false; }
        });
        actions.append(update); wrapper.append(actions);
      }
      const tasks = document.createElement("div"); tasks.className = "task-list";
      try {
        const taskRows = await api(`/milestones/${item.id}/tasks`);
        for (const task of taskRows) {
          const taskRow = document.createElement("div"); taskRow.className = "task-row";
          const label = document.createElement("span"); label.textContent = task.description;
          const taskStatus = document.createElement("span"); taskStatus.textContent = task.status;
          taskRow.append(label, badge(taskStatus.textContent, statusClass(task.status)));
          tasks.append(taskRow);
        }
      } catch { /* Keep the milestone visible if an older API has no task-list route. */ }
      if (tasks.childElementCount) wrapper.append(tasks);
      list.append(wrapper);
    }
    const percent = Math.round((completed / rows.length) * 100);
    document.querySelector("#progress-label").textContent = `${completed} of ${rows.length} completed (${percent}%)`;
    document.querySelector("#progress-fill").style.width = `${percent}%`;
  } catch (error) { showFailure(error, list); }
}

async function loadResources() {
  const list = document.querySelector("#resource-list");
  try {
    const rows = await api(`/projects/${encodeURIComponent(projectId)}/resources`);
    if (!rows.length) return empty(list, "No shared resources yet.");
    list.replaceChildren();
    for (const item of rows) {
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3");
      if (item.url) {
        const link = document.createElement("a"); link.href = item.url; link.target = "_blank"; link.rel = "noreferrer";
        link.className = "link-resource"; link.textContent = item.title; title.append(link);
      } else { title.textContent = item.title; }
      const desc = document.createElement("p"); desc.textContent = item.description || "No description provided.";
      copy.append(title, desc);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(item.type));
      row.append(copy, meta); wrapper.append(row); list.append(wrapper);
    }
  } catch (error) { showFailure(error, list); }
}

async function loadActivity() {
  const list = document.querySelector("#activity-list");
  try {
    const page = await api(`/projects/${encodeURIComponent(projectId)}/activity?page=${activityPage}&page_size=${activityPageSize}`);
    document.querySelector("#activity-page").textContent = `Page ${activityPage}`;
    document.querySelector("#activity-prev").disabled = activityPage <= 1;
    document.querySelector("#activity-next").disabled = (page.items || []).length < activityPageSize;
    if (!page.items || !page.items.length) return empty(list, "No recorded activity yet.");
    list.replaceChildren();
    for (const item of page.items) {
      const wrapper = card("activity-row");
      const dot = document.createElement("span"); dot.className = "timeline-dot";
      const copy = document.createElement("div");
      const message = document.createElement("strong"); message.textContent = item.action;
      const time = document.createElement("time"); time.textContent = new Date(item.timestamp).toLocaleString();
      copy.append(message, time); wrapper.append(dot, copy); list.append(wrapper);
    }
  } catch (error) { showFailure(error, list); }
}

async function loadNotifications() {
  const list = document.querySelector("#notification-list");
  try {
    const rows = await api("/notifications");
    const unread = rows.filter((item) => !item.read).length;
    const badgeEl = document.querySelector("#unread-count");
    badgeEl.textContent = String(unread);
    badgeEl.hidden = unread === 0;
    if (!rows.length) return empty(list, "You have no notifications.");
    list.replaceChildren();
    for (const item of rows) {
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3"); title.textContent = item.title;
      const body = document.createElement("p"); body.textContent = item.message;
      copy.append(title, body);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(item.read ? "Read" : "New", item.read ? "" : "badge-warning"));
      row.append(copy, meta); wrapper.append(row);
      if (!item.read) {
        const action = document.createElement("button"); action.className = "small-button"; action.type = "button";
        action.textContent = "Mark as read";
        action.addEventListener("click", async () => {
          try { await api(`/notifications/${item.id}/read`, { method: "POST" }); await loadNotifications(); }
          catch (error) { setNotice(error.message, "error"); }
        });
        wrapper.append(action);
      }
      list.append(wrapper);
    }
  } catch (error) { showFailure(error, list); }
}

async function loadLetters() {
  const list = document.querySelector("#letter-list");
  try {
    const rows = await api("/lor/mine");
    if (!rows.length) return empty(list, "No letters requested or issued yet.");
    list.replaceChildren();
    for (const item of rows) {
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3");
      title.textContent = item.status === "Issued" ? "Recommendation letter" : `Recommendation request (${item.status})`;
      const details = document.createElement("p");
      details.textContent = item.body || "No letter body available.";
      copy.append(title, details);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(item.status, statusClass(item.status)));
      row.append(copy, meta); wrapper.append(row);
      if (item.faculty_user_id === currentUserId() && item.status === "Requested") {
        const actions = document.createElement("div"); actions.className = "row-actions";
        const issue = document.createElement("button"); issue.className = "small-button"; issue.type = "button"; issue.textContent = "Issue letter";
        issue.addEventListener("click", async () => {
          const body = window.prompt("Write your recommendation letter:");
          if (!body) return;
          await decideLetter(item.id, "Issue", body);
        });
        const decline = document.createElement("button"); decline.className = "small-button"; decline.type = "button"; decline.textContent = "Decline";
        decline.addEventListener("click", () => decideLetter(item.id, "Decline", ""));
        actions.append(issue, decline); wrapper.append(actions);
      }
      const summary = document.createElement("button"); summary.className = "small-button"; summary.type = "button";
      summary.textContent = "View project snapshot";
      summary.addEventListener("click", async () => {
        try {
          const data = await api(`/lor/${item.id}/summary`);
          setNotice(`Project summary · ${data.milestones.completed}/${data.milestones.total} milestones and ${data.tasks.completed}/${data.tasks.total} tasks completed.`, "success");
        } catch (error) { setNotice(error.message, "error"); }
      });
      wrapper.append(summary);
      list.append(wrapper);
    }
  } catch (error) { showFailure(error, list); }
}

function currentUserId() {
  try { return Number(JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub); } catch { return -1; }
}

async function decideLetter(id, decision, body) {
  try {
    await api(`/lor/${id}/decide`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, body }) });
    setNotice(`Request ${decision.toLowerCase()}.`, "success");
    await loadLetters();
  } catch (error) { setNotice(error.message, "error"); }
}

async function loadPanel(name) {
  if (!projectId && name !== "notifications" && name !== "letters") {
    setNotice("Open a project using its project link to load this workspace.", "error");
    return;
  }
  setNotice("");
  if (name === "milestones") await loadMilestones();
  if (name === "resources") await loadResources();
  if (name === "activity") await loadActivity();
  if (name === "notifications") await loadNotifications();
  if (name === "letters") await loadLetters();
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", async () => {
  activePanel = tab.dataset.panel;
  document.querySelectorAll(".tab").forEach((item) => { const active = item === tab; item.classList.toggle("is-active", active); item.setAttribute("aria-selected", String(active)); });
  document.querySelectorAll(".panel").forEach((panel) => { panel.hidden = panel.id !== `panel-${activePanel}`; });
  await loadPanel(activePanel);
}));

document.querySelector("#refresh-button").addEventListener("click", () => loadPanel(activePanel));
document.querySelector("#new-milestone").addEventListener("click", () => document.querySelector("#milestone-dialog").showModal());
document.querySelector("#cancel-milestone").addEventListener("click", () => document.querySelector("#milestone-dialog").close());
document.querySelector("#milestone-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; const values = Object.fromEntries(new FormData(form));
  try { await api(`/projects/${encodeURIComponent(projectId)}/milestones`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) }); form.reset(); document.querySelector("#milestone-dialog").close(); setNotice("Milestone created.", "success"); await Promise.all([loadMilestones(), loadActivity()]); }
  catch (error) { setNotice(error.message, "error"); }
});

document.querySelector("#resource-form [name=type]").addEventListener("change", (event) => {
  const isFile = event.target.value === "File";
  document.querySelector("#file-field").hidden = !isFile;
  document.querySelector("#url-field").hidden = isFile;
});
document.querySelector("#resource-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; const values = new FormData(form); const type = values.get("type");
  try {
    if (type === "File") {
      const file = values.get("file"); if (!file?.size) throw new Error("Choose a file to upload.");
      const query = new URLSearchParams({ title: values.get("title"), description: values.get("description") });
      await api(`/projects/${encodeURIComponent(projectId)}/resources/upload?${query}`, { method: "POST", headers: { "Content-Type": file.type || "application/octet-stream", "X-Filename": file.name }, body: file });
    } else {
      await api(`/projects/${encodeURIComponent(projectId)}/resources`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: values.get("title"), description: values.get("description"), type, url: values.get("url") || null }) });
    }
    form.reset(); document.querySelector("#file-field").hidden = true; document.querySelector("#url-field").hidden = false;
    setNotice("Resource added.", "success"); await Promise.all([loadResources(), loadActivity()]);
  } catch (error) { setNotice(error.message, "error"); }
});

document.querySelector("#activity-prev").addEventListener("click", async () => { activityPage = Math.max(1, activityPage - 1); await loadActivity(); });
document.querySelector("#activity-next").addEventListener("click", async () => { activityPage += 1; await loadActivity(); });
document.querySelector("#letter-request-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const facultyUserId = Number(new FormData(event.currentTarget).get("faculty_user_id"));
  try { await api("/lor/request", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ faculty_user_id: facultyUserId, project_id: projectId ? Number(projectId) : null }) }); event.currentTarget.reset(); setNotice("Your request was sent.", "success"); await Promise.all([loadLetters(), loadNotifications()]); }
  catch (error) { setNotice(error.message, "error"); }
});

async function initWorkspace() {
  if (!token) {
    setNotice("Please sign in to view your research project workspace. <a href='/#/login' style='color:var(--color-teal);font-weight:700;text-decoration:underline;margin-left:8px;'>Sign in →</a>", "error");
    document.querySelector("#milestone-list").innerHTML = '<div class="empty"><p style="font-size:15px;margin-bottom:12px;">Sign in to your ResearchBridge account to view your project workspace.</p><a href="/#/login" class="button button-primary" style="text-decoration:none;display:inline-block;">Sign in to continue →</a></div>';
    return;
  }
  if (!projectId) {
    try {
      const studentDash = await api("/dashboard/student").catch(() => null);
      const facultyDash = !studentDash ? await api("/dashboard/faculty").catch(() => null) : null;
      const projs = (studentDash && studentDash.projects) || (facultyDash && facultyDash.projects) || [];
      if (projs.length > 0) {
        projectId = String(projs[0].project_id || projs[0].id);
        const titleEl = document.querySelector("#project-title");
        if (titleEl && projs[0].title) titleEl.textContent = projs[0].title;
      } else {
        document.querySelector("#milestone-list").innerHTML = '<div class="empty"><p style="font-size:15px;margin-bottom:12px;">No active project enrolled yet. Browse open faculty opportunities to join a research team.</p><a href="/#/opportunities" class="button button-primary" style="text-decoration:none;display:inline-block;">Explore Opportunities →</a></div>';
        setNotice("You do not have any active research projects yet. Once accepted into a project, your lab workspace will appear here.", "info");
        return;
      }
    } catch (e) {
      console.warn("Could not auto-resolve project", e);
    }
  }
  if (!projectId) {
    document.querySelector("#project-title").textContent = "Research workspace";
  }
  await loadPanel("milestones");
}

initWorkspace();
