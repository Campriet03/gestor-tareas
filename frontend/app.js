"use strict";
const API = "/api/v1";
const POLL_MS = 30000; // ADR 0006: consulta periódica de notificaciones
const STATUS = { todo: "Por hacer", doing: "En progreso", done: "Hecha" };
const ORDER = ["todo", "doing", "done"];

const state = { token: localStorage.getItem("token"), user: null, teams: [], team: null, project: null,
  projects: [], tasks: [], invitations: [], notes: { items: [], unread: 0 }, showNotes: false, tab: "login" };
let pollTimer = null;

// ---------- utilidades ----------
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(c));
  return el;
}

function toast(message) {
  const t = document.getElementById("toast");
  t.textContent = message; t.classList.add("show");
  clearTimeout(toast.id); toast.id = setTimeout(() => t.classList.remove("show"), 2800);
}

async function api(path, { method = "GET", data } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json", ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}) },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (res.status === 204) return null;
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && state.token) logout("Tu sesión expiró. Inicia sesión de nuevo.");
    throw new Error(json.error?.message || "Error inesperado");
  }
  return json;
}

async function run(action) {
  try { await action(); } catch (e) { toast(e.message); }
}

// ---------- sesión ----------
function setSession({ token, user }) {
  state.token = token; state.user = user; localStorage.setItem("token", token);
}

function logout(message) {
  localStorage.removeItem("token");
  clearInterval(pollTimer);
  Object.assign(state, { token: null, user: null, teams: [], team: null, project: null, projects: [], tasks: [],
    invitations: [], notes: { items: [], unread: 0 }, showNotes: false });
  render();
  if (message) toast(message);
}

async function boot() {
  if (state.token) {
    try { state.user = await api("/auth/me"); await loadHome(); startPolling(); }
    catch { state.token = null; localStorage.removeItem("token"); }
  }
  render();
}

// ---------- carga de datos ----------
async function loadHome() {
  [state.teams, state.invitations, state.notes] = await Promise.all([api("/teams"), api("/invitations"), api("/notifications")]);
}

async function refreshNotifications() {
  try {
    const snapshot = () => JSON.stringify([state.notes, state.invitations, state.team?.members]);
    const before = snapshot();
    [state.notes, state.invitations] = await Promise.all([api("/notifications"), api("/invitations")]);
    if (state.team) state.team = await api(`/teams/${state.team.id}`); // por si alguien aceptó una invitación
    // No redibujar si hay un campo en edición: se perdería lo que la persona está escribiendo
    const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
    if (before !== snapshot() && !typing) render();
  } catch { /* se reintenta en el siguiente ciclo */ }
}

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(refreshNotifications, POLL_MS);
}

async function selectTeam(id) {
  state.team = await api(`/teams/${id}`);
  state.projects = await api(`/teams/${id}/projects`);
  state.project = null; state.tasks = [];
  render();
}

async function selectProject(id) {
  state.project = await api(`/projects/${id}`);
  [state.team, state.tasks] = await Promise.all([api(`/teams/${state.project.team_id}`), api(`/projects/${id}/tasks`)]);
  render();
}

// ---------- vistas ----------
function authView() {
  const isLogin = state.tab === "login";
  const error = h("p", { class: "error", role: "alert" });
  const field = (label, name, type, extra = {}) => h("label", {}, label, h("input", { name, type, required: true, ...extra }));
  const form = h("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(e.target));
      try {
        setSession(await api(isLogin ? "/auth/login" : "/auth/register", { method: "POST", data }));
        await loadHome(); startPolling(); render();
      } catch (err) { error.textContent = err.message; }
    } },
    isLogin ? null : field("Nombre", "name", "text", { maxlength: 80, autocomplete: "name" }),
    field("Correo", "email", "email", { autocomplete: "email" }),
    field("Contraseña", "password", "password", { minlength: 8, autocomplete: isLogin ? "current-password" : "new-password" }),
    error,
    h("button", { class: "primary", type: "submit" }, isLogin ? "Entrar" : "Crear cuenta"));
  const tab = (id, text) => h("button", { type: "button", role: "tab", "aria-selected": String(state.tab === id),
    onclick: () => { state.tab = id; render(); } }, text);
  return h("main", { class: "auth card" }, h("h1", {}, "Gestor de Tareas"),
    h("p", { class: "muted" }, "Organiza equipos, proyectos y tareas."),
    h("div", { class: "tabs", role: "tablist" }, tab("login", "Iniciar sesión"), tab("register", "Registrarse")), form);
}

function notificationsPanel() {
  const { items, unread } = state.notes;
  return h("section", { class: "panel card", "aria-label": "Notificaciones" },
    h("div", { class: "row", style: "justify-content:space-between" }, h("h3", {}, "Notificaciones"),
      unread ? h("button", { class: "link", onclick: () => run(async () => { await api("/notifications/read-all", { method: "POST" }); await refreshNotifications(); }) }, "Marcar todas como leídas") : null),
    items.length ? items.map((n) => h("div", { class: "note" + (n.is_read ? "" : " unread") },
      n.message, h("div", { class: "muted" }, n.created_at))) : h("p", { class: "muted" }, "Sin notificaciones."));
}

function header() {
  return h("header", { class: "top" }, h("strong", {}, "Gestor de Tareas"),
    h("div", { class: "row" }, h("span", { class: "muted" }, state.user.name),
      h("button", { class: "bell", "aria-label": `Notificaciones, ${state.notes.unread} sin leer`,
        onclick: () => { state.showNotes = !state.showNotes; render(); } },
        "🔔", state.notes.unread ? h("span", { class: "badge" }, state.notes.unread) : null),
      h("button", { onclick: () => logout() }, "Salir")));
}

function sidebar() {
  const teamForm = h("form", { class: "inline", onsubmit: (e) => { e.preventDefault(); const name = e.target.name.value;
    run(async () => { const t = await api("/teams", { method: "POST", data: { name } }); state.teams = await api("/teams"); await selectTeam(t.id); }); } },
    h("input", { name: "name", placeholder: "Nuevo equipo", required: true, maxlength: 80, "aria-label": "Nombre del nuevo equipo" }),
    h("button", { class: "primary" }, "Crear"));
  const invites = state.invitations.length ? h("section", { class: "card stack" }, h("h2", {}, "Invitaciones"),
    state.invitations.map((i) => h("div", { class: "stack" }, h("div", {}, `${i.invited_by_name} te invitó a «${i.team_name}»`),
      h("div", { class: "row" },
        h("button", { class: "primary", onclick: () => run(async () => { await api(`/invitations/${i.id}/accept`, { method: "POST" }); await loadHome(); toast("Te uniste al equipo"); render(); }) }, "Aceptar"),
        h("button", { onclick: () => run(async () => { await api(`/invitations/${i.id}/decline`, { method: "POST" }); await loadHome(); render(); }) }, "Rechazar"))))) : null;
  return h("aside", { class: "side" }, invites,
    h("section", { class: "card stack" }, h("h2", {}, "Mis equipos"),
      state.teams.length ? h("ul", { class: "list" }, state.teams.map((t) => h("li", {},
        h("button", { "aria-current": String(state.team?.id === t.id), onclick: () => run(() => selectTeam(t.id)) }, t.name, " ", h("span", { class: "tag" }, t.role === "owner" ? "propietario" : "miembro"))))) : h("p", { class: "muted" }, "Aún no tienes equipos."),
      teamForm));
}

function teamView() {
  const t = state.team;
  const isOwner = t.role === "owner";
  const invite = isOwner ? h("form", { class: "inline", onsubmit: (e) => { e.preventDefault(); const email = e.target.email.value;
    run(async () => { await api(`/teams/${t.id}/invitations`, { method: "POST", data: { email } }); e.target.reset(); toast("Invitación enviada"); }); } },
    h("input", { name: "email", type: "email", placeholder: "Correo de la persona a invitar", required: true, "aria-label": "Correo a invitar" }),
    h("button", {}, "Invitar")) : null;
  const projectForm = h("form", { class: "inline", onsubmit: (e) => { e.preventDefault(); const name = e.target.name.value;
    run(async () => { const p = await api(`/teams/${t.id}/projects`, { method: "POST", data: { name } }); state.projects = await api(`/teams/${t.id}/projects`); await selectProject(p.id); }); } },
    h("input", { name: "name", placeholder: "Nuevo proyecto", required: true, maxlength: 100, "aria-label": "Nombre del nuevo proyecto" }),
    h("button", { class: "primary" }, "Crear proyecto"));
  return h("section", { class: "card stack" }, h("h2", {}, t.name),
    h("p", { class: "muted" }, "Miembros: ", t.members.map((m) => m.name).join(", ")), invite,
    h("h3", {}, "Proyectos"),
    state.projects.length ? h("ul", { class: "list" }, state.projects.map((p) => h("li", {},
      h("button", { "aria-current": String(state.project?.id === p.id), onclick: () => run(() => selectProject(p.id)) }, p.name)))) : h("p", { class: "muted" }, "Este equipo no tiene proyectos."),
    projectForm);
}

function taskCard(task) {
  const overdue = task.due_date && task.status !== "done" && task.due_date < new Date().toISOString().slice(0, 10);
  const idx = ORDER.indexOf(task.status);
  const move = (to) => run(async () => { await api(`/tasks/${task.id}`, { method: "PATCH", data: { status: to } }); state.tasks = await api(`/projects/${state.project.id}/tasks`); render(); });
  const assign = h("select", { "aria-label": `Asignar «${task.title}»`, onchange: (e) => run(async () => {
      await api(`/tasks/${task.id}`, { method: "PATCH", data: { assignee_id: e.target.value ? Number(e.target.value) : null } });
      state.tasks = await api(`/projects/${state.project.id}/tasks`); render(); }) },
    h("option", { value: "" }, "Sin asignar"),
    state.team.members.map((m) => h("option", { value: m.id, selected: m.id === task.assignee_id }, m.name)));
  return h("article", { class: "task" + (overdue ? " overdue" : "") }, h("div", { class: "title" }, task.title),
    task.due_date ? h("div", { class: "muted" }, (overdue ? "Vencida: " : "Límite: ") + task.due_date) : null, assign,
    h("div", { class: "row" },
      idx > 0 ? h("button", { "aria-label": "Mover a la columna anterior", onclick: () => move(ORDER[idx - 1]) }, "←") : null,
      idx < 2 ? h("button", { "aria-label": "Mover a la columna siguiente", onclick: () => move(ORDER[idx + 1]) }, "→") : null,
      h("button", { class: "danger", onclick: () => confirm(`¿Eliminar «${task.title}»?`) && run(async () => {
        await api(`/tasks/${task.id}`, { method: "DELETE" }); state.tasks = await api(`/projects/${state.project.id}/tasks`); render(); }) }, "Eliminar")));
}

function boardView() {
  const form = h("form", { class: "new-task", onsubmit: (e) => { e.preventDefault(); const f = e.target;
    run(async () => {
      await api(`/projects/${state.project.id}/tasks`, { method: "POST", data: { title: f.title.value,
        assignee_id: f.assignee.value ? Number(f.assignee.value) : null, due_date: f.due.value || null } });
      state.tasks = await api(`/projects/${state.project.id}/tasks`); render(); }); } },
    h("input", { name: "title", placeholder: "Nueva tarea", required: true, maxlength: 150, "aria-label": "Título de la tarea" }),
    h("select", { name: "assignee", "aria-label": "Responsable" }, h("option", { value: "" }, "Sin asignar"), state.team.members.map((m) => h("option", { value: m.id }, m.name))),
    h("input", { name: "due", type: "date", "aria-label": "Fecha límite" }),
    h("button", { class: "primary" }, "Agregar"));
  return h("section", { class: "card" }, h("h2", {}, state.project.name), form,
    h("div", { class: "board" }, ORDER.map((s) => {
      const tasks = state.tasks.filter((t) => t.status === s);
      return h("div", { class: "col" }, h("h3", {}, `${STATUS[s]} (${tasks.length})`), tasks.map(taskCard));
    })));
}

function render() {
  const app = document.getElementById("app");
  app.replaceChildren();
  if (!state.token || !state.user) { app.append(authView()); return; }
  app.append(header());
  if (state.showNotes) app.append(notificationsPanel());
  app.append(h("div", { class: "layout" }, sidebar(),
    h("main", { class: "stack" }, state.team ? teamView() : h("p", { class: "card muted" }, "Elige o crea un equipo para empezar."),
      state.project ? boardView() : null)));
}

boot();
