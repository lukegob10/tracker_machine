const API_BASE = "/api";

const els = {
  navButtons: document.querySelectorAll(".nav-btn[data-view]"),
  views: document.querySelectorAll(".view"),
  status: document.getElementById("connection-status"),
  currentUser: document.getElementById("current-user"),
  logoutBtn: document.getElementById("logout-btn"),
  themeToggle: document.getElementById("theme-toggle"),
  appShell: document.getElementById("app-shell"),
  authScreen: document.getElementById("auth-screen"),
  authTabLogin: document.getElementById("auth-tab-login"),
  authTabRegister: document.getElementById("auth-tab-register"),
  loginForm: document.getElementById("login-form"),
  registerForm: document.getElementById("register-form"),
  authError: document.getElementById("auth-error"),
  masterFilters: document.getElementById("master-filters"),
  masterTable: document.getElementById("master-table"),
  dashboardCards: document.getElementById("dashboard-cards"),
  projectsSummary: document.getElementById("projects-summary"),
  solutionsSummary: document.getElementById("solutions-summary"),
  attentionPanel: document.getElementById("attention-panel"),
  upcomingPanel: document.getElementById("upcoming-panel"),
  projectForm: document.getElementById("project-form"),
  projectList: document.getElementById("project-list"),
  projectsDownload: document.getElementById("projects-download"),
  projectsUpload: document.getElementById("projects-upload"),
  projectsFile: document.getElementById("projects-file"),
  projectsImportResult: document.getElementById("projects-import-result"),
  solutionForm: document.getElementById("solution-form"),
  solutionList: document.getElementById("solution-list"),
  solutionsDownload: document.getElementById("solutions-download"),
  solutionsUpload: document.getElementById("solutions-upload"),
  solutionsFile: document.getElementById("solutions-file"),
  solutionsImportResult: document.getElementById("solutions-import-result"),
  phasesTable: document.getElementById("phases-table"),
  subcomponentForm: document.getElementById("subcomponent-form"),
  subcomponentList: document.getElementById("subcomponent-list"),
  subcomponentsDownload: document.getElementById("subcomponents-download"),
  subcomponentsUpload: document.getElementById("subcomponents-upload"),
  subcomponentsFile: document.getElementById("subcomponents-file"),
  subcomponentsImportResult: document.getElementById("subcomponents-import-result"),
  kanbanBoard: document.getElementById("kanban-board"),
  calendarGrid: document.getElementById("calendar-grid"),
  newProjectBtn: document.getElementById("new-project"),
  newSolutionBtn: document.getElementById("new-solution"),
  newSubcomponentBtn: document.getElementById("new-subcomponent"),
};

const state = {
  user: null,
  authed: false,
  authMode: "login",
  phases: [],
  projects: [],
  solutions: [],
  solutionPhases: {}, // solution_id -> phases
  subcomponents: [],
  filters: {},
  currentView: "master",
  theme: "dark",
  loading: false,
  pendingRefresh: false,
};

let liveSyncStarted = false;
let refreshInFlight = false;
const pendingRefreshEntities = new Set();
const ignoreNextRefresh = new Set();

function markIgnoreRefresh(entity) {
  if (entity) ignoreNextRefresh.add(entity);
}

async function refreshFromServer(entity = "all") {
  const ent = entity || "all";
  if (!state.authed) return;

  if (ignoreNextRefresh.has(ent)) {
    ignoreNextRefresh.delete(ent);
    return;
  }

  if (state.loading || refreshInFlight) {
    pendingRefreshEntities.add(ent);
    return;
  }

  const selectedProjectId = els.projectForm?.querySelector('[name="project_id"]')?.value || "";
  const selectedSolutionId = els.solutionForm?.querySelector('[name="solution_id"]')?.value || "";
  const selectedSubcomponentId = els.subcomponentForm?.querySelector('[name="subcomponent_id"]')?.value || "";

  refreshInFlight = true;
  try {
    if (ent === "projects") {
      state.projects = await api("/projects");
      populateSelects();
    } else if (ent === "solutions") {
      state.solutions = await api("/solutions");
      populateSelects();
    } else if (ent === "subcomponents") {
      state.subcomponents = await api("/subcomponents");
    } else if (ent === "phases") {
      state.phases = await api("/phases");
      state.solutionPhases = {};
      populateSelects();
    } else {
      const [phases, projects, solutions, subcomponents] = await Promise.all([
        api("/phases"),
        api("/projects"),
        api("/solutions"),
        api("/subcomponents"),
      ]);
      state.phases = phases;
      state.projects = projects;
      state.solutions = solutions;
      state.subcomponents = subcomponents;
      state.solutionPhases = {};
      populateSelects();
    }

    renderActiveView();
    restoreSelections(selectedProjectId, selectedSolutionId, selectedSubcomponentId);
  } catch (err) {
    console.warn("Refresh failed", err);
    if (handleAuthError(err)) {
      setStatus("Sign in required", "warn");
    }
  } finally {
    refreshInFlight = false;
    if (pendingRefreshEntities.size) {
      const pending = Array.from(pendingRefreshEntities);
      pendingRefreshEntities.clear();
      if (pending.includes("all") || pending.length > 1) {
        refreshFromServer("all");
      } else {
        refreshFromServer(pending[0]);
      }
    }
  }
}

function setStatus(text, type = "") {
  if (!els.status) return;
  els.status.textContent = text;
  els.status.className = `pill ${type}`;
}

function setImportResult(el, message, isError = false) {
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("error", !!isError);
}

function setAuthVisible(show) {
  if (els.authScreen) els.authScreen.classList.toggle("hidden", !show);
  if (els.appShell) els.appShell.classList.toggle("hidden", show);
}

function setAuthed(user) {
  state.user = user;
  state.authed = !!user;
  if (els.currentUser) {
    els.currentUser.textContent = user ? user.display_name || user.email : "Not signed in";
    els.currentUser.classList.toggle("muted", !user);
  }
  if (els.logoutBtn) {
    els.logoutBtn.disabled = !user;
  }
  setAuthVisible(!state.authed);
  if (!state.authed) {
    setStatus("Sign in required", "warn");
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  els.authTabLogin?.classList.toggle("active", mode === "login");
  els.authTabRegister?.classList.toggle("active", mode === "register");
  els.loginForm?.classList.toggle("hidden", mode !== "login");
  els.registerForm?.classList.toggle("hidden", mode !== "register");
  if (els.authError) els.authError.textContent = "";
}

function showAuthError(message) {
  if (els.authError) {
    els.authError.textContent = message || "";
  }
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text || null;
  }
  if (!res.ok) {
    const err = new Error((data && data.detail) || data || res.statusText);
    err.status = res.status;
    throw err;
  }
  return data;
}

function handleAuthError(err) {
  if (err && err.status === 401) {
    setAuthed(null);
    setAuthVisible(true);
    return true;
  }
  return false;
}

async function fetchCurrentUser() {
  try {
    const me = await api("/auth/me");
    setAuthed(me);
    return me;
  } catch (err) {
    if (err.status === 401) {
      setAuthed(null);
      return null;
    }
    throw err;
  }
}

async function performLogin(email, password) {
  return api("/auth/login", {
    method: "POST",
    body: JSON.stringify({ soeid: email, password }),
  });
}

async function performRegister(display_name, email, password) {
  return api("/auth/register", {
    method: "POST",
    body: JSON.stringify({ display_name, soeid: email, password }),
  });
}

function bindAuthUI() {
  setAuthMode("login");
  els.authTabLogin?.addEventListener("click", () => setAuthMode("login"));
  els.authTabRegister?.addEventListener("click", () => setAuthMode("register"));

  els.loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    showAuthError("");
    const form = new FormData(els.loginForm);
    try {
      const user = await performLogin(form.get("soeid"), form.get("password"));
      setAuthed(user);
      setAuthVisible(false);
      startLiveSyncOnce();
      await loadData();
    } catch (err) {
      if (!handleAuthError(err)) {
        showAuthError(err.message || "Login failed");
      }
    }
  });

  els.registerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    showAuthError("");
    const form = new FormData(els.registerForm);
    try {
      const user = await performRegister(form.get("display_name"), form.get("soeid"), form.get("password"));
      setAuthed(user);
      setAuthVisible(false);
      startLiveSyncOnce();
      await loadData();
    } catch (err) {
      if (!handleAuthError(err)) {
        showAuthError(err.message || "Registration failed");
      }
    }
  });

  els.logoutBtn?.addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch (err) {
      console.warn("Logout error", err);
    } finally {
      setAuthed(null);
      setAuthVisible(true);
    }
  });
}

function startLiveSyncOnce() {
  if (liveSyncStarted) return;
  initLiveSync();
  liveSyncStarted = true;
}

async function bootstrapAuth() {
  setStatus("Checking session...", "warn");
  setAuthVisible(true);
  const user = await fetchCurrentUser();
  if (user) {
    setAuthVisible(false);
    startLiveSyncOnce();
    await loadData();
  } else {
    setStatus("Sign in required", "warn");
  }
}

async function loadData() {
  if (!state.authed) {
    setStatus("Sign in required", "warn");
    setAuthVisible(true);
    return;
  }
  const selectedProjectId = els.projectForm?.querySelector('[name="project_id"]')?.value || "";
  const selectedSolutionId = els.solutionForm?.querySelector('[name="solution_id"]')?.value || "";
  const selectedSubcomponentId = els.subcomponentForm?.querySelector('[name="subcomponent_id"]')?.value || "";
  if (state.loading) {
    state.pendingRefresh = true;
    return;
  }
  state.loading = true;
  try {
    setStatus("Loading...", "warn");
    const [phases, projects, solutions, subcomponents] = await Promise.all([
      api("/phases"),
      api("/projects"),
      api("/solutions"),
      api("/subcomponents"),
    ]);

    state.phases = phases;
    state.projects = projects;
    state.solutions = solutions;
    state.subcomponents = subcomponents;
    state.solutionPhases = {};
    populateSelects();

    if (!state.projects.length && !state.solutions.length) {
      setStatus("No data loaded", "warn");
      alert("No data loaded. Create a project/solution/subcomponent to begin.");
    } else {
      setStatus("Online", "positive");
    }
    renderActiveView();
    restoreSelections(selectedProjectId, selectedSolutionId, selectedSubcomponentId);
  } catch (err) {
    console.error(err);
    if (handleAuthError(err)) {
      setStatus("Sign in required", "warn");
    } else {
      setStatus("Error", "danger");
    }
  } finally {
    state.loading = false;
    if (state.pendingRefresh) {
      state.pendingRefresh = false;
      loadData();
    }
    if (pendingRefreshEntities.size) {
      const pending = Array.from(pendingRefreshEntities);
      pendingRefreshEntities.clear();
      if (pending.includes("all") || pending.length > 1) {
        refreshFromServer("all");
      } else {
        refreshFromServer(pending[0]);
      }
    }
  }
}

function setView(view) {
  state.currentView = view;
  els.views.forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  els.navButtons.forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  if (state.authed) renderActiveView();
}

function applyTheme(theme) {
  state.theme = theme;
  document.body.classList.toggle("theme-light", theme === "light");
  if (els.themeToggle) {
    els.themeToggle.textContent = theme === "light" ? "Dark Mode" : "Light Mode";
  }
  try {
    localStorage.setItem("jira-lite-theme", theme);
  } catch (e) {
    console.warn("Theme preference not saved", e);
  }
}

function initTheme() {
  let saved = "dark";
  try {
    saved = localStorage.getItem("jira-lite-theme") || "dark";
  } catch (e) {
    console.warn("Theme preference not loaded", e);
  }
  applyTheme(saved === "light" ? "light" : "dark");
  els.themeToggle?.addEventListener("click", () => {
    const next = document.body.classList.contains("theme-light") ? "dark" : "light";
    applyTheme(next);
  });
}

function upsertById(list, item, idKey) {
  if (!item || !list) return;
  const id = item[idKey];
  if (!id) return;
  const idx = list.findIndex((row) => row[idKey] === id);
  if (idx === -1) list.push(item);
  else list[idx] = item;
}

function renderActiveView() {
  switch (state.currentView) {
    case "master":
      renderMasterFilters();
      renderMasterTable();
      break;
    case "dashboard":
      renderDashboard();
      break;
    case "projects":
      renderProjects();
      break;
    case "solutions":
      renderSolutions();
      break;
    case "subcomponents":
      renderSubcomponents();
      break;
    case "kanban":
      renderKanban();
      break;
    case "calendar":
      renderCalendar();
      break;
    default:
      renderMasterFilters();
      renderMasterTable();
  }
}

function liveUrl() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${location.host}/api/ws`;
}

function initLiveSync() {
  let socket;
  let backoff = 1000;

  const connect = () => {
    socket = new WebSocket(liveUrl());

    socket.addEventListener("open", () => {
      backoff = 1000;
      setStatus("Online", "positive");
    });

    socket.addEventListener("message", (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "refresh") {
          refreshFromServer(msg.entity || "all");
        }
      } catch (err) {
        console.warn("Live message parse failed", err);
      }
    });

    const retry = () => {
      socket = null;
      backoff = Math.min(backoff * 1.5, 5000);
      setTimeout(connect, backoff);
    };

    socket.addEventListener("close", retry);
    socket.addEventListener("error", retry);
  };

  connect();
}

function restoreSelections(projectId, solutionId, subcomponentId) {
  if (projectId && els.projectForm) {
    const proj = state.projects.find((p) => p.project_id === projectId);
    if (proj) {
      els.projectForm.querySelector('[name="project_id"]').value = proj.project_id;
      els.projectForm.querySelector('[name="project_name"]').value = proj.project_name || "";
      els.projectForm.querySelector('[name="name_abbreviation"]').value = proj.name_abbreviation || "";
      els.projectForm.querySelector('[name="status"]').value = proj.status || "";
      els.projectForm.querySelector('[name="description"]').value = proj.description || "";
      els.projectForm.querySelector('[name="success_criteria"]').value = proj.success_criteria || "";
      els.projectForm.querySelector('[name="sponsor"]').value = proj.sponsor || "";
    }
  }

	  if (solutionId && els.solutionForm) {
	    const sol = state.solutions.find((s) => s.solution_id === solutionId);
	    if (sol) {
	      els.solutionForm.querySelector('[name="solution_id"]').value = sol.solution_id;
	      els.solutionForm.querySelector('[name="project_id"]').value = sol.project_id;
	      els.solutionForm.querySelector('[name="solution_name"]').value = sol.solution_name || "";
	      els.solutionForm.querySelector('[name="version"]').value = sol.version || "";
	      els.solutionForm.querySelector('[name="status"]').value = sol.status || "";
	      els.solutionForm.querySelector('[name="rag_source"]').value = sol.rag_source || "auto";
	      els.solutionForm.querySelector('[name="rag_status"]').value = sol.rag_status || "amber";
	      els.solutionForm.querySelector('[name="rag_reason"]').value = sol.rag_reason || "";
	      els.solutionForm.querySelector('[name="priority"]').value = sol.priority ?? "";
	      els.solutionForm.querySelector('[name="due_date"]').value = sol.due_date || "";
	      els.solutionForm.querySelector('[name="description"]').value = sol.description || "";
	      els.solutionForm.querySelector('[name="success_criteria"]').value = sol.success_criteria || "";
	      els.solutionForm.querySelector('[name="owner"]').value = sol.owner || "";
      els.solutionForm.querySelector('[name="assignee"]').value = sol.assignee || "";
      els.solutionForm.querySelector('[name="approver"]').value = sol.approver || "";
      els.solutionForm.querySelector('[name="key_stakeholder"]').value = sol.key_stakeholder || "";
      els.solutionForm.querySelector('[name="blockers"]').value = sol.blockers || "";
      els.solutionForm.querySelector('[name="risks"]').value = sol.risks || "";
	      updateCurrentPhaseOptions(sol.solution_id);
	      els.solutionForm.querySelector('[name="current_phase"]').value = sol.current_phase || "";
	      renderSolutionPhases(sol.solution_id);
	      updateRagFormControls();
	    }
	  }

  if (subcomponentId && els.subcomponentForm) {
    const sub = state.subcomponents.find((s) => s.subcomponent_id === subcomponentId);
    if (sub) {
      els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = sub.subcomponent_id;
      els.subcomponentForm.querySelector('[name="project_id"]').value = sub.project_id;
      updateSubcomponentSolutionOptions(sub.project_id);
      els.subcomponentForm.querySelector('[name="solution_id"]').value = sub.solution_id;
      els.subcomponentForm.querySelector('[name="subcomponent_name"]').value = sub.subcomponent_name || "";
      els.subcomponentForm.querySelector('[name="priority"]').value = sub.priority ?? "";
      els.subcomponentForm.querySelector('[name="due_date"]').value = sub.due_date || "";
      els.subcomponentForm.querySelector('[name="status"]').value = sub.status || "";
      els.subcomponentForm.querySelector('[name="assignee"]').value = sub.assignee || "";
    }
  }
}

function renderMasterFilters() {
  const root = els.masterFilters;
  if (!root) return;
  const projectOpts = state.projects.map((p) => `<option value="${p.project_id}">${p.project_name}</option>`).join("");
  const phaseOpts = state.phases.map((p) => `<option value="${p.phase_id}">${phaseDisplayName(p.phase_id)}</option>`).join("");
  const ownerOptions = Array.from(new Set(state.solutions.map((s) => s.owner).filter(Boolean))).map(
    (o) => `<option value="${o}">${o}</option>`
  ).join("");
  const assigneeOptions = Array.from(new Set(state.solutions.map((s) => s.assignee).filter(Boolean))).map(
    (o) => `<option value="${o}">${o}</option>`
  ).join("");
  root.innerHTML = `
    <label>Status
      <select data-filter="status">
        <option value="">Any</option>
        <option value="not_started">Not started</option>
        <option value="active">Active</option>
        <option value="on_hold">On hold</option>
        <option value="complete">Complete</option>
        <option value="abandoned">Abandoned</option>
      </select>
    </label>
    <label>Project
      <select data-filter="project_id"><option value="">Any</option>${projectOpts}</select>
    </label>
    <label>Current Phase
      <select data-filter="current_phase"><option value="">Any</option>${phaseOpts}</select>
    </label>
    <label>Priority ≤ <input type="number" data-filter="priority" min="0" max="5" /></label>
    <label>Owner
      <select data-filter="owner"><option value="">Any</option>${ownerOptions}</select>
    </label>
    <label>Assignee
      <select data-filter="assignee"><option value="">Any</option>${assigneeOptions}</select>
    </label>
    <label>Search <input type="text" data-filter="search" placeholder="Solution or notes" /></label>
  `;
  root.querySelectorAll("[data-filter]").forEach((el) => {
    const key = el.dataset.filter;
    if (state.filters[key] !== undefined) el.value = state.filters[key];
    el.addEventListener("input", () => {
      state.filters[key] = el.value;
      renderMasterTable();
      renderKanban();
      renderCalendar();
    });
  });
}

function filteredSolutions() {
  const f = state.filters || {};
  return state.solutions.filter((s) => {
    if (f.status && s.status !== f.status) return false;
    if (f.project_id && s.project_id !== f.project_id) return false;
    if (f.priority && Number(s.priority) > Number(f.priority)) return false;
    if (f.owner && s.owner !== f.owner) return false;
    if (f.assignee && s.assignee !== f.assignee) return false;
    if (f.current_phase && s.current_phase !== f.current_phase) return false;
    if (f.search) {
      const text = `${s.solution_name || ""} ${s.description || ""} ${s.success_criteria || ""} ${s.blockers || ""} ${s.risks || ""}`.toLowerCase();
      if (!text.includes(f.search.toLowerCase())) return false;
    }
    return true;
  });
}

function orderedPhases(solutionId) {
  const enabled = (state.solutionPhases[solutionId] || []).filter((p) => p.is_enabled);
  return enabled.sort((a, b) => {
    const aSeq = a.sequence_override ?? state.phases.find((p) => p.phase_id === a.phase_id)?.sequence ?? 0;
    const bSeq = b.sequence_override ?? state.phases.find((p) => p.phase_id === b.phase_id)?.sequence ?? 0;
    return aSeq - bSeq;
  });
}

function updateCurrentPhaseOptions(solutionId) {
  const sel = els.solutionForm?.querySelector('[name="current_phase"]');
  if (!sel) return;

  const enabledPhaseIds = orderedPhases(solutionId).map((p) => p.phase_id);
  const phases = enabledPhaseIds.length
    ? enabledPhaseIds
        .map((id) => state.phases.find((p) => p.phase_id === id) || { phase_id: id, phase_name: id })
        .filter(Boolean)
    : state.phases;

  const opts = phases
    .map((p) => `<option value="${p.phase_id}">${phaseDisplayName(p.phase_id) || p.phase_id}</option>`)
    .join("");
  sel.innerHTML = `<option value="">None</option>${opts}`;
}

function solutionProgress(solution) {
  if (!solution) return 0;
  if (solution.status === "complete") return 100;
  if (!state.phases.length || !solution.current_phase) return 0;
  const phases = [...state.phases].sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));
  const idx = phases.findIndex((p) => p.phase_id === solution.current_phase);
  if (idx === -1) return 0;
  return Math.round(((idx + 1) / phases.length) * 100);
}

function formatStatus(status) {
  if (!status) return "—";
  return status
    .toString()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function escapeAttr(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function ragPill(ragStatus, ragSource, ragReason) {
  if (!ragStatus) return "—";
  const status = String(ragStatus);
  const source = String(ragSource || "auto");
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  const cls = status === "red" ? "danger" : status === "green" ? "positive" : "warn";
  const title =
    source === "manual" && ragReason
      ? `Manual: ${ragReason}`
      : source === "manual"
        ? "Manual override"
        : "Auto";
  const suffix = source === "manual" ? "*" : "";
  return `<span class="pill ${cls}" title="${escapeAttr(title)}">${label}${suffix}</span>`;
}

function updateRagFormControls() {
  const form = els.solutionForm;
  if (!form) return;
  const sourceEl = form.querySelector('[name="rag_source"]');
  const statusEl = form.querySelector('[name="rag_status"]');
  const reasonEl = form.querySelector('[name="rag_reason"]');
  const reasonLabel = form.querySelector(".rag-reason-field");
  if (!sourceEl || !statusEl || !reasonEl) return;

  const manual = (sourceEl.value || "auto") === "manual";
  statusEl.disabled = !manual;
  reasonEl.disabled = !manual;
  if (reasonLabel) reasonLabel.classList.toggle("hidden", !manual);
  if (!manual) reasonEl.value = "";
}

function phaseDisplayName(phaseId) {
  if (!phaseId) return "";
  const phase = state.phases.find((p) => p.phase_id === phaseId);
  const name = phase?.phase_name || phaseId;
  if (phaseId === "poc" || name.toLowerCase() === "poc") return "Proof of Concept";
  return name;
}

function renderMasterTable() {
  if (!els.masterTable) return;
  const rows = filteredSolutions();
  const header = ["Project", "Sponsor", "Solution", "Version", "Owner", "Assignee", "Current Phase", "Priority", "Due", "RAG", "Status", "Progress"];
  let html = "<table><thead><tr>" + header.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>";
  rows.forEach((r) => {
    const project = state.projects.find((p) => p.project_id === r.project_id);
    html += `<tr>
      <td>${project?.project_name || "–"}</td>
      <td>${project?.sponsor || "–"}</td>
      <td>${r.solution_name || "–"}</td>
      <td>${r.version || "–"}</td>
      <td>${r.owner || "–"}</td>
      <td>${r.assignee || "–"}</td>
      <td>${phaseDisplayName(r.current_phase) || "–"}</td>
      <td>${r.priority ?? ""}</td>
      <td>${r.due_date || ""}</td>
      <td>${ragPill(r.rag_status, r.rag_source, r.rag_reason)}</td>
      <td>${formatStatus(r.status)}</td>
      <td>${solutionProgress(r)}%</td>
    </tr>`;
  });
  html += "</tbody></table>";
  els.masterTable.innerHTML = html;
}

function renderDashboard() {
  if (!els.dashboardCards) return;
  const solutions = filteredSolutions();
  const overdue = solutions.filter((s) => s.due_date && new Date(s.due_date) < new Date() && s.status !== "complete");
  const active = solutions.filter((s) => s.status === "active").length;
  const complete = solutions.filter((s) => s.status === "complete").length;
  const onHold = solutions.filter((s) => s.status === "on_hold").length;
  const noDue = solutions.filter((s) => !s.due_date).length;
  const avgPriority = solutions.length
    ? (solutions.reduce((acc, s) => acc + (s.priority ?? 0), 0) / solutions.length).toFixed(1)
    : "–";
  const cards = [
    { title: "Projects", value: state.projects.length },
    { title: "Solutions", value: state.solutions.length },
    { title: "Subcomponents", value: state.subcomponents.length },
    { title: "Overdue", value: overdue.length, meta: "Due date past" },
    { title: "Active", value: active },
    { title: "Complete", value: complete },
    { title: "On Hold", value: onHold },
    { title: "No Due Date", value: noDue },
    { title: "Avg Priority", value: avgPriority },
  ];
  els.dashboardCards.innerHTML = cards
    .map((c) => `<div class="card"><h3>${c.title}</h3><div class="value">${c.value}</div><div class="meta">${c.meta || ""}</div></div>`)
    .join("");
  if (els.projectsSummary) {
    if (!state.projects.length) {
      els.projectsSummary.innerHTML = "<h3>Projects</h3><p class='muted'>No data</p>";
    } else {
      const rows = state.projects
        .map((p) => `<tr><td>${p.project_name}</td><td>${p.name_abbreviation}</td><td>${p.sponsor || ""}</td><td>${formatStatus(p.status)}</td></tr>`)
        .join("");
      els.projectsSummary.innerHTML = `<h3>Projects</h3><div class="table"><table><thead><tr><th>Project</th><th>Abbrev</th><th>Sponsor</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    }
  }
  if (els.solutionsSummary) {
    if (!state.solutions.length) {
      els.solutionsSummary.innerHTML = "<h3>Solutions</h3><p class='muted'>No data</p>";
    } else {
      const rows = state.solutions
        .map((s) => {
          const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
          return `<tr><td>${s.solution_name}</td><td>${proj}</td><td>${s.version}</td><td>${s.owner || ""}</td><td>${s.assignee || ""}</td><td>${phaseDisplayName(s.current_phase) || "–"}</td><td>${s.due_date || ""}</td><td>${formatStatus(s.status)}</td></tr>`;
        })
        .join("");
      els.solutionsSummary.innerHTML = `<h3>Solutions</h3><div class="table"><table><thead><tr><th>Solution</th><th>Project</th><th>Version</th><th>Owner</th><th>Assignee</th><th>Phase</th><th>Due</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    }
  }
  if (els.attentionPanel) {
    if (!overdue.length) {
      els.attentionPanel.innerHTML = "<h3>Needs Attention</h3><p class='muted'>All clear</p>";
    } else {
      const items = overdue
        .slice(0, 6)
        .map((s) => {
          const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
          return `<tr><td>${s.solution_name}</td><td>${proj}</td><td>${s.owner || "—"}</td><td>${s.due_date}</td></tr>`;
        })
        .join("");
      els.attentionPanel.innerHTML = `<h3>Needs Attention</h3><div class="table"><table><thead><tr><th>Solution</th><th>Project</th><th>Owner</th><th>Due</th></tr></thead><tbody>${items}</tbody></table></div>`;
    }
  }
  if (els.upcomingPanel) {
    const upcoming = solutions
      .filter((s) => s.due_date)
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      .slice(0, 6);
    if (!upcoming.length) {
      els.upcomingPanel.innerHTML = "<h3>Upcoming</h3><p class='muted'>No upcoming items</p>";
    } else {
      const html = upcoming
        .map((s) => {
          const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
          const phaseName = phaseDisplayName(s.current_phase) || "No phase";
          return `<tr><td>${s.solution_name}</td><td>${proj}</td><td>${s.due_date}</td><td>${phaseName}</td></tr>`;
        })
        .join("");
      els.upcomingPanel.innerHTML = `<h3>Upcoming</h3><div class="table"><table><thead><tr><th>Solution</th><th>Project</th><th>Due</th><th>Phase</th></tr></thead><tbody>${html}</tbody></table></div>`;
    }
  }
}

function tableFrom(items, cols) {
  if (!items.length) return "<p class='muted'>No data</p>";
  const head = cols.map((c) => `<th>${c.replace("_", " ")}</th>`).join("");
  const body = items.map((row) => `<tr>${cols.map((c) => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function bindProjectForm() {
  if (!els.projectForm) return;
  els.projectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(els.projectForm);
    const id = data.get("project_id");
    if (!id) {
      alert("Select a project or use New to create one.");
      return;
    }
    const payload = {
      project_name: data.get("project_name"),
      name_abbreviation: data.get("name_abbreviation"),
      status: data.get("status"),
      description: data.get("description"),
      success_criteria: data.get("success_criteria") || null,
      sponsor: data.get("sponsor"),
    };
    try {
      markIgnoreRefresh("projects");
      const updated = await api(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      upsertById(state.projects, updated, "project_id");
      populateSelects();
      renderActiveView();
    } catch (err) {
      ignoreNextRefresh.delete("projects");
      alert(`Save failed: ${err.message}`);
    }
  });
  els.projectForm.addEventListener("reset", () => {
    els.projectForm.querySelector('[name="project_id"]').value = "";
  });
  if (els.newProjectBtn) {
    els.newProjectBtn.addEventListener("click", async () => {
      const data = new FormData(els.projectForm);
      const payload = {
        project_name: data.get("project_name"),
        name_abbreviation: data.get("name_abbreviation"),
        status: data.get("status"),
        description: data.get("description"),
        success_criteria: data.get("success_criteria") || null,
        sponsor: data.get("sponsor"),
      };
      try {
        markIgnoreRefresh("projects");
        const created = await api("/projects", { method: "POST", body: JSON.stringify(payload) });
        upsertById(state.projects, created, "project_id");
        populateSelects();
        els.projectForm.reset();
        els.projectForm.querySelector('[name="project_id"]').value = "";
        renderActiveView();
      } catch (err) {
        ignoreNextRefresh.delete("projects");
        alert(`Create failed: ${err.message}`);
      }
    });
  }
}

function renderProjects() {
  if (!els.projectList) return;
  let html = "<table><thead><tr><th>Project</th><th>Abbrev</th><th>Sponsor</th><th>Status</th></tr></thead><tbody>";
  state.projects.forEach((p) => {
    html += `<tr data-id="${p.project_id}"><td>${p.project_name}</td><td>${p.name_abbreviation}</td><td>${p.sponsor || ""}</td><td>${formatStatus(p.status)}</td></tr>`;
  });
  html += "</tbody></table>";
  els.projectList.innerHTML = html;
}

function bindSolutionForm() {
  if (!els.solutionForm) return;
  const ragSourceSelect = els.solutionForm.querySelector('[name="rag_source"]');
  if (ragSourceSelect) {
    ragSourceSelect.addEventListener("change", updateRagFormControls);
  }
  updateRagFormControls();

  const saveHandler = async () => {
    const data = new FormData(els.solutionForm);
    const id = data.get("solution_id");
    if (!id) {
      alert("Select a solution or use New to create one.");
      return;
    }
    const ragSource = data.get("rag_source") || "auto";
    const payload = {
      solution_name: data.get("solution_name"),
      version: data.get("version"),
      status: data.get("status"),
      rag_source: ragSource,
      priority: Number(data.get("priority") || 3),
      due_date: data.get("due_date") || null,
      current_phase: data.get("current_phase") || null,
      description: data.get("description"),
      success_criteria: data.get("success_criteria") || null,
      owner: data.get("owner"),
      assignee: data.get("assignee") || "",
      approver: data.get("approver") || null,
      key_stakeholder: data.get("key_stakeholder"),
      blockers: data.get("blockers") || null,
      risks: data.get("risks") || null,
    };
    if (ragSource === "manual") {
      payload.rag_status = data.get("rag_status") || "amber";
      payload.rag_reason = data.get("rag_reason") || "";
    } else {
      delete payload.rag_status;
      delete payload.rag_reason;
    }
    try {
      markIgnoreRefresh("solutions");
      const updated = await api(`/solutions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      upsertById(state.solutions, updated, "solution_id");
      populateSelects();
      if (els.solutionForm?.querySelector('[name="solution_id"]')?.value === updated.solution_id) {
        els.solutionForm.querySelector('[name="status"]').value = updated.status || "";
        els.solutionForm.querySelector('[name="rag_source"]').value = updated.rag_source || "auto";
        els.solutionForm.querySelector('[name="rag_status"]').value = updated.rag_status || "amber";
        els.solutionForm.querySelector('[name="rag_reason"]').value = updated.rag_reason || "";
        els.solutionForm.querySelector('[name="priority"]').value = updated.priority ?? "";
        els.solutionForm.querySelector('[name="due_date"]').value = updated.due_date || "";
        updateCurrentPhaseOptions(updated.solution_id);
        els.solutionForm.querySelector('[name="current_phase"]').value = updated.current_phase || "";
        els.solutionForm.querySelector('[name="success_criteria"]').value = updated.success_criteria || "";
        updateRagFormControls();
      }
      renderActiveView();
    } catch (err) {
      ignoreNextRefresh.delete("solutions");
      alert(`Save failed: ${err.message}`);
    }
  };

  els.solutionForm.addEventListener("submit", (e) => {
    e.preventDefault();
    saveHandler();
  });
  els.solutionForm.addEventListener("reset", () => {
    els.solutionForm.querySelector('[name="solution_id"]').value = "";
    els.solutionForm.querySelector('[name="rag_source"]').value = "auto";
    els.solutionForm.querySelector('[name="rag_status"]').value = "amber";
    els.solutionForm.querySelector('[name="rag_reason"]').value = "";
    updateRagFormControls();
    updateCurrentPhaseOptions("");
    renderSolutionPhases();
  });
  if (els.newSolutionBtn) {
    els.newSolutionBtn.addEventListener("click", async () => {
      const data = new FormData(els.solutionForm);
      const projectId = data.get("project_id");
      const ragSource = data.get("rag_source") || "auto";
      const payload = {
        solution_name: data.get("solution_name"),
        version: data.get("version"),
        status: data.get("status"),
        rag_source: ragSource,
        priority: Number(data.get("priority") || 3),
        due_date: data.get("due_date") || null,
        current_phase: data.get("current_phase") || null,
        description: data.get("description"),
        success_criteria: data.get("success_criteria") || null,
        owner: data.get("owner"),
        assignee: data.get("assignee") || "",
	        approver: data.get("approver") || null,
	        key_stakeholder: data.get("key_stakeholder"),
	        blockers: data.get("blockers") || null,
	        risks: data.get("risks") || null,
	      };
      if (ragSource === "manual") {
        payload.rag_status = data.get("rag_status") || "amber";
        payload.rag_reason = data.get("rag_reason") || "";
      } else {
        delete payload.rag_status;
        delete payload.rag_reason;
      }
		      if (!projectId) {
		        alert("Select a project to create a solution.");
		        return;
      }
      try {
        markIgnoreRefresh("solutions");
        const created = await api(`/projects/${projectId}/solutions`, { method: "POST", body: JSON.stringify(payload) });
        upsertById(state.solutions, created, "solution_id");
        populateSelects();
        els.solutionForm.reset();
        els.solutionForm.querySelector('[name="solution_id"]').value = "";
        renderSolutionPhases();
        renderActiveView();
      } catch (err) {
        ignoreNextRefresh.delete("solutions");
        alert(`Create failed: ${err.message}`);
      }
    });
  }
}

function renderSolutions() {
  if (!els.solutionList) return;
  const projectMap = new Map(state.projects.map((p) => [p.project_id, p]));
  let html =
    "<table><thead><tr><th>Solution</th><th>Project</th><th>Version</th><th>Owner</th><th>Assignee</th><th>Phase</th><th>Due</th><th>RAG</th><th>Status</th></tr></thead><tbody>";
  state.solutions.forEach((s) => {
    const proj = projectMap.get(s.project_id);
    html += `<tr data-id="${s.solution_id}"><td>${s.solution_name}</td><td>${proj?.project_name || ""}</td><td>${s.version}</td><td>${s.owner || ""}</td><td>${s.assignee || ""}</td><td>${phaseDisplayName(s.current_phase) || "–"}</td><td>${s.due_date || ""}</td><td>${ragPill(s.rag_status, s.rag_source, s.rag_reason)}</td><td>${formatStatus(s.status)}</td></tr>`;
  });
  html += "</tbody></table>";
  els.solutionList.innerHTML = html;
  const selectedSolutionId = els.solutionForm?.querySelector('[name="solution_id"]')?.value || "";
  renderSolutionPhases(selectedSolutionId);
}

async function renderSolutionPhases(selectedId) {
  if (!els.phasesTable) return;
  const solutionId = selectedId || els.solutionForm?.querySelector('[name="solution_id"]')?.value || "";
  if (!solutionId) {
    els.phasesTable.innerHTML = "<p class='muted'>Select a solution to edit phases.</p>";
    return;
  }

  if (!state.solutionPhases[solutionId]) {
    els.phasesTable.innerHTML = "<p class='muted'>Loading phases…</p>";
    try {
      state.solutionPhases[solutionId] = await api(`/solutions/${solutionId}/phases`);
    } catch (err) {
      alert(`Load failed: ${err.message}`);
      return;
    }
  }
  updateCurrentPhaseOptions(solutionId);

  const enabled = new Set((state.solutionPhases[solutionId] || []).filter((p) => p.is_enabled).map((p) => p.phase_id));
  const grouped = {};
  state.phases.forEach((p) => {
    grouped[p.phase_group] = grouped[p.phase_group] || [];
    grouped[p.phase_group].push(p);
  });
  const groupHtml = Object.entries(grouped)
    .map(([groupName, phases]) => {
      const cards = phases
        .map((p) => {
          const checked = enabled.has(p.phase_id) ? "checked" : "";
          return `<div class="phase-cell">
            <div class="phase-title">${phaseDisplayName(p.phase_id)}</div>
            <div class="phase-meta">${groupName}</div>
            <label class="phase-toggle">
              <input type="checkbox" data-phase-id="${p.phase_id}" ${checked}>
              <span>Enabled</span>
            </label>
          </div>`;
        })
        .join("");
      return `<div class="phase-group"><div class="phase-group-title">${groupName}</div><div class="phase-grid">${cards}</div></div>`;
    })
    .join("");
  els.phasesTable.innerHTML = groupHtml;
  els.phasesTable.querySelectorAll('input[data-phase-id]').forEach((box) => {
    box.addEventListener("change", async () => {
      const phases = state.phases.map((ph) => ({
        phase_id: ph.phase_id,
        is_enabled: !!els.phasesTable.querySelector(`input[data-phase-id="${ph.phase_id}"]`)?.checked,
      }));
      try {
        markIgnoreRefresh("solutions");
        await api(`/solutions/${solutionId}/phases`, { method: "POST", body: JSON.stringify({ phases }) });
        const [updated, updatedSolution] = await Promise.all([
          api(`/solutions/${solutionId}/phases`),
          api(`/solutions/${solutionId}`),
        ]);
        state.solutionPhases[solutionId] = updated;
        const idx = state.solutions.findIndex((s) => s.solution_id === solutionId);
        if (idx !== -1) state.solutions[idx] = updatedSolution;

        updateCurrentPhaseOptions(solutionId);
        if (els.solutionForm?.querySelector('[name="solution_id"]')?.value === solutionId) {
          els.solutionForm.querySelector('[name="current_phase"]').value = updatedSolution.current_phase || "";
        }
        renderSolutionPhases(solutionId);
        renderMasterTable();
        renderDashboard();
        renderKanban();
        renderCalendar();
      } catch (err) {
        ignoreNextRefresh.delete("solutions");
        alert(`Save failed: ${err.message}`);
      }
    });
  });
}

function bindSubcomponentForm() {
  if (!els.subcomponentForm) return;
  els.subcomponentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(els.subcomponentForm);
    const id = data.get("subcomponent_id");
    if (!id) {
      alert("Select a subcomponent or use New to create one.");
      return;
    }
    const payload = {
      subcomponent_name: data.get("subcomponent_name"),
      status: data.get("status"),
      priority: Number(data.get("priority") || 3),
      due_date: data.get("due_date") || null,
      assignee: data.get("assignee"),
    };
    try {
      markIgnoreRefresh("subcomponents");
      const updated = await api(`/subcomponents/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      upsertById(state.subcomponents, updated, "subcomponent_id");
      renderActiveView();
    } catch (err) {
      ignoreNextRefresh.delete("subcomponents");
      alert(`Save failed: ${err.message}`);
    }
  });
  els.subcomponentForm.addEventListener("reset", () => {
    els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = "";
  });
  const projectSelect = els.subcomponentForm.querySelector('[name="project_id"]');
  projectSelect?.addEventListener("change", () => {
    const solSel = els.subcomponentForm.querySelector('[name="solution_id"]');
    if (solSel) solSel.value = "";
    updateSubcomponentSolutionOptions(projectSelect.value || "");
  });
  if (els.newSubcomponentBtn) {
    els.newSubcomponentBtn.addEventListener("click", async () => {
      const data = new FormData(els.subcomponentForm);
      const solutionId = data.get("solution_id");
      const projectId = data.get("project_id");
      const name = data.get("subcomponent_name");
      const assignee = data.get("assignee");
      if (!projectId || !solutionId || !name || !assignee) {
        alert("Project, solution, task name, and assignee are required to create.");
        return;
      }
      const payload = {
        subcomponent_name: name,
        status: data.get("status"),
        priority: Number(data.get("priority") || 3),
        due_date: data.get("due_date") || null,
        assignee,
      };
      try {
        markIgnoreRefresh("subcomponents");
        const created = await api(`/solutions/${solutionId}/subcomponents`, { method: "POST", body: JSON.stringify(payload) });
        upsertById(state.subcomponents, created, "subcomponent_id");
        els.subcomponentForm.reset();
        els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = "";
        renderActiveView();
      } catch (err) {
        ignoreNextRefresh.delete("subcomponents");
        alert(`Create failed: ${err.message}`);
      }
    });
  }
}

function renderSubcomponents() {
  if (!els.subcomponentList) return;
  const projectMap = new Map(state.projects.map((p) => [p.project_id, p.project_name]));
  const solutionMap = new Map(state.solutions.map((s) => [s.solution_id, s.solution_name]));
  let html =
    "<table><thead><tr><th>Task</th><th>Project</th><th>Solution</th><th>Assignee</th><th>Status</th><th>Priority</th><th>Due</th></tr></thead><tbody>";
  state.subcomponents.forEach((s) => {
    html += `<tr data-id="${s.subcomponent_id}"><td>${s.subcomponent_name}</td><td>${projectMap.get(s.project_id) || ""}</td><td>${solutionMap.get(s.solution_id) || ""}</td><td>${s.assignee || ""}</td><td>${formatStatus(s.status)}</td><td>${s.priority ?? ""}</td><td>${s.due_date || ""}</td></tr>`;
  });
  html += "</tbody></table>";
  els.subcomponentList.innerHTML = html;
}

function populateSelects() {
  const projectOpts = state.projects.map((p) => `<option value="${p.project_id}">${p.project_name}</option>`).join("");
  const projSelects = [
    els.solutionForm?.querySelector('[name="project_id"]'),
    els.subcomponentForm?.querySelector('[name="project_id"]'),
  ].filter(Boolean);
  projSelects.forEach((sel) => (sel.innerHTML = `<option value="">Select</option>${projectOpts}`));
  if (els.subcomponentForm) {
    const scProjectId = els.subcomponentForm.querySelector('[name="project_id"]')?.value || "";
    updateSubcomponentSolutionOptions(scProjectId);
  }
  if (els.solutionForm) {
    const projSel = els.solutionForm.querySelector('[name="project_id"]');
    if (projSel && projSel.innerHTML.indexOf("Select") === -1) {
      projSel.innerHTML = `<option value="">Select</option>${projectOpts}`;
    }
    updateCurrentPhaseOptions(els.solutionForm.querySelector('[name="solution_id"]')?.value || "");
  }
}

function updateSubcomponentSolutionOptions(projectId) {
  const solSel = els.subcomponentForm?.querySelector('[name="solution_id"]');
  if (!solSel) return;
  if (!projectId) {
    solSel.innerHTML = `<option value="">Select project first</option>`;
    return;
  }
  const filteredSolutions = state.solutions.filter((s) => s.project_id === projectId);
  const solutionOpts = filteredSolutions.map((s) => `<option value="${s.solution_id}">${s.solution_name}</option>`).join("");
  solSel.innerHTML = `<option value="">Select</option>${solutionOpts}`;
}

function renderKanban() {
  if (!els.kanbanBoard) return;
  const list = filteredSolutions();
  const phaseGroups = Array.from(
    new Set(state.phases.sort((a, b) => a.sequence - b.sequence).map((p) => p.phase_group))
  );

  // group solutions by project
  const byProject = {};
  list.forEach((s) => {
    const pid = s.project_id || "none";
    byProject[pid] = byProject[pid] || [];
    byProject[pid].push(s);
  });

  let html = "";
  Object.entries(byProject).forEach(([pid, items]) => {
    const projName = state.projects.find((p) => p.project_id === pid)?.project_name || "Unassigned Project";
    html += `<div class="kanban-project"><div class="kanban-project-title">${projName} <span class="pill">${items.length}</span></div>`;
    html += renderSolutionSwimlane(items, phaseGroups);
    html += `</div>`;
  });

  els.kanbanBoard.innerHTML = html || "<p class='muted'>No items</p>";
}

function renderSolutionSwimlane(items, phaseGroups) {
  let html = `<div class="kanban-swimlane">`;
  phaseGroups.forEach((g) => {
    const groupCards = items.filter((s) => {
      const phase = state.phases.find((p) => p.phase_id === s.current_phase);
      return (phase?.phase_group || "Unassigned") === g;
    });
    html += `<div class="kanban-column"><h4>${g}</h4>${renderSolutionCards(groupCards)}</div>`;
  });
  // handle unassigned if any
  const unassigned = items.filter((s) => !s.current_phase || !state.phases.find((p) => p.phase_id === s.current_phase));
  if (unassigned.length) {
    html += `<div class="kanban-column"><h4>Unassigned</h4>${renderSolutionCards(unassigned)}</div>`;
  }
  html += `</div>`;
  return html;
}

function renderSolutionCards(cards) {
  if (!cards.length) return "<p class='muted'>Empty</p>";
  return cards
    .map((s) => {
      const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
      const phaseLabel = phaseDisplayName(s.current_phase) || "No phase";
      return `<div class="kanban-card"><strong>${s.solution_name}</strong><div class="meta">${proj}${s.version ? " • " + s.version : ""}</div><div class="meta">Owner ${s.owner || "—"} • Assignee ${s.assignee || "—"}</div><div class="meta">P${s.priority ?? ""} • ${phaseLabel}</div><div class="meta">Due ${s.due_date || "—"} • ${formatStatus(s.status)}</div></div>`;
    })
    .join("");
}

function renderCalendar() {
  if (!els.calendarGrid) return;
  const byDay = {};
  filteredSolutions().forEach((s) => {
    if (!s.due_date) return;
    byDay[s.due_date] = byDay[s.due_date] || [];
    byDay[s.due_date].push(s);
  });
  const entries = Object.entries(byDay).sort(([a], [b]) => new Date(a) - new Date(b));
  if (!entries.length) {
    els.calendarGrid.innerHTML = "<p class='muted'>No due dates</p>";
    return;
  }
  let html = "";
  entries.forEach(([day, items]) => {
    html += `<div class="calendar-day"><strong>${day}</strong>${items
      .map((i) => `<div>${i.solution_name} (${formatStatus(i.status)}) • Owner ${i.owner || "—"} • Assignee ${i.assignee || "—"}</div>`)
      .join("")}</div>`;
  });
  els.calendarGrid.innerHTML = html;
}

async function downloadCsv(kind, filename, resultEl) {
  try {
    const res = await fetch(`${API_BASE}/${kind}/export`, { credentials: "include" });
    if (res.status === 401) {
      handleAuthError({ status: 401 });
      setImportResult(resultEl, "Sign in required", true);
      return;
    }
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setImportResult(resultEl, `Downloaded ${filename}`);
  } catch (err) {
    setImportResult(resultEl, `Download failed: ${err.message}`, true);
  }
}

async function uploadCsv(kind, fileInput, resultEl) {
  const file = fileInput?.files?.[0];
  if (!file) {
    setImportResult(resultEl, "Choose a CSV file first", true);
    return;
  }
  try {
    const csvText = await file.text();
    const res = await fetch(`${API_BASE}/${kind}/import`, {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: csvText,
      credentials: "include",
    });
    if (res.status === 401) {
      handleAuthError({ status: 401 });
      setImportResult(resultEl, "Sign in required", true);
      return;
    }
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const errs = data.errors || [];
    const parts = [
      `Created ${data.created || 0}`,
      `Updated ${data.updated || 0}`,
    ];
    if (data.projects_created !== undefined) parts.push(`Projects created ${data.projects_created}`);
    if (data.solutions_created !== undefined) parts.push(`Solutions created ${data.solutions_created}`);
    const msg = parts.join(", ");
    const errorSnippet = errs.length ? ` Errors (${errs.length}): ${errs.slice(0, 3).join(" | ")}` : "";
    setImportResult(
      resultEl,
      errs.length ? `${msg}.${errorSnippet}` : msg,
      errs.length > 0
    );
    if (errs.length) console.warn("Import errors:", errs);
    await loadData();
  } catch (err) {
    setImportResult(resultEl, `Import failed: ${err.message}`, true);
  } finally {
    if (fileInput) fileInput.value = "";
  }
}

function bindCsvControls() {
  if (els.projectsDownload) {
    els.projectsDownload.addEventListener("click", () =>
      downloadCsv("projects", "projects.csv", els.projectsImportResult)
    );
  }
  if (els.projectsUpload && els.projectsFile) {
    els.projectsUpload.addEventListener("click", () => els.projectsFile?.click());
    els.projectsFile.addEventListener("change", () =>
      uploadCsv("projects", els.projectsFile, els.projectsImportResult)
    );
  }

  if (els.solutionsDownload) {
    els.solutionsDownload.addEventListener("click", () =>
      downloadCsv("solutions", "solutions.csv", els.solutionsImportResult)
    );
  }
  if (els.solutionsUpload && els.solutionsFile) {
    els.solutionsUpload.addEventListener("click", () => els.solutionsFile?.click());
    els.solutionsFile.addEventListener("change", () =>
      uploadCsv("solutions", els.solutionsFile, els.solutionsImportResult)
    );
  }

  if (els.subcomponentsDownload) {
    els.subcomponentsDownload.addEventListener("click", () =>
      downloadCsv("subcomponents", "subcomponents.csv", els.subcomponentsImportResult)
    );
  }
  if (els.subcomponentsUpload && els.subcomponentsFile) {
    els.subcomponentsUpload.addEventListener("click", () => els.subcomponentsFile?.click());
    els.subcomponentsFile.addEventListener("change", () =>
      uploadCsv("subcomponents", els.subcomponentsFile, els.subcomponentsImportResult)
    );
  }
}

function bindProjectListClicks() {
  if (!els.projectList || !els.projectForm) return;
  els.projectList.addEventListener("click", (e) => {
    const row = e.target.closest("tr[data-id]");
    if (!row) return;
    const proj = state.projects.find((p) => p.project_id === row.dataset.id);
    if (!proj) return;
    els.projectForm.querySelector('[name="project_id"]').value = proj.project_id;
    els.projectForm.querySelector('[name="project_name"]').value = proj.project_name;
    els.projectForm.querySelector('[name="name_abbreviation"]').value = proj.name_abbreviation;
    els.projectForm.querySelector('[name="status"]').value = proj.status;
    els.projectForm.querySelector('[name="description"]').value = proj.description || "";
    els.projectForm.querySelector('[name="success_criteria"]').value = proj.success_criteria || "";
    els.projectForm.querySelector('[name="sponsor"]').value = proj.sponsor || "";
  });
}

function bindSolutionListClicks() {
  if (!els.solutionList || !els.solutionForm) return;
  els.solutionList.addEventListener("click", (e) => {
    const row = e.target.closest("tr[data-id]");
    if (!row) return;
    const sol = state.solutions.find((s) => s.solution_id === row.dataset.id);
    if (!sol) return;
    els.solutionForm.querySelector('[name="solution_id"]').value = sol.solution_id;
    els.solutionForm.querySelector('[name="project_id"]').value = sol.project_id;
    els.solutionForm.querySelector('[name="solution_name"]').value = sol.solution_name;
    els.solutionForm.querySelector('[name="version"]').value = sol.version;
    els.solutionForm.querySelector('[name="status"]').value = sol.status;
    els.solutionForm.querySelector('[name="rag_source"]').value = sol.rag_source || "auto";
    els.solutionForm.querySelector('[name="rag_status"]').value = sol.rag_status || "amber";
    els.solutionForm.querySelector('[name="rag_reason"]').value = sol.rag_reason || "";
    els.solutionForm.querySelector('[name="priority"]').value = sol.priority ?? "";
    els.solutionForm.querySelector('[name="due_date"]').value = sol.due_date || "";
    els.solutionForm.querySelector('[name="description"]').value = sol.description || "";
    els.solutionForm.querySelector('[name="success_criteria"]').value = sol.success_criteria || "";
    els.solutionForm.querySelector('[name="owner"]').value = sol.owner || "";
    els.solutionForm.querySelector('[name="assignee"]').value = sol.assignee || "";
    els.solutionForm.querySelector('[name="approver"]').value = sol.approver || "";
    els.solutionForm.querySelector('[name="key_stakeholder"]').value = sol.key_stakeholder || "";
    els.solutionForm.querySelector('[name="blockers"]').value = sol.blockers || "";
    els.solutionForm.querySelector('[name="risks"]').value = sol.risks || "";
    updateCurrentPhaseOptions(sol.solution_id);
    els.solutionForm.querySelector('[name="current_phase"]').value = sol.current_phase || "";
    renderSolutionPhases(sol.solution_id);
    updateRagFormControls();
  });
}

function bindSubcomponentListClicks() {
  if (!els.subcomponentList || !els.subcomponentForm) return;
  els.subcomponentList.addEventListener("click", (e) => {
    const row = e.target.closest("tr[data-id]");
    if (!row) return;
    const sub = state.subcomponents.find((s) => s.subcomponent_id === row.dataset.id);
    if (!sub) return;
    els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = sub.subcomponent_id;
    els.subcomponentForm.querySelector('[name="project_id"]').value = sub.project_id;
    updateSubcomponentSolutionOptions(sub.project_id);
    els.subcomponentForm.querySelector('[name="solution_id"]').value = sub.solution_id;
    els.subcomponentForm.querySelector('[name="subcomponent_name"]').value = sub.subcomponent_name || "";
    els.subcomponentForm.querySelector('[name="priority"]').value = sub.priority ?? "";
    els.subcomponentForm.querySelector('[name="due_date"]').value = sub.due_date || "";
    els.subcomponentForm.querySelector('[name="status"]').value = sub.status;
    els.subcomponentForm.querySelector('[name="assignee"]').value = sub.assignee || "";
  });
}

function bindNav() {
  els.navButtons.forEach((btn) =>
    btn.addEventListener("click", () => {
      setView(btn.dataset.view);
    })
  );
}

function init() {
  initTheme();
  bindAuthUI();
  bindCsvControls();
  bindNav();
  bindProjectForm();
  bindSolutionForm();
  bindSubcomponentForm();
  bindProjectListClicks();
  bindSolutionListClicks();
  bindSubcomponentListClicks();
  setView(state.currentView);
  bootstrapAuth();
}

init();
