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
  token = token || sessionStorage.getItem("rb-token") || localStorage.getItem("rb-token");
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

async function api(path, options = {}) {
  token = token || sessionStorage.getItem("rb-token") || localStorage.getItem("rb-token");
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
    if (!rows.length) return empty(list, "No resources shared yet. Upload slides (.pptx), documents (.pdf, .docx), datasets, or links.");
    list.replaceChildren();
    for (const item of rows) {
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3");
      const ext = (item.title.split('.').pop() || '').toUpperCase();
      const isDoc = ['PPTX', 'PPT', 'PDF', 'DOCX', 'DOC', 'XLSX', 'CSV', 'ZIP'].includes(ext);

      if (item.link_url || item.url) {
        const url = item.link_url || item.url;
        const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noreferrer";
        link.className = "link-resource"; link.textContent = item.title; title.append(link);
      } else if (item.has_file) {
        const downloadUrl = `${apiBase}/resources/${encodeURIComponent(item.id)}/download`;
        const link = document.createElement("a"); link.href = downloadUrl; link.target = "_blank";
        link.className = "link-resource"; link.textContent = item.title;
        title.append(link);
      } else {
        title.textContent = item.title;
      }
      const desc = document.createElement("p"); desc.textContent = item.description || "No description provided.";
      copy.append(title, desc);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(isDoc ? ext : item.type));
      if (item.has_file) {
        const downloadBtn = document.createElement("a");
        downloadBtn.href = `${apiBase}/resources/${encodeURIComponent(item.id)}/download`;
        downloadBtn.target = "_blank";
        downloadBtn.className = "small-button";
        downloadBtn.style.cssText = "text-decoration:none;display:inline-flex;align-items:center;padding:4px 8px;font-size:11px;";
        downloadBtn.textContent = "Download ⤓";
        meta.append(downloadBtn);
      }
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
      const title = document.createElement("h3"); title.textContent = item.title || item.type || "Notification";
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

function currentUserRole() {
  try { return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).role || "Student"; } catch { return "Student"; }
}

async function loadLetters() {
  const list = document.querySelector("#letter-list");
  const isFaculty = currentUserRole() === "Faculty";
  const reqForm = document.querySelector("#letter-request-form");
  const fBanner = document.querySelector("#faculty-lor-banner");
  
  if (reqForm) reqForm.hidden = isFaculty;
  if (fBanner) fBanner.hidden = !isFaculty;

  if (!isFaculty && reqForm && projectId) {
    try {
      const proj = await api(`/projects/${encodeURIComponent(projectId)}`).catch(() => null);
      if (proj && proj.members) {
        const lead = proj.members.find(m => m.role === "Lead");
        const leadInput = reqForm.querySelector("[name=faculty_user_id]");
        if (lead && leadInput && !leadInput.value) {
          leadInput.value = lead.user_id;
        }
      }
    } catch {}
  }

  try {
    const rows = await api("/lor/mine");
    if (!rows.length) {
      return empty(list, isFaculty ? "No student recommendation requests received yet. When students submit a request, it will appear here." : "No letters requested or issued yet.");
    }
    list.replaceChildren();
    for (const item of rows) {
      const wrapper = card();
      const row = document.createElement("div"); row.className = "row";
      const copy = document.createElement("div");
      const title = document.createElement("h3");
      if (isFaculty) {
        title.textContent = item.status === "Requested" ? `Request from Student #${item.student_user_id}` : `Recommendation for Student #${item.student_user_id} (${item.status})`;
      } else {
        title.textContent = item.status === "Issued" ? "Recommendation letter" : `Recommendation request (${item.status})`;
      }
      const details = document.createElement("p");
      details.textContent = item.body || (item.status === "Requested" ? "Awaiting your review and decision." : "No letter body available.");
      copy.append(title, details);
      const meta = document.createElement("div"); meta.className = "row-meta";
      meta.append(badge(item.status, statusClass(item.status)));
      row.append(copy, meta); wrapper.append(row);
      if (item.faculty_user_id === currentUserId() && item.status === "Requested") {
        const actions = document.createElement("div"); actions.className = "row-actions";
        const issue = document.createElement("button"); issue.className = "small-button"; issue.type = "button"; issue.textContent = "Issue letter";
        issue.addEventListener("click", async () => {
          const body = window.prompt("Write your recommendation letter for the student:");
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

const typeSelect = document.querySelector("#resource-form [name=type]");
if (typeSelect) {
  typeSelect.addEventListener("change", (event) => {
    const val = event.target.value;
    const isLink = val === "Link";
    const isFile = val === "File";
    document.querySelector("#file-field").hidden = isLink;
    document.querySelector("#url-field").hidden = isFile;
  });
}
document.querySelector("#resource-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const type = values.get("type");
  const file = values.get("file");
  const url = values.get("url");

  try {
    if (file && file.size > 0 && type !== "Link") {
      const query = new URLSearchParams({ title: values.get("title"), description: values.get("description") });
      await api(`/projects/${encodeURIComponent(projectId)}/resources/upload?${query}`, {
        method: "POST",
        headers: { "Content-Type": file.type || "application/octet-stream", "X-Filename": file.name },
        body: file
      });
    } else {
      if (type === "Link" && !url) throw new Error("Please provide a valid URL for link resources.");
      await api(`/projects/${encodeURIComponent(projectId)}/resources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: values.get("title"),
          description: values.get("description"),
          type: type === "File" ? "Paper" : type,
          url: url || null
        })
      });
    }
    form.reset();
    document.querySelector("#file-field").hidden = false;
    document.querySelector("#url-field").hidden = true;
    setNotice("Resource added.", "success");
    await Promise.all([loadResources(), loadActivity()]);
  } catch (error) {
    setNotice(error.message, "error");
  }
});

document.querySelector("#activity-prev").addEventListener("click", async () => { activityPage = Math.max(1, activityPage - 1); await loadActivity(); });
document.querySelector("#activity-next").addEventListener("click", async () => { activityPage += 1; await loadActivity(); });
document.querySelector("#letter-request-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const facultyUserId = Number(new FormData(event.currentTarget).get("faculty_user_id"));
  try { await api("/lor/request", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ faculty_user_id: facultyUserId, project_id: projectId ? Number(projectId) : null }) }); event.currentTarget.reset(); setNotice("Your request was sent.", "success"); await Promise.all([loadLetters(), loadNotifications()]); }
  catch (error) { setNotice(error.message, "error"); }
});

async function initWorkspace() {
  token = token || sessionStorage.getItem("rb-token") || localStorage.getItem("rb-token");
  if (token) {
    sessionStorage.setItem("rb-token", token);
    localStorage.setItem("rb-token", token);
  }
  if (!token) {
    setNotice("Please sign in to view your research project workspace. <a href='/#/login' style='color:var(--color-teal);font-weight:700;text-decoration:underline;margin-left:8px;'>Sign in &rarr;</a>", "error");
    document.querySelector("#milestone-list").innerHTML = '<div class="empty"><p style="font-size:15px;margin-bottom:12px;">Sign in to your ResearchBridge account to view your project workspace.</p><a href="/#/login" class="button button-primary" style="text-decoration:none;display:inline-block;">Sign in to continue &rarr;</a></div>';
    return;
  }

  let projs = [];
  try {
    const list = await api("/projects").catch(() => null);
    if (Array.isArray(list) && list.length > 0) {
      projs = list;
    }
  } catch (e) {
    console.warn("Could not load /projects", e);
  }

  if (projs.length === 0) {
    try {
      const studentDash = await api("/dashboard/student").catch(() => null);
      const facultyDash = !studentDash ? await api("/dashboard/faculty").catch(() => null) : null;
      projs = (studentDash && studentDash.projects) || (facultyDash && (facultyDash.active_projects || facultyDash.projects)) || [];
    } catch (e) {
      console.warn("Could not load dashboard fallback", e);
    }
  }

  const titleEl = document.querySelector("#project-title");

  if (projs.length > 0) {
    const matchingProj = projs.find(p => String(p.id || p.project_id) === String(projectId));
    if (matchingProj) {
      projectId = String(matchingProj.id || matchingProj.project_id);
      if (titleEl) titleEl.textContent = matchingProj.title || "Research workspace";
    } else {
      projectId = String(projs[0].id || projs[0].project_id);
      if (titleEl) titleEl.textContent = projs[0].title || "Research workspace";
    }

    if (projs.length > 1 && titleEl) {
      let switcher = document.querySelector("#project-switcher");
      if (!switcher) {
        switcher = document.createElement("select");
        switcher.id = "project-switcher";
        switcher.setAttribute("aria-label", "Select research project");
        switcher.style.cssText = "margin-top: 8px; padding: 6px 12px; font-size: 13px; font-weight: 600; border-radius: 8px; border: 1px solid var(--color-border); background: #fff; color: var(--color-teal); cursor: pointer; max-width: 380px;";
        titleEl.insertAdjacentElement("afterend", switcher);
      }
      switcher.innerHTML = projs.map(p => {
        const pid = String(p.id || p.project_id);
        const selected = pid === String(projectId) ? "selected" : "";
        const roleStr = p.role_in_project ? ` · ${p.role_in_project}` : "";
        return `<option value="${pid}" ${selected}>${p.title}${roleStr}</option>`;
      }).join("");
      switcher.onchange = async (e) => {
        projectId = e.target.value;
        const sel = projs.find(p => String(p.id || p.project_id) === String(projectId));
        if (titleEl && sel) titleEl.textContent = sel.title;
        const newParams = new URLSearchParams(window.location.search);
        newParams.set("project", projectId);
        history.replaceState(null, "", `${location.pathname}?${newParams.toString()}${location.hash}`);
        await loadPanel(activePanel);
      };
    }
  } else if (!projectId) {
    let userRole = "Student";
    try {
      const me = await api("/me").catch(() => null);
      if (me && me.role) userRole = me.role;
    } catch {
      // default
    }

    if (userRole === "Faculty") {
      document.querySelector("#milestone-list").innerHTML = '<div class="empty"><p style="font-size:15px;margin-bottom:12px;">No active research lab workspace yet. When student applications are accepted or a project is launched from your opportunities, your lab workspace will appear here.</p><a href="/#/my-opportunities" class="button button-primary" style="text-decoration:none;display:inline-block;">View My Opportunities &rarr;</a></div>';
      setNotice("You do not have any active research projects yet. Review your open opportunities to accept students and activate your lab.", "info");
    } else {
      document.querySelector("#milestone-list").innerHTML = '<div class="empty"><p style="font-size:15px;margin-bottom:12px;">No active project enrolled yet. Browse open faculty opportunities to join a research team.</p><a href="/#/opportunities" class="button button-primary" style="text-decoration:none;display:inline-block;">Explore Opportunities &rarr;</a></div>';
      setNotice("You do not have any active research projects yet. Once accepted into a project, your lab workspace will appear here.", "info");
    }
    return;
  }

  if (projectId) {
    await loadPanel("milestones");
  }
}

initWorkspace();
