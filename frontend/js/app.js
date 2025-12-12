const API_BASE = "/api";

const els = {
  navButtons: document.querySelectorAll(".nav-btn[data-view]"),
  views: document.querySelectorAll(".view"),
  status: document.getElementById("connection-status"),
  themeToggle: document.getElementById("theme-toggle"),
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
  phases: [],
  projects: [],
  solutions: [],
  solutionPhases: {}, // solution_id -> phases
  subcomponents: [],
  filters: {},
  currentView: "master",
  theme: "dark",
};

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

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function loadData() {
  try {
    setStatus("Loading...", "warn");
    state.phases = await api("/phases");
    state.projects = await api("/projects");

    const solutions = [];
    for (const proj of state.projects) {
      const sols = await api(`/projects/${proj.project_id}/solutions`);
      solutions.push(...sols);
    }
    state.solutions = solutions;

    state.solutionPhases = {};
    for (const sol of state.solutions) {
      const sp = await api(`/solutions/${sol.solution_id}/phases`);
      state.solutionPhases[sol.solution_id] = sp;
    }

    const subs = [];
    for (const sol of state.solutions) {
      const list = await api(`/solutions/${sol.solution_id}/subcomponents`);
      subs.push(...list);
    }
    state.subcomponents = subs;

    if (!state.projects.length && !state.solutions.length && !state.subcomponents.length) {
      setStatus("No data loaded", "warn");
      alert("No data loaded. Create a project/solution/subcomponent to begin.");
    } else {
      setStatus("Online", "positive");
    }
    render();
  } catch (err) {
    console.error(err);
    setStatus("Error", "danger");
  }
}

function setView(view) {
  state.currentView = view;
  els.views.forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  els.navButtons.forEach((b) => b.classList.toggle("active", b.dataset.view === view));
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

function render() {
  renderMasterFilters();
  renderMasterTable();
  renderDashboard();
  renderProjects();
  renderSolutions();
  renderSubcomponents();
  renderKanban();
  renderCalendar();
}

function renderMasterFilters() {
  const root = els.masterFilters;
  if (!root) return;
  const projectOpts = state.projects.map((p) => `<option value="${p.project_id}">${p.project_name}</option>`).join("");
  const solutionOpts = state.solutions.map((s) => `<option value="${s.solution_id}">${s.solution_name}</option>`).join("");
  const phaseOpts = state.phases.map((p) => `<option value="${p.phase_id}">${p.phase_name}</option>`).join("");
  root.innerHTML = `
    <label>Status
      <select data-filter="status">
        <option value="">Any</option>
        <option value="to_do">To do</option>
        <option value="in_progress">In progress</option>
        <option value="on_hold">On hold</option>
        <option value="complete">Complete</option>
        <option value="abandoned">Abandoned</option>
      </select>
    </label>
    <label>Project
      <select data-filter="project_id"><option value="">Any</option>${projectOpts}</select>
    </label>
    <label>Solution
      <select data-filter="solution_id"><option value="">Any</option>${solutionOpts}</select>
    </label>
    <label>Subphase
      <select data-filter="sub_phase"><option value="">Any</option>${phaseOpts}</select>
    </label>
    <label>Priority ≤ <input type="number" data-filter="priority" min="0" max="5" /></label>
    <label>Search <input type="text" data-filter="search" placeholder="Name or description" /></label>
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

function filteredSubcomponents() {
  const f = state.filters || {};
  return state.subcomponents.filter((s) => {
    if (f.status && s.status !== f.status) return false;
    if (f.project_id && s.project_id !== f.project_id) return false;
    if (f.solution_id && s.solution_id !== f.solution_id) return false;
    if (f.sub_phase && s.sub_phase !== f.sub_phase) return false;
    if (f.priority && Number(s.priority) > Number(f.priority)) return false;
    if (f.search) {
      const text = `${s.subcomponent_name || ""} ${s.description || ""}`.toLowerCase();
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

function progress(sub) {
  if (sub.status === "complete") return 100;
  const phases = orderedPhases(sub.solution_id);
  if (!phases.length || !sub.sub_phase) return 0;
  const idx = phases.findIndex((p) => p.phase_id === sub.sub_phase);
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

function renderMasterTable() {
  if (!els.masterTable) return;
  const rows = filteredSubcomponents();
  const header = ["Project", "Solution", "Name", "Subphase", "Priority", "Due", "Status", "Progress"];
  let html = "<table><thead><tr>" + header.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>";
  rows.forEach((r) => {
    const project = state.projects.find((p) => p.project_id === r.project_id);
    const solution = state.solutions.find((s) => s.solution_id === r.solution_id);
    html += `<tr>
      <td>${project?.project_name || "–"}</td>
      <td>${solution?.solution_name || "–"}</td>
      <td>${r.subcomponent_name || "Untitled"}</td>
      <td>${r.sub_phase || "–"}</td>
      <td>${r.priority ?? ""}</td>
      <td>${r.due_date || ""}</td>
      <td>${formatStatus(r.status)}</td>
      <td>${progress(r)}%</td>
    </tr>`;
  });
  html += "</tbody></table>";
  els.masterTable.innerHTML = html;
}

function renderDashboard() {
  if (!els.dashboardCards) return;
  const subs = filteredSubcomponents();
  const overdue = subs.filter((s) => s.due_date && new Date(s.due_date) < new Date());
  const inProgress = subs.filter((s) => s.status === "in_progress").length;
  const complete = subs.filter((s) => s.status === "complete").length;
  const onHold = subs.filter((s) => s.status === "on_hold").length;
  const noDue = subs.filter((s) => !s.due_date).length;
  const avgPriority = subs.length ? (subs.reduce((acc, s) => acc + (s.priority ?? 0), 0) / subs.length).toFixed(1) : "–";
  const cards = [
    { title: "Projects", value: state.projects.length },
    { title: "Solutions", value: state.solutions.length },
    { title: "Subcomponents", value: subs.length },
    { title: "Overdue", value: overdue.length, meta: "Due date past" },
    { title: "In Progress", value: inProgress },
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
        .map((p) => `<tr><td>${p.project_name}</td><td>${p.name_abbreviation}</td><td>${formatStatus(p.status)}</td></tr>`)
        .join("");
      els.projectsSummary.innerHTML = `<h3>Projects</h3><div class="table"><table><thead><tr><th>Project</th><th>Abbrev</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    }
  }
  if (els.solutionsSummary) {
    if (!state.solutions.length) {
      els.solutionsSummary.innerHTML = "<h3>Solutions</h3><p class='muted'>No data</p>";
    } else {
      const rows = state.solutions
        .map((s) => {
          const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
          return `<tr><td>${s.solution_name}</td><td>${proj}</td><td>${s.version}</td><td>${formatStatus(s.status)}</td></tr>`;
        })
        .join("");
      els.solutionsSummary.innerHTML = `<h3>Solutions</h3><div class="table"><table><thead><tr><th>Solution</th><th>Project</th><th>Version</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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
          const sol = state.solutions.find((p) => p.solution_id === s.solution_id)?.solution_name || "";
          return `<tr><td>${s.subcomponent_name}</td><td>${proj}</td><td>${sol}</td><td>${s.due_date}</td></tr>`;
        })
        .join("");
      els.attentionPanel.innerHTML = `<h3>Needs Attention</h3><div class="table"><table><thead><tr><th>Name</th><th>Project</th><th>Solution</th><th>Due</th></tr></thead><tbody>${items}</tbody></table></div>`;
    }
  }
  if (els.upcomingPanel) {
    const upcoming = subs
      .filter((s) => s.due_date)
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      .slice(0, 6);
    if (!upcoming.length) {
      els.upcomingPanel.innerHTML = "<h3>Upcoming</h3><p class='muted'>No upcoming items</p>";
    } else {
      const html = upcoming
        .map((s) => {
          const proj = state.projects.find((p) => p.project_id === s.project_id)?.project_name || "";
          const sol = state.solutions.find((p) => p.solution_id === s.solution_id)?.solution_name || "";
          const phaseName = state.phases.find((p) => p.phase_id === s.sub_phase)?.phase_name || s.sub_phase || "No phase";
          return `<tr><td>${s.subcomponent_name}</td><td>${proj}</td><td>${sol}</td><td>${s.due_date}</td><td>${phaseName}</td></tr>`;
        })
        .join("");
      els.upcomingPanel.innerHTML = `<h3>Upcoming</h3><div class="table"><table><thead><tr><th>Name</th><th>Project</th><th>Solution</th><th>Due</th><th>Phase</th></tr></thead><tbody>${html}</tbody></table></div>`;
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
    };
    try {
      await api(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await loadData();
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
  });
  els.projectForm.addEventListener("reset", () => {
    els.projectForm.querySelector('[name="project_id"]').value = "";
  });
  if (els.newProjectBtn) {
    els.newProjectBtn.addEventListener("click", () => {
      const data = new FormData(els.projectForm);
      const payload = {
        project_name: data.get("project_name"),
        name_abbreviation: data.get("name_abbreviation"),
        status: data.get("status"),
        description: data.get("description"),
      };
      api("/projects", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
          els.projectForm.reset();
          els.projectForm.querySelector('[name="project_id"]').value = "";
          loadData();
        })
        .catch((err) => alert(`Create failed: ${err.message}`));
    });
  }
}

function renderProjects() {
  if (!els.projectList) return;
  let html = "<table><thead><tr><th>Project</th><th>Abbrev</th><th>Status</th></tr></thead><tbody>";
  state.projects.forEach((p) => {
    html += `<tr data-id="${p.project_id}"><td>${p.project_name}</td><td>${p.name_abbreviation}</td><td>${formatStatus(p.status)}</td></tr>`;
  });
  html += "</tbody></table>";
  els.projectList.innerHTML = html;
  els.projectList.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const proj = state.projects.find((p) => p.project_id === row.dataset.id);
      if (!proj) return;
      els.projectForm.querySelector('[name="project_id"]').value = proj.project_id;
      els.projectForm.querySelector('[name="project_name"]').value = proj.project_name;
      els.projectForm.querySelector('[name="name_abbreviation"]').value = proj.name_abbreviation;
      els.projectForm.querySelector('[name="status"]').value = proj.status;
      els.projectForm.querySelector('[name="description"]').value = proj.description || "";
    });
  });
  populateSelects();
}

function bindSolutionForm() {
  if (!els.solutionForm) return;
  const saveHandler = async () => {
    const data = new FormData(els.solutionForm);
    const id = data.get("solution_id");
    const projectId = data.get("project_id");
    if (!id) {
      alert("Select a solution or use New to create one.");
      return;
    }
    const payload = {
      solution_name: data.get("solution_name"),
      version: data.get("version"),
      status: data.get("status"),
      description: data.get("description"),
    };
    try {
      await api(`/solutions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await loadData();
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
  };

  els.solutionForm.addEventListener("submit", (e) => {
    e.preventDefault();
    saveHandler();
  });
  els.solutionForm.addEventListener("reset", () => {
    els.solutionForm.querySelector('[name="solution_id"]').value = "";
    renderSolutionPhases();
  });
  if (els.newSolutionBtn) {
    els.newSolutionBtn.addEventListener("click", () => {
      const data = new FormData(els.solutionForm);
      const projectId = data.get("project_id");
      const payload = {
        solution_name: data.get("solution_name"),
        version: data.get("version"),
        status: data.get("status"),
        description: data.get("description"),
      };
      if (!projectId) {
        alert("Select a project to create a solution.");
        return;
      }
      api(`/projects/${projectId}/solutions`, { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
          els.solutionForm.reset();
          els.solutionForm.querySelector('[name="solution_id"]').value = "";
          renderSolutionPhases();
          loadData();
        })
        .catch((err) => alert(`Create failed: ${err.message}`));
    });
  }
}

function renderSolutions() {
  if (!els.solutionList) return;
  let html = "<table><thead><tr><th>Solution</th><th>Project</th><th>Version</th><th>Status</th></tr></thead><tbody>";
  state.solutions.forEach((s) => {
    const proj = state.projects.find((p) => p.project_id === s.project_id);
    html += `<tr data-id="${s.solution_id}"><td>${s.solution_name}</td><td>${proj?.project_name || ""}</td><td>${s.version}</td><td>${formatStatus(s.status)}</td></tr>`;
  });
  html += "</tbody></table>";
  els.solutionList.innerHTML = html;
  els.solutionList.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const sol = state.solutions.find((s) => s.solution_id === row.dataset.id);
      if (!sol) return;
      els.solutionForm.querySelector('[name="solution_id"]').value = sol.solution_id;
      els.solutionForm.querySelector('[name="project_id"]').value = sol.project_id;
      els.solutionForm.querySelector('[name="solution_name"]').value = sol.solution_name;
      els.solutionForm.querySelector('[name="version"]').value = sol.version;
      els.solutionForm.querySelector('[name="status"]').value = sol.status;
      els.solutionForm.querySelector('[name="description"]').value = sol.description || "";
      renderSolutionPhases(sol.solution_id);
    });
  });
  renderSolutionPhases(); // reset
}

function renderSolutionPhases(selectedId) {
  if (!els.phasesTable) return;
  const solutionId = selectedId || els.solutionForm?.querySelector('[name="solution_id"]')?.value || "";
  if (!solutionId) {
    els.phasesTable.innerHTML = "<p class='muted'>Select a solution to edit phases.</p>";
    return;
  }
  const enabled = new Set((state.solutionPhases[solutionId] || []).filter((p) => p.is_enabled).map((p) => p.phase_id));
  let html = "<table><thead><tr><th>Phase</th><th>Enabled</th></tr></thead><tbody>";
  state.phases.forEach((p) => {
    const checked = enabled.has(p.phase_id) ? "checked" : "";
    html += `<tr><td>${p.phase_name} <span class="muted">(${p.phase_group})</span></td><td><input type="checkbox" data-phase-id="${p.phase_id}" ${checked}></td></tr>`;
  });
  html += "</tbody></table>";
  els.phasesTable.innerHTML = html;
  els.phasesTable.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    box.addEventListener("change", async () => {
      const phases = state.phases.map((ph) => ({
        phase_id: ph.phase_id,
        is_enabled: !!els.phasesTable.querySelector(`input[data-phase-id="${ph.phase_id}"]`)?.checked,
      }));
      try {
        await api(`/solutions/${solutionId}/phases`, { method: "POST", body: JSON.stringify({ phases }) });
        await loadData();
      } catch (err) {
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
    const solutionId = data.get("solution_id");
    if (!id) {
      alert("Select a subcomponent or use New to create one.");
      return;
    }
    const payload = {
      subcomponent_name: data.get("subcomponent_name"),
      status: data.get("status"),
      priority: Number(data.get("priority") || 0),
      due_date: data.get("due_date") || null,
      sub_phase: data.get("sub_phase") || null,
      description: data.get("description") || null,
      notes: data.get("notes") || null,
    };
    try {
      await api(`/subcomponents/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await loadData();
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
  });
  els.subcomponentForm.addEventListener("reset", () => {
    els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = "";
  });
  els.subcomponentForm.querySelector('[name="solution_id"]')?.addEventListener("change", updateSubphaseOptions);
  const projectSelect = els.subcomponentForm.querySelector('[name="project_id"]');
  projectSelect?.addEventListener("change", () => {
    const solSel = els.subcomponentForm.querySelector('[name="solution_id"]');
    if (solSel) solSel.value = "";
    updateSubcomponentSolutionOptions(projectSelect.value || "");
  });
  if (els.newSubcomponentBtn) {
    els.newSubcomponentBtn.addEventListener("click", () => {
      const data = new FormData(els.subcomponentForm);
      const solutionId = data.get("solution_id");
      const projectId = data.get("project_id");
      const name = data.get("subcomponent_name");
      if (!projectId || !solutionId || !name) {
        alert("Project, solution, and name are required to create.");
        return;
      }
      const payload = {
        subcomponent_name: name,
        status: data.get("status"),
        priority: Number(data.get("priority") || 0),
        due_date: data.get("due_date") || null,
        sub_phase: data.get("sub_phase") || null,
        description: data.get("description") || null,
        notes: data.get("notes") || null,
      };
      api(`/solutions/${solutionId}/subcomponents`, { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
          els.subcomponentForm.reset();
          els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = "";
          loadData();
        })
        .catch((err) => alert(`Create failed: ${err.message}`));
    });
  }
}

function renderSubcomponents() {
  if (!els.subcomponentList) return;
  let html =
    "<table><thead><tr><th>Name</th><th>Project</th><th>Solution</th><th>Status</th><th>Priority</th></tr></thead><tbody>";
  state.subcomponents.forEach((s) => {
    const project = state.projects.find((p) => p.project_id === s.project_id);
    const solution = state.solutions.find((p) => p.solution_id === s.solution_id);
    html += `<tr data-id="${s.subcomponent_id}"><td>${s.subcomponent_name}</td><td>${project?.project_name || ""}</td><td>${solution?.solution_name || ""}</td><td>${formatStatus(s.status)}</td><td>${s.priority ?? ""}</td></tr>`;
  });
  html += "</tbody></table>";
  els.subcomponentList.innerHTML = html;
  els.subcomponentList.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const sub = state.subcomponents.find((s) => s.subcomponent_id === row.dataset.id);
      if (!sub) return;
      els.subcomponentForm.querySelector('[name="subcomponent_id"]').value = sub.subcomponent_id;
      els.subcomponentForm.querySelector('[name="project_id"]').value = sub.project_id;
      updateSubcomponentSolutionOptions(sub.project_id);
      els.subcomponentForm.querySelector('[name="solution_id"]').value = sub.solution_id;
      updateSubphaseOptions();
      els.subcomponentForm.querySelector('[name="subcomponent_name"]').value = sub.subcomponent_name || "";
      els.subcomponentForm.querySelector('[name="priority"]').value = sub.priority ?? "";
      els.subcomponentForm.querySelector('[name="due_date"]').value = sub.due_date || "";
      els.subcomponentForm.querySelector('[name="status"]').value = sub.status;
      els.subcomponentForm.querySelector('[name="sub_phase"]').value = sub.sub_phase || "";
      els.subcomponentForm.querySelector('[name="description"]').value = sub.description || "";
      els.subcomponentForm.querySelector('[name="notes"]').value = sub.notes || "";
    });
  });
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
    const solutionOptsAll = state.solutions.map((s) => `<option value="${s.solution_id}">${s.solution_name}</option>`).join("");
    const projSel = els.solutionForm.querySelector('[name="project_id"]');
    if (projSel && projSel.innerHTML.indexOf("Select") === -1) {
      projSel.innerHTML = `<option value="">Select</option>${projectOpts}`;
    }
    // solutionForm does not need a solution select
  }
}

function updateSubcomponentSolutionOptions(projectId) {
  const solSel = els.subcomponentForm?.querySelector('[name="solution_id"]');
  if (!solSel) return;
  if (!projectId) {
    solSel.innerHTML = `<option value="">Select project first</option>`;
    updateSubphaseOptions();
    return;
  }
  const filteredSolutions = state.solutions.filter((s) => s.project_id === projectId);
  const solutionOpts = filteredSolutions.map((s) => `<option value="${s.solution_id}">${s.solution_name}</option>`).join("");
  solSel.innerHTML = `<option value="">Select</option>${solutionOpts}`;
  updateSubphaseOptions();
}

function updateSubphaseOptions() {
  const sel = els.subcomponentForm?.querySelector('[name="sub_phase"]');
  if (!sel) return;
  const solutionId = els.subcomponentForm.querySelector('[name="solution_id"]')?.value;
  const phases = orderedPhases(solutionId).map((p) => {
    const ph = state.phases.find((x) => x.phase_id === p.phase_id);
    return `<option value="${p.phase_id}">${ph?.phase_name || p.phase_id}</option>`;
  });
  sel.innerHTML = `<option value="">None</option>${phases.join("")}`;
}

function renderKanban() {
  if (!els.kanbanBoard) return;
  const list = filteredSubcomponents();
  const phaseGroups = Array.from(
    new Set(state.phases.sort((a, b) => a.sequence - b.sequence).map((p) => p.phase_group))
  );

  // group subs by project -> solution
  const byProject = {};
  list.forEach((c) => {
    const pid = c.project_id || "none";
    const sid = c.solution_id || "none";
    byProject[pid] = byProject[pid] || {};
    byProject[pid][sid] = byProject[pid][sid] || [];
    byProject[pid][sid].push(c);
  });

  let html = "";
  Object.entries(byProject).forEach(([pid, solutions]) => {
    const projName = state.projects.find((p) => p.project_id === pid)?.project_name || "Unassigned Project";
    html += `<div class="kanban-project"><div class="kanban-project-title">${projName}</div>`;
    Object.entries(solutions).forEach(([sid, items]) => {
      const solName = state.solutions.find((s) => s.solution_id === sid)?.solution_name || "Unassigned Solution";
      html += `<div class="kanban-solution"><div class="kanban-solution-title">${solName} <span class="pill">${items.length}</span></div>`;
      html += renderSolutionSwimlane(items, phaseGroups);
      html += `</div>`;
    });
    html += "</div>";
  });

  els.kanbanBoard.innerHTML = html || "<p class='muted'>No items</p>";
}

function renderSolutionSwimlane(items, phaseGroups) {
  let html = `<div class="kanban-swimlane">`;
  phaseGroups.forEach((g) => {
    const groupCards = items.filter((c) => {
      const phase = state.phases.find((p) => p.phase_id === c.sub_phase);
      return (phase?.phase_group || "Unassigned") === g;
    });
    html += `<div class="kanban-column"><h4>${g}</h4>${renderKanbanCards(groupCards)}</div>`;
  });
  // handle unassigned if any
  const unassigned = items.filter((c) => !c.sub_phase || !state.phases.find((p) => p.phase_id === c.sub_phase));
  if (unassigned.length) {
    html += `<div class="kanban-column"><h4>Unassigned</h4>${renderKanbanCards(unassigned)}</div>`;
  }
  html += `</div>`;
  return html;
}

function renderKanbanCards(cards) {
  if (!cards.length) return "<p class='muted'>Empty</p>";
  return cards
    .map((c) => {
      const proj = state.projects.find((p) => p.project_id === c.project_id)?.project_name || "";
      const sol = state.solutions.find((s) => s.solution_id === c.solution_id)?.solution_name || "";
      const statusLabel = c.sub_phase || formatStatus(c.status);
      return `<div class="kanban-card"><strong>${c.subcomponent_name}</strong><div class="meta">${proj}${sol ? " • " + sol : ""}</div><div class="meta">P${c.priority ?? ""} • ${statusLabel}</div><div class="meta">Due ${c.due_date || "—"}</div></div>`;
    })
    .join("");
}

function renderCalendar() {
  if (!els.calendarGrid) return;
  const byDay = {};
  state.subcomponents.forEach((s) => {
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
      .map((i) => `<div>${i.subcomponent_name} (${formatStatus(i.status)})</div>`)
      .join("")}</div>`;
  });
  els.calendarGrid.innerHTML = html;
}

async function downloadCsv(kind, filename, resultEl) {
  try {
    const res = await fetch(`${API_BASE}/${kind}/export`);
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
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/${kind}/import`, {
      method: "POST",
      body: formData,
    });
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
    setImportResult(
      resultEl,
      errs.length ? `${msg}. Errors: ${errs.length} (see console)` : msg,
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

function bindNav() {
  els.navButtons.forEach((btn) =>
    btn.addEventListener("click", () => {
      setView(btn.dataset.view);
    })
  );
}

function init() {
  initTheme();
  bindCsvControls();
  bindNav();
  bindProjectForm();
  bindSolutionForm();
  bindSubcomponentForm();
  setView(state.currentView);
  loadData();
}

init();
