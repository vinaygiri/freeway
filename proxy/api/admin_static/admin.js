const state = {
  config: null,
  activeView: "dashboard",
  pollTimer: null,
  modelQuery: "",
  modelSort: readPref("freeway.modelSort", "quality"),
  modelFilter: readPref("freeway.modelFilter", "ready"),
  modelsData: null,
};

function readPref(key, fallback) {
  try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}
function writePref(key, value) {
  try { localStorage.setItem(key, value); } catch { /* storage unavailable */ }
}

const MASKED_SECRET = "********";

// ---- view definitions (task-oriented, with help copy) ----
const STATUS_VIEWS = [
  { id: "dashboard", icon: "◆", label: "Dashboard", title: "Dashboard",
    help: "A quick read on whether Freeway is working and what it's doing right now.", render: renderDashboard },
  { id: "models", icon: "◎", label: "Models", title: "Models",
    help: "Every model Freeway can route to and its live status. Star favourites and pick the one to use — one click.", render: renderModels },
  { id: "activity", icon: "≡", label: "Activity", title: "Request Activity",
    help: "Every request that passed through Freeway: which provider served it, whether it fell back, and why.", render: renderActivity },
  { id: "limits", icon: "▤", label: "Limits", title: "Limits & Quota",
    help: "How much of each provider's free-tier budget you've used this window.", render: renderLimits },
  { id: "health", icon: "♥", label: "Health", title: "Provider Health",
    help: "Live stability of each provider from background probes (no completion cost).", render: renderHealth },
  { id: "cache", icon: "⚡", label: "Cache", title: "Response Cache",
    help: "Identical no-tool requests can be served instantly from cache.", render: renderCache },
];

const CONFIG_VIEWS = [
  { id: "providers", icon: "⚿", label: "Providers", title: "Connect Providers",
    help: "Add an API key for each AI provider you want to use. Models appear on the Models page once a key works.",
    sections: ["providers", "runtime", "diagnostics", "smoke"], containerId: "providersSections", providerStrip: true },
  { id: "routing", icon: "⇄", label: "Routing", title: "Model & Routing",
    help: "Choose your default model, set a fallback chain, define @-directive shortcuts, and enable auto-fit to survive free-tier token limits.",
    sections: ["models", "routing", "thinking"], containerId: "routingSections", explainer: routingExplainer },
  { id: "features", icon: "⚙", label: "Features", title: "Features",
    help: "Turn Freeway's observability and caching features on or off.",
    sections: ["features", "web_tools"], containerId: "featuresSections" },
  { id: "privacy", icon: "⛨", label: "Privacy", title: "Privacy & Data Governance",
    help: "Hard rules that keep your prompts away from providers you don't trust.",
    sections: ["privacy"], containerId: "privacySections" },
  { id: "messaging", icon: "✉", label: "Messaging", title: "Messaging & Voice",
    help: "Optional Discord / Telegram bridges and voice-note transcription.",
    sections: ["messaging", "voice"], containerId: "messagingSections" },
];

const HELP_VIEWS = [
  { id: "guide", icon: "?", label: "User Guide", title: "Freeway User Guide",
    help: "Everything you need — setup, commands, what each page does, and how the routing features work.",
    static: true, render: renderHelp },
];

const byId = (id) => document.getElementById(id);
const allViews = () => [...STATUS_VIEWS, ...CONFIG_VIEWS, ...HELP_VIEWS];
const findView = (id) => allViews().find((v) => v.id === id);
const RENDER_VIEWS = () => [...STATUS_VIEWS, ...HELP_VIEWS];
const isStatus = (id) => RENDER_VIEWS().some((v) => v.id === id);

function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}
function badge(text, kind) { return el("span", `badge ${kind || "neutral"}`, text); }

function routingExplainer() {
  const box = el("div", "explainer");
  box.innerHTML = `
    <div class="explainer-item">
      <h4>Fallback chain</h4>
      <p>If your default model's provider is down or rate-limited, Freeway automatically tries these next, in order.
      Tip: build it fast from the <strong>Models</strong> page — click "+ Fallback" on any model.</p>
    </div>
    <div class="explainer-item">
      <h4>@-Directives — per-message model shortcuts</h4>
      <p>Define aliases as <code>key=provider/model</code> (comma-separated) in <em>Inline @-Directives</em> below.
      Then type <code>@key</code> anywhere in a prompt to route <em>that message</em> to that model.</p>
      <p class="mono-example">fast=groq/llama-3.3-70b-versatile, big=cerebras/gpt-oss-120b, local=ollama/qwen2.5-coder</p>
      <p>Usage in Claude Code: <code>@big refactor this module</code> → that turn goes to Cerebras.
      Only the first <code>@alias</code> in a message wins; unknown <code>@words</code> (emails, decorators) are ignored.</p>
    </div>
    <div class="explainer-item">
      <h4>Auto-fit — the "request too large" (413) fix</h4>
      <p>Free tiers cap tokens-per-minute. Editors send every tool's schema on every request, which alone can blow the cap.
      Set <em>Auto-fit Budget</em> to a bit under your provider's per-minute limit and Freeway drops the largest
      non-essential tools until the request fits. Core coding tools are always kept.</p>
    </div>`;
  return box;
}

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function load() {
  showMessage("Loading Freeway control center");
  buildViews();
  // Reveal the default view with a spinner so the page isn't blank while config loads.
  const first = byId(`view-${state.activeView}`);
  if (first) { first.hidden = false; first.classList.add("active"); }
  byId("pageTitle").textContent = (findView(state.activeView) || {}).title || "";
  showLoading(state.activeView);
  const config = await api("/admin/api/config");
  state.config = config;
  renderNav();
  renderProviders(config.provider_status);
  renderSections(config.sections, config.fields);
  byId("configPath").textContent = config.paths.managed;
  await validate(false);
  await refreshLocalStatus();
  updateDirtyState();
  const hashView = location.hash.slice(1);
  if (findView(hashView)) state.activeView = hashView;
  setActiveView(state.activeView, { scroll: false });
  showMessage("");
}

// ---- scaffolding ----
function buildViews() {
  const root = byId("adminViews");
  root.innerHTML = "";
  allViews().forEach((view) => {
    const section = el("section", `admin-view${isStatus(view.id) ? " status-view" : ""}`);
    section.id = `view-${view.id}`;
    section.dataset.view = view.id;
    section.hidden = true;
    const head = el("div", "view-head");
    head.appendChild(el("p", "view-help", view.help));
    section.appendChild(head);
    if (isStatus(view.id)) {
      const body = el("div", "status-body");
      body.id = `status-${view.id}`;
      section.appendChild(body);
    } else {
      if (view.explainer) section.appendChild(view.explainer());
      if (view.providerStrip) {
        const strip = el("section", "provider-strip");
        const h = el("div", "strip-header");
        h.appendChild(el("h3", null, "Provider connections"));
        strip.appendChild(h);
        const grid = el("div", "provider-grid");
        grid.id = "providerGrid";
        strip.appendChild(grid);
        section.appendChild(strip);
      }
      const container = el("div", "form-sections");
      container.id = view.containerId;
      section.appendChild(container);
    }
    root.appendChild(section);
  });
}

function renderNav() {
  const nav = byId("sectionNav");
  nav.innerHTML = "";
  nav.appendChild(el("div", "nav-group-label", "Monitor"));
  STATUS_VIEWS.forEach((v) => nav.appendChild(navButton(v)));
  nav.appendChild(el("div", "nav-group-label", "Configure"));
  CONFIG_VIEWS.forEach((v) => nav.appendChild(navButton(v)));
  nav.appendChild(el("div", "nav-group-label", "Help"));
  HELP_VIEWS.forEach((v) => nav.appendChild(navButton(v)));
}

function navButton(view) {
  const b = el("button", "nav-link");
  b.type = "button";
  b.dataset.view = view.id;
  b.appendChild(el("span", "nav-icon", view.icon));
  b.appendChild(el("span", null, view.label));
  b.addEventListener("click", () => setActiveView(view.id, { scroll: true }));
  return b;
}

function setActiveView(viewId, { scroll = false } = {}) {
  const view = findView(viewId) || STATUS_VIEWS[0];
  state.activeView = view.id;
  byId("pageTitle").textContent = view.title;
  document.querySelectorAll(".nav-link").forEach((l) => l.classList.toggle("active", l.dataset.view === view.id));
  document.querySelectorAll(".admin-view").forEach((s) => {
    const on = s.dataset.view === view.id;
    s.classList.toggle("active", on);
    s.hidden = !on;
  });
  if (location.hash.slice(1) !== view.id) {
    try { history.replaceState(null, "", `#${view.id}`); } catch { location.hash = view.id; }
  }
  const status = isStatus(view.id);
  byId("actionBarButtons").hidden = status;
  byId("dirtyState").hidden = status;
  if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  if (status) {
    if (!view.static) showLoading(view.id);
    view.render().catch((e) => showStatus(view.id, `Couldn't load: ${e.message}`));
    if (!view.static) state.pollTimer = setInterval(() => view.render().catch(() => {}), 5000);
  }
  if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
}

function showStatus(id, msg) {
  const b = byId(`status-${id}`);
  if (b) b.innerHTML = `<div class="empty-state">${msg}</div>`;
}
function showLoading(id) {
  const b = byId(`status-${id}`);
  if (b) b.innerHTML = '<div class="loading"><span class="spinner"></span>Loading…</div>';
}
function emptyState(icon, title, detail, actionLabel, actionView) {
  const box = el("div", "empty-state");
  box.appendChild(el("div", "empty-icon", icon));
  box.appendChild(el("div", "empty-title", title));
  if (detail) box.appendChild(el("div", "empty-detail", detail));
  if (actionLabel) {
    const btn = el("button", "primary-button small", actionLabel);
    btn.addEventListener("click", () => setActiveView(actionView, { scroll: true }));
    box.appendChild(btn);
  }
  return box;
}
function statCard(label, value, sub, kind) {
  const c = el("div", "stat-card");
  c.appendChild(el("div", "stat-label", label));
  c.appendChild(el("div", `stat-value ${kind || ""}`.trim(), value));
  if (sub) c.appendChild(el("div", "stat-sub", sub));
  return c;
}

// ---- Dashboard ----
async function renderDashboard() {
  const [models, activity, cache] = await Promise.all([
    api("/admin/api/models"), api("/admin/api/requests"), api("/admin/api/cache"),
  ]);
  const body = byId("status-dashboard");
  body.innerHTML = "";
  const ready = models.providers.filter((p) => p.usable);
  const configured = models.providers.filter((p) => p.configured);
  const currentUsable = ready.some((p) => p.models.some((m) => m.is_current)) || currentProviderUsable(models);
  // Prefer the model that was ACTUALLY routed most recently (matches Activity),
  // falling back to the configured default MODEL when there's no traffic yet.
  const rows = activity.requests || [];  // newest first
  const last = rows.find((r) => r.provider_id);
  const routedRef = last ? `${last.provider_id}/${last.provider_model || last.model || ""}`.replace(/\/$/, "") : "";
  const activeModel = routedRef || models.current_model;
  const differs = routedRef && models.current_model && routedRef !== models.current_model;
  const hero = el("div", `hero ${configured.length ? (currentUsable ? "ok" : "warn") : "warn"}`);
  const dot = el("span", "hero-dot");
  const heroText = el("div");
  heroText.appendChild(el("div", "hero-title", configured.length ? "Freeway is running" : "Freeway needs a provider"));
  heroText.appendChild(el("div", "hero-sub",
    configured.length
      ? `Routing to ${shortRef(activeModel)} · ${ready.length} provider(s) ready`
      : "Add an API key to start routing to a free model."));
  hero.append(dot, heroText);
  body.appendChild(hero);

  const grid = el("div", "stat-grid");
  const s = cache.stats || {};
  const hitRate = (s.hits || 0) + (s.misses || 0) > 0 ? Math.round((100 * (s.hits || 0)) / ((s.hits || 0) + (s.misses || 0))) : 0;
  grid.appendChild(statCard("Active model", shortRef(activeModel),
    differs ? `default: ${shortRef(models.current_model)}` : (routedRef ? "from last request" : "configured default")));
  grid.appendChild(statCard("Providers ready", `${ready.length}`, `${configured.length} configured`, ready.length ? "ok" : "warn"));
  grid.appendChild(statCard("Fallback chain", `${models.fallbacks.length}`, models.fallbacks.length ? "auto-failover on" : "none — add on Models", models.fallbacks.length ? "ok" : "warn"));
  grid.appendChild(statCard("Auto-fit", models.auto_fit_max_tokens ? `${models.auto_fit_max_tokens} tok` : "off", models.auto_fit_max_tokens ? "413 protection on" : "may 413 on free tiers", models.auto_fit_max_tokens ? "ok" : "warn"));
  grid.appendChild(statCard("Recent requests", `${(activity.requests || []).length}`, activity.enabled ? "inspector on" : "inspector off"));
  grid.appendChild(statCard("Cache hit-rate", cache.enabled ? `${hitRate}%` : "off", cache.enabled ? `${s.hits || 0}/${(s.hits || 0) + (s.misses || 0)}` : "disabled"));
  body.appendChild(grid);

  const actions = el("div", "quick-actions");
  actions.appendChild(quickAction("◎ Pick a model", "models"));
  actions.appendChild(quickAction("⚿ Connect a provider", "providers"));
  actions.appendChild(quickAction("⇄ Tune routing & auto-fit", "routing"));
  actions.appendChild(quickAction("≡ See recent activity", "activity"));
  body.appendChild(actions);
}
function currentProviderUsable(models) {
  const cur = (models.current_model || "").split("/")[0];
  const p = models.providers.find((x) => x.provider_id === cur);
  return p ? p.usable : false;
}
function quickAction(label, view) {
  const b = el("button", "quick-action", label);
  b.addEventListener("click", () => setActiveView(view, { scroll: true }));
  return b;
}
function shortRef(ref) {
  if (!ref) return "—";
  const parts = ref.split("/");
  return parts.length > 1 ? `${parts[0]} / ${parts.slice(1).join("/")}` : ref;
}

// ---- Models picker ----
async function renderModels() {
  const data = await api("/admin/api/models");
  state.modelsData = data;
  const body = byId("status-models");
  // Build the toolbar + list container ONCE; polling only repaints the list, so the
  // search box keeps focus and the Sort buttons stay live (no rebuild mid-click).
  if (!byId("modelsToolbar")) {
    body.innerHTML = "";
    const toolbar = el("div", "toolbar");
    toolbar.id = "modelsToolbar";
    const search = el("input", "search-input");
    search.type = "search";
    search.placeholder = "Search models or providers…";
    search.value = state.modelQuery;
    search.addEventListener("input", () => { state.modelQuery = search.value; paintModels(); });
    toolbar.appendChild(search);
    const sortWrap = el("div", "segmented");
    sortWrap.appendChild(el("span", "seg-label", "Sort"));
    [["quality", "Quality"], ["latency", "Latency"], ["name", "Name"]].forEach(([k, lbl]) => {
      const b = el("button", `seg${state.modelSort === k ? " on" : ""}`, lbl);
      b.dataset.k = k;
      b.addEventListener("click", () => {
        state.modelSort = k;
        writePref("freeway.modelSort", k);
        sortWrap.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x.dataset.k === k));
        paintModels();
        showMessage(k === "latency"
          ? "Sorted by latency (models from the same provider share one latency)"
          : `Sorted by ${lbl.toLowerCase()}`, "ok");
      });
      sortWrap.appendChild(b);
    });
    toolbar.appendChild(sortWrap);
    const filterWrap = el("div", "segmented");
    filterWrap.appendChild(el("span", "seg-label", "Show"));
    [["ready", "Ready"], ["all", "All"], ["favourites", "★ Favs"]].forEach(([k, lbl]) => {
      const b = el("button", `seg${state.modelFilter === k ? " on" : ""}`, lbl);
      b.dataset.f = k;
      b.addEventListener("click", () => {
        state.modelFilter = k;
        writePref("freeway.modelFilter", k);
        filterWrap.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x.dataset.f === k));
        paintModels();
        showMessage(`Showing: ${lbl}`, "ok");
      });
      filterWrap.appendChild(b);
    });
    toolbar.appendChild(filterWrap);
    const legend = el("div", "legend");
    legend.append(badge("ready", "ok"), badge("needs key", "warn"), badge("unavailable", "error"), badge("↩ fallback", "fallback"));
    toolbar.appendChild(legend);
    const verifyWrap = el("div", "fav-slot");
    const verifyBtn = el("button", "primary-button small", "⚡ Verify all");
    verifyBtn.id = "verifyAllBtn";
    verifyBtn.title = "Ping every model shown to check it's actually live (sends a tiny request to each — uses a little quota). Results are saved.";
    verifyBtn.addEventListener("click", verifyVisibleModels);
    verifyWrap.appendChild(verifyBtn);
    const suggestBtn = el("button", "primary-button small", "★ Suggest a chain");
    suggestBtn.id = "suggestChainBtn";
    suggestBtn.title = "Pick the best live model per provider (live-verify × quality × context) and apply it as your primary + fallback chain — one click. Run ⚡ Verify all first for the sharpest picks.";
    suggestBtn.addEventListener("click", suggestChain);
    verifyWrap.appendChild(suggestBtn);
    toolbar.appendChild(verifyWrap);
    body.appendChild(toolbar);
    body.appendChild(el("p", "models-help",
      "Show → Ready: models whose provider is currently usable  ·  All: every provider, including ones that still need a key  ·  ★ Favs: your starred models.  “ready” is provider-level (optimistic) — click ⚡ Verify all, or a model's Test, to ping each one. Tested models regroup by real result: ✓ verified, ⏳ Busy (rate-limited / overloaded — retry later), or ✗ Verified down. Results are saved."));
    body.appendChild(el("p", "models-help",
      "★ Favourite = a personal shortlist/bookmark (doesn't change routing on its own — use the ★ Favs filter to find them fast). Fallback = routing safety net: if your primary model's provider is down or rate-limited, Freeway tries the fallback chain in order. “Use” sets the primary model  ·  “+ Fallback” / “✓ Fallback” adds or removes a model from the chain."));
    const list = el("div", "models-list");
    list.id = "modelsList";
    body.appendChild(list);
  }
  paintModels();
}

function paintModels() {
  const data = state.modelsData;
  const list = byId("modelsList");
  if (!data || !list) return;
  list.innerHTML = "";
  if (data.model_locked) {
    const banner = el("div", "lock-banner");
    banner.textContent = "⚠ The default model is set by an environment variable (MODEL), which overrides the UI — “Use” can't change it until you unset MODEL and restart. Fallbacks still work.";
    list.appendChild(banner);
  }
  const q = state.modelQuery.trim().toLowerCase();
  const match = (pid, mid) => !q || pid.toLowerCase().includes(q) || mid.toLowerCase().includes(q) || (data.providers.find((p) => p.provider_id === pid)?.display_name || "").toLowerCase().includes(q);

  const rows = [];
  data.providers.forEach((p) => {
    (p.models || []).forEach((m) => {
      if (match(p.provider_id, m.id)) rows.push({ p, m });
    });
  });

  const cmp = modelComparator();
  const favs = rows.filter((r) => r.m.is_favourite).sort(cmp);
  const nonFav = rows.filter((r) => !r.m.is_favourite);
  // A tested model's real result wins over the provider-level "ready": live/untested
  // stay Ready; 429/overload are temporary (Busy); the rest are Verified down.
  const ready = nonFav.filter((r) => rowBucket(r) === "ready").sort(cmp);
  const busy = nonFav.filter((r) => rowBucket(r) === "busy").sort(cmp);
  const down = nonFav.filter((r) => rowBucket(r) === "down").sort(cmp);
  const other = nonFav.filter((r) => rowBucket(r) === "other").sort(cmp);

  // Providers with no discovered models (can't be listed without a working key) —
  // shown as status rows in "All" mode so every provider is visible.
  const noModels = data.providers
    .filter((p) => !(p.models || []).length && (!q || p.provider_id.toLowerCase().includes(q) || (p.display_name || "").toLowerCase().includes(q)))
    .sort((a, b) => Number(b.configured) - Number(a.configured) || (a.display_name || "").localeCompare(b.display_name || ""));

  const filter = state.modelFilter;
  const isFav = filter === "favourites";

  const printed = [];
  if (favs.length) printed.push(modelGroup("★ Favourites", favs, data));
  if (!isFav) {
    if (ready.length) printed.push(modelGroup("Ready to use", ready, data));
    if (busy.length) printed.push(modelGroup("Busy — retry later", busy, data));
    if (down.length) printed.push(modelGroup("Verified down", down, data));
    if (other.length) printed.push(modelGroup("Needs setup / unavailable", other, data));
    if (filter === "all" && noModels.length) printed.push(providerStatusGroup(noModels));
  }

  if (!printed.length) {
    if (filter === "favourites") {
      list.appendChild(emptyState("★", q ? "No favourites match your search" : "No favourites yet",
        q ? "Try a different term." : "Star (☆) a model in Ready or All to shortlist it here.", null));
      return;
    }
    const configured = data.providers.some((p) => p.configured);
    list.appendChild(configured
      ? emptyState("◎", q ? "No models match your search" : "No models discovered yet",
          q ? "Try a different term." : "Your providers are connected but haven't listed models yet — open Providers and hit “Refresh models”.",
          q ? null : "Go to Providers", "providers")
      : emptyState("⚿", "No providers connected yet",
          "Add an API key (Groq, Cerebras, etc.) and Freeway will discover its models here. Switch “Show” to All to see every provider and what it needs.",
          "Connect a provider", "providers"));
    return;
  }
  printed.forEach((g) => list.appendChild(g));
}

function providerStatusGroup(providers) {
  const group = el("div", "model-group");
  group.appendChild(el("div", "model-group-title", `Not connected  ·  ${providers.length}`));
  providers.forEach((p) => group.appendChild(providerStatusRow(p)));
  return group;
}

function providerStatusRow(p) {
  const card = el("div", "model-card provider-row");
  const info = el("div", "model-info");
  const nameRow = el("div", "model-name-row");
  nameRow.appendChild(el("span", "model-id", p.display_name || p.provider_id));
  info.appendChild(nameRow);
  const sub = el("div", "model-sub");
  sub.appendChild(p.configured
    ? badge(p.usable_reason || "no models yet", "neutral")
    : badge("needs key", "warn"));
  sub.appendChild(el("span", "model-meta", p.configured ? "connected — refresh to list models" : "add an API key to use"));
  info.appendChild(sub);
  card.appendChild(info);
  const actions = el("div", "model-actions");
  const connect = el("button", "mini-button ghost", p.configured ? "Providers" : "Connect");
  connect.addEventListener("click", () => setActiveView("providers"));
  actions.appendChild(connect);
  card.appendChild(actions);
  return card;
}

function latencyOf(provider) {
  const v = provider.health && (provider.health.p95_ms ?? provider.health.avg_ms);
  return v == null ? Infinity : v;
}

// Which Models group a row belongs to. A live test result overrides the optimistic
// provider-level "ready"; rate-limit/overload are temporary ("busy"); other
// failures are "down"; untested rows fall back to provider usability.
function rowBucket(r) {
  const pr = r.m.probe;
  if (pr) {
    if (pr.status === "live") return "ready";
    if (pr.kind === "rate_limited" || pr.kind === "overloaded") return "busy";
    return "down";
  }
  return r.p.usable ? "ready" : "other";
}

const PROBE_BADGE = {
  rate_limited: ["warn", "⏳ rate-limited"],
  overloaded: ["warn", "◔ overloaded"],
  unavailable: ["error", "✗ unavailable"],
  unreachable: ["neutral", "⚠ unreachable"],
  error: ["error", "✗ error"],
};
function probeBadge(probe) {
  if (probe.status === "live") return badge(`✓ verified ${probe.latency_ms}ms`, "ok");
  const [kind, label] = PROBE_BADGE[probe.kind] || PROBE_BADGE.error;
  const b = badge(label, kind);
  if (probe.error) b.title = probe.error;
  return b;
}
function modelComparator() {
  const s = state.modelSort;
  if (s === "latency") return (a, b) => latencyOf(a.p) - latencyOf(b.p) || (b.m.score_num ?? -1) - (a.m.score_num ?? -1);
  if (s === "name") return (a, b) => a.m.id.localeCompare(b.m.id);
  return (a, b) => (b.m.score_num ?? -1) - (a.m.score_num ?? -1);
}

function modelGroup(title, rows, data) {
  const group = el("div", "model-group");
  group.appendChild(el("div", "model-group-title", `${title}  ·  ${rows.length}`));
  rows.forEach(({ p, m }) => group.appendChild(modelCard(p, m, data)));
  return group;
}

function modelCard(p, m, data) {
  const ref = `${p.provider_id}/${m.id}`;
  const card = el("div", `model-card${m.is_current ? " current" : ""}${m.is_fallback ? " is-fallback" : ""}`);
  card.dataset.provider = p.provider_id;
  card.dataset.model = m.id;

  const star = el("button", `star${m.is_favourite ? " on" : ""}`, m.is_favourite ? "★" : "☆");
  star.title = m.is_favourite ? "Unfavourite" : "Favourite";
  star.addEventListener("click", () => toggleFavourite(ref));
  card.appendChild(star);

  const info = el("div", "model-info");
  const nameRow = el("div", "model-name-row");
  nameRow.appendChild(el("span", "model-id", m.id));
  if (m.is_current) nameRow.appendChild(badge("current", "ok"));
  if (m.is_fallback) nameRow.appendChild(badge("↩ fallback", "fallback"));
  info.appendChild(nameRow);
  const sub = el("div", "model-sub");
  sub.appendChild(el("span", "model-provider", p.display_name));
  // A per-model test result (if any) is authoritative and replaces the optimistic
  // provider-level "ready" badge.
  if (m.probe) sub.appendChild(probeBadge(m.probe));
  else sub.appendChild(p.usable ? badge("ready", "ok") : badge(p.usable_reason || "unavailable", p.configured ? "error" : "warn"));
  if (m.tier) sub.appendChild(badge(m.tier, tierKind(m.tier)));
  if (m.swe_score && m.swe_score !== "-") sub.appendChild(el("span", "model-meta", `SWE ${m.swe_score}`));
  if (m.context) sub.appendChild(el("span", "model-meta", m.context));
  const lat = p.health && (p.health.p95_ms ?? p.health.avg_ms);
  if (lat != null) sub.appendChild(el("span", "model-meta latency", `⚡ ${lat}ms`));
  if (m.probe) sub.appendChild(el("span", "model-meta", `tested ${agoText(m.probe.at)}`));
  info.appendChild(sub);
  card.appendChild(info);

  const actions = el("div", "model-actions");
  const use = el("button", "mini-button", m.is_current ? "In use" : "Use");
  use.disabled = m.is_current || !!data.model_locked;
  use.title = data.model_locked && !m.is_current
    ? "Default model is locked by an environment variable — unset MODEL to change it here"
    : (m.is_current ? "" : "Make this the primary model");
  use.addEventListener("click", () => setPrimaryModel(ref));
  const fb = el("button", `mini-button fb-toggle${m.is_fallback ? " on" : " ghost"}`);
  if (m.is_fallback) {
    // Selected: blue "✓ Fallback", turns red "✕ Remove" on hover so it's clearly removable.
    fb.innerHTML = '<span class="fb-idle">✓ Fallback</span><span class="fb-hover">✕ Remove</span>';
    fb.title = "In your fallback chain — click to remove";
  } else {
    fb.textContent = "+ Fallback";
    fb.title = "Add to fallback chain";
  }
  fb.addEventListener("click", () => toggleFallback(ref, m.is_fallback));
  const test = el("button", "mini-button ghost", "Test");
  test.title = "Ping this model now to check it's actually live";
  test.addEventListener("click", () => testModel(p.provider_id, m.id));
  actions.append(use, fb, test);
  card.appendChild(actions);
  return card;
}

function agoText(epochSeconds) {
  if (!epochSeconds) return "just now";
  const secs = Math.max(0, Math.floor(Date.now() / 1000 - epochSeconds));
  if (secs < 60) return "just now";
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

function applyProbe(providerId, modelId, probe) {
  const data = state.modelsData;
  if (!data) return;
  const p = data.providers.find((x) => x.provider_id === providerId);
  const m = p && (p.models || []).find((x) => x.id === modelId);
  if (m) m.probe = probe;
}

async function testModel(providerId, modelId) {
  const ref = `${providerId}/${modelId}`;
  showMessage(`Testing ${ref}…`);
  try {
    const res = await api("/admin/api/models/ping", { method: "POST", body: JSON.stringify({ provider_id: providerId, model_id: modelId }) });
    applyProbe(providerId, modelId, res.probe);
    paintModels();
    const live = res.probe && res.probe.status === "live";
    showMessage(live ? `${ref} is live (${res.probe.latency_ms}ms)` : `${ref} is down: ${(res.probe && res.probe.error) || "unknown"}`, live ? "ok" : "error");
  } catch (e) {
    showMessage(`Test failed: ${e.message}`, "error");
  }
}

async function verifyVisibleModels() {
  const cards = [...document.querySelectorAll("#modelsList .model-card[data-model]")];
  const targets = cards.map((c) => ({ provider_id: c.dataset.provider, model_id: c.dataset.model }));
  if (!targets.length) { showMessage("No models to verify in this view.", ""); return; }
  if (targets.length > 40 && !confirm(`Verify ${targets.length} models now? This sends a tiny request to each and uses a little quota.`)) return;
  const btn = byId("verifyAllBtn");
  if (btn) { btn.disabled = true; }
  let done = 0, live = 0, down = 0, idx = 0;
  const worker = async () => {
    while (idx < targets.length) {
      const t = targets[idx++];
      try {
        const res = await api("/admin/api/models/ping", { method: "POST", body: JSON.stringify(t) });
        applyProbe(t.provider_id, t.model_id, res.probe);
        if (res.probe && res.probe.status === "live") live++; else down++;
      } catch { down++; }
      done++;
      showMessage(`Verifying models…  ${done}/${targets.length}   (✓ ${live} live · ✗ ${down} down)`, "");
    }
  };
  await Promise.all(Array.from({ length: Math.min(6, targets.length) }, worker));
  paintModels();
  if (btn) { btn.disabled = false; }
  showMessage(`Verified ${targets.length}:  ✓ ${live} live · ✗ ${down} down`, down ? "warn" : "ok");
}

async function applyValues(values, note) {
  showMessage(note || "Applying…");
  const res = await api("/admin/api/config/apply", { method: "POST", body: JSON.stringify({ values }) });
  const restart = res.restart || {};
  if (restart.required && restart.automatic) {
    showMessage("Applied — restarting…", "ok");
    setTimeout(() => { window.location.href = restart.admin_url || "/admin"; }, 1500);
    return false;
  }
  // Re-pull config so other views (e.g. Routing's Fallback Chain box + chips) reflect
  // changes made from the Models page without a full page reload.
  await refreshConfig();
  return true;
}
async function refreshConfig() {
  try {
    const config = await api("/admin/api/config");
    state.config = config;
    renderProviders(config.provider_status);
    renderSections(config.sections, config.fields);
    updateDirtyState();
  } catch {}
}
async function setPrimaryModel(ref) {
  if (state.modelsData && state.modelsData.model_locked) {
    showMessage("Can't change the model — MODEL is set by an environment variable. Unset it and restart.", "error");
    return;
  }
  if (await applyValues({ MODEL: ref }, `Setting model to ${ref}…`)) { await renderModels(); showMessage(`Now routing to ${ref} — applies to new requests automatically.`, "ok"); }
}
async function toggleFallback(ref, isFallback) {
  // Read the latest chain from state (not a render-time closure) and update it
  // optimistically, so toggling several in quick succession can't clobber each other.
  const chain = (state.modelsData && state.modelsData.fallbacks) || [];
  const next = isFallback
    ? chain.filter((r) => r !== ref)
    : (chain.includes(ref) ? chain : [...chain, ref]);
  if (state.modelsData) state.modelsData.fallbacks = next;
  const note = isFallback ? "Removing fallback…" : "Adding fallback…";
  if (await applyValues({ MODEL_FALLBACKS: next.join(",") }, note)) {
    await renderModels();
    showMessage(isFallback ? `Removed ${ref} from fallback chain` : `Added ${ref} to fallback chain`, "ok");
  }
}
async function toggleFavourite(ref) {
  const favs = (state.modelsData && state.modelsData.favourites) || [];
  const next = favs.includes(ref) ? favs.filter((r) => r !== ref) : [...favs, ref];
  if (state.modelsData) state.modelsData.favourites = next;
  if (await applyValues({ FAVOURITE_MODELS: next.join(",") })) { await renderModels(); }
}

async function suggestChain() {
  if (state.modelsData && state.modelsData.model_locked) {
    showMessage("Can't change the model — MODEL is set by an environment variable. Unset it and restart.", "error");
    return;
  }
  const btn = byId("suggestChainBtn");
  if (btn) { btn.disabled = true; btn.textContent = "★ Thinking…"; }
  try {
    const res = await api("/admin/api/models/recommend");
    const chain = (res && res.chain) || [];
    if (!chain.length) {
      showMessage("No recommendation yet — click ⚡ Verify all first so Freeway knows which models are live.", "warn");
      return;
    }
    const [primary, ...fallbacks] = chain;
    if (await applyValues({ MODEL: primary, MODEL_FALLBACKS: fallbacks.join(",") }, "Applying recommended chain…")) {
      await renderModels();
      showMessage(`Recommended chain applied — ${primary}${fallbacks.length ? " → " + fallbacks.join(" → ") : ""}`, "ok");
    }
  } catch {
    showMessage("Couldn't build a recommendation right now.", "error");
  } finally {
    const b = byId("suggestChainBtn");
    if (b) { b.disabled = false; b.textContent = "★ Suggest a chain"; }
  }
}

// ---- Activity / Limits / Health / Cache ----
function servedRefOf(r) {
  if (r.provider_id) return `${r.provider_id}/${r.provider_model || r.model || ""}`.replace(/\/$/, "");
  return r.gateway_model || "—";
}
function fmtClock(at) {
  if (!at) return "—";
  const d = new Date(at * 1000);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function fmtAgo(at) {
  if (!at) return "";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - at));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

async function renderActivity() {
  const data = await api("/admin/api/requests");
  const body = byId("status-activity");
  body.innerHTML = "";
  if (!data.enabled) { body.appendChild(emptyState("≡", "Request Inspector is off", "Turn it on under Features to see routing decisions here.", "Open Features", "features")); return; }
  const rows = data.requests || [];  // newest first
  if (!rows.length) { body.appendChild(emptyState("≡", "No requests yet", "Point a tool at Freeway and run something — it'll show up here live.")); return; }

  // "What ran most recently" — the answer to "which model is running?"
  const latest = rows.find((r) => r.provider_id) || rows[0];
  const okLatest = latest.outcome === "routed";
  const hero = el("div", `hero ${okLatest ? "ok" : "warn"}`);
  hero.appendChild(el("span", "hero-dot"));
  const ht = el("div");
  ht.appendChild(el("div", "hero-title", `Most recent: ${shortRef(servedRefOf(latest))}`));
  const bits = [
    latest.was_fallback ? "switched via fallback" : "primary model",
    `${latest.input_tokens != null ? latest.input_tokens : "?"} input tokens`,
    latest.outcome || "—",
    `${fmtClock(latest.at)} (${fmtAgo(latest.at)})`,
  ];
  if (latest.error) bits.push(latest.error);
  ht.appendChild(el("div", "hero-sub", bits.join(" · ")));
  hero.appendChild(ht);
  body.appendChild(hero);

  const table = el("table", "data-table");
  table.innerHTML = "<thead><tr><th>Time</th><th>Served model</th><th>In-tokens</th><th>Fallback</th><th>Status</th></tr></thead>";
  const tb = el("tbody");
  rows.forEach((r) => {  // newest first — current request is at the top
    const tr = el("tr");
    const t = el("td", "mono-cell", fmtClock(r.at)); t.title = fmtAgo(r.at); tr.appendChild(t);
    tr.appendChild(el("td", "mono-cell", servedRefOf(r)));
    tr.appendChild(el("td", "mono-cell", r.input_tokens != null ? String(r.input_tokens) : "—"));
    const fb = el("td");
    const fbb = badge(r.was_fallback ? "switched" : "primary", r.was_fallback ? "warn" : "ok");
    if (r.was_fallback && r.downgrade_reason) fbb.title = r.downgrade_reason;
    fb.appendChild(fbb); tr.appendChild(fb);
    const o = el("td");
    const ob = badge(r.outcome || "—", r.outcome === "routed" ? "ok" : "warn");
    if (r.error) ob.title = r.error;
    o.appendChild(ob); tr.appendChild(o);
    tb.appendChild(tr);
  });
  table.appendChild(tb);
  body.appendChild(table);
}

async function renderLimits() {
  const data = await api("/admin/api/quota");
  const body = byId("status-limits");
  body.innerHTML = "";
  if (!data.enabled) { body.appendChild(emptyState("▤", "Quota tracking is off", "Enable it under Features to watch free-tier budgets.", "Open Features", "features")); return; }
  const keys = Object.keys(data.providers || {});
  if (!keys.length) { body.appendChild(emptyState("▤", "No usage recorded yet", "Once requests flow, per-provider usage shows here.")); return; }
  const table = el("table", "data-table");
  table.innerHTML = "<thead><tr><th>Provider</th><th>Status</th><th>Utilization</th><th>Detail</th></tr></thead>";
  const tb = el("tbody");
  keys.forEach((k) => {
    const q = data.providers[k] || {};
    const tr = el("tr");
    tr.appendChild(el("td", null, k));
    const st = el("td"); st.appendChild(badge(q.status || "ok", statusKind(q.status))); tr.appendChild(st);
    const util = typeof q.utilization === "number" ? Math.round(q.utilization * 100) : null;
    const ut = el("td");
    if (util !== null) {
      const bar = el("div", "meter");
      const fill = el("div", `meter-fill ${statusKind(q.status)}`);
      fill.style.width = `${Math.min(100, util)}%`;
      bar.appendChild(fill);
      ut.append(bar, el("span", "meter-label", `${util}%`));
    } else ut.textContent = "—";
    tr.appendChild(ut);
    tr.appendChild(el("td", null, q.seconds_to_exhaustion ? `~${Math.round(q.seconds_to_exhaustion)}s to limit` : ""));
    tb.appendChild(tr);
  });
  table.appendChild(tb);
  body.appendChild(table);
  const note = el("p", "guide-note");
  note.innerHTML = "Near 100%? Freeway routes away to your other providers and fails over at the cap "
    + "(daily limits reset at UTC midnight). Keep favourites / fallbacks from <strong>2–3 different "
    + "providers</strong> so a single provider's cap can't stop you.";
  body.appendChild(note);
}

async function renderHealth() {
  const data = await api("/admin/api/health");
  const body = byId("status-health");
  body.innerHTML = "";
  if (!data.enabled) { body.appendChild(emptyState("♥", "Health probes are off", "Enable them under Features for live provider stability.", "Open Features", "features")); return; }
  const keys = Object.keys(data.targets || {});
  if (!keys.length) { body.appendChild(emptyState("♥", "No samples yet", "Probes run periodically — check back shortly.")); return; }
  const grid = el("div", "card-grid");
  keys.forEach((k) => {
    const h = data.targets[k] || {};
    const verdict = h.verdict || "—";
    const c = el("div", "mini-card");
    const top = el("div", "mini-card-top");
    top.append(el("strong", null, k), badge(verdict, statusKind(verdict)));
    c.appendChild(top);
    const score = h.stability_score ?? h.score;
    const samples = h.sample_count ?? h.samples ?? 0;
    const parts = [`stability ${score !== undefined && score !== null ? score : "—"}`, `${samples} samples`];
    if (h.p95_ms != null) parts.push(`p95 ${h.p95_ms}ms`);
    if (h.uptime != null) parts.push(`${h.uptime}% up`);
    c.appendChild(el("div", "mini-card-sub", parts.join(" · ")));
    grid.appendChild(c);
  });
  body.appendChild(grid);
}

async function renderCache() {
  const data = await api("/admin/api/cache");
  const body = byId("status-cache");
  body.innerHTML = "";
  const grid = el("div", "stat-grid");
  const s = data.stats || {};
  grid.appendChild(statCard("Status", data.enabled ? "enabled" : "disabled", "", data.enabled ? "ok" : "warn"));
  grid.appendChild(statCard("Entries", `${s.entries || 0}`, `window ${data.window}`));
  grid.appendChild(statCard("Hits", `${s.hits || 0}`));
  grid.appendChild(statCard("Misses", `${s.misses || 0}`));
  grid.appendChild(statCard("TTL", `${data.ttl_seconds}s`));
  body.appendChild(grid);
  if (data.enabled) {
    const bar = el("div", "toolbar");
    const clear = el("button", "mini-button ghost", "Clear cache");
    clear.disabled = !(s.entries || 0);
    clear.addEventListener("click", async () => {
      await api("/admin/api/cache/clear", { method: "POST", body: "{}" });
      showMessage("Cache cleared", "ok");
      await renderCache();
    });
    bar.appendChild(clear);
    body.appendChild(bar);
  } else {
    body.appendChild(emptyState("⚡", "Cache is off", "Enable it under Features to instantly replay identical no-tool requests.", "Open Features", "features"));
  }
}

function tierKind(tier) {
  const t = String(tier || "");
  if (t === "S+" || t === "S" || t === "A+" || t === "A") return "ok";
  if (t === "A-" || t === "B+" || t === "B") return "warn";
  if (t === "C") return "error";
  return "neutral";
}

async function renderHelp() {
  const body = byId("status-guide");
  body.innerHTML = `
  <div class="guide">
    <section class="guide-card">
      <h3>What is Freeway?</h3>
      <p>Freeway is one local endpoint that sits between your coding tools (Claude Code, Codex,
      or any OpenAI-compatible client) and 26 AI providers (free-tier cloud + local). It translates
      protocols, picks a working model, fails over when one is down, and trims oversized
      requests so free tiers don't reject them.</p>
    </section>

    <section class="guide-card">
      <h3>Quick start (3 steps)</h3>
      <ol class="guide-steps">
        <li><strong>Add a provider key.</strong> Go to <em>Configure → Providers</em>, paste an API key
        (e.g. Cerebras, Groq), and click <em>Apply</em>. Hit <em>Refresh models</em> on that provider card.</li>
        <li><strong>Pick a model.</strong> Open <em>Monitor → Models</em>, find a <span class="badge ok">ready</span>
        model, and click <em>Use</em>. (Click <em>“+ Fallback”</em> on other models to build a failover chain.)</li>
        <li><strong>Point your tool at Freeway.</strong> Run <code>freeway</code> to start the proxy, then
        <code>freeway-claude</code> (or <code>freeway-codex</code>) in another terminal.</li>
      </ol>
    </section>

    <section class="guide-card">
      <h3>Get your API keys</h3>
      <p>Freeway routes across the providers below — most offer a free or generous free-tier plan.
      Open a link, create a key, then paste it under <em>Configure → Providers</em> and click <em>Apply</em>.
      Add several — Freeway rotates and fails over between them so you rarely hit a limit.</p>
      <div id="guideKeyLinks"><p class="guide-note">Loading providers…</p></div>
    </section>

    <section class="guide-card">
      <h3>Commands</h3>
      <table class="data-table">
        <tbody>
          <tr><td><code>freeway</code></td><td>Start the proxy server (reads <code>~/.freeway/.env</code>).</td></tr>
          <tr><td><code>freeway-init</code></td><td>Create the config file <code>~/.freeway/.env</code>.</td></tr>
          <tr><td><code>freeway-claude</code></td><td>Launch Claude Code pointed at Freeway.</td></tr>
          <tr><td><code>freeway-codex</code></td><td>Launch Codex pointed at Freeway.</td></tr>
          <tr><td><code>freeway-server</code></td><td>Alias for <code>freeway</code>.</td></tr>
        </tbody>
      </table>
      <p class="guide-note">All settings live in this UI — you rarely need to touch <code>~/.freeway/.env</code> by hand.</p>
    </section>

    <section class="guide-card">
      <h3>The pages</h3>
      <table class="data-table">
        <thead><tr><th>Page</th><th>What it's for</th></tr></thead>
        <tbody>
          <tr><td><strong>Dashboard</strong></td><td>At-a-glance: is Freeway running, active model, providers ready, cache hit-rate.</td></tr>
          <tr><td><strong>Models</strong></td><td>The picker. Every model you can route to + live status. Sort by Quality/Latency/Name, filter by Ready/All/★ Favs, star favourites, one-click <em>Use</em> / <em>+Fallback</em>. <em>“ready”</em> is provider-level; use <em>⚡ Verify all</em> or a model's <em>Test</em> to ping each model for real (results are saved).</td></tr>
          <tr><td><strong>Activity</strong></td><td>Every request, newest first: time, the model that served it, input tokens, primary-vs-fallback, and status — with a "most recent" card at the top showing what's running right now.</td></tr>
          <tr><td><strong>Limits</strong></td><td>Free-tier token usage vs each provider's per-minute budget.</td></tr>
          <tr><td><strong>Health</strong></td><td>Live provider stability + latency from background probes.</td></tr>
          <tr><td><strong>Cache</strong></td><td>Response-cache hits/misses; clear it here.</td></tr>
          <tr><td><strong>Providers</strong></td><td>Connect providers — API keys, local endpoints, proxies.</td></tr>
          <tr><td><strong>Routing</strong></td><td>Default model, fallback chain, @-directives, and auto-fit (the 413 fix).</td></tr>
          <tr><td><strong>Features</strong></td><td>Toggle health probes, quota tracking, request inspector, cache, web tools.</td></tr>
          <tr><td><strong>Privacy</strong></td><td>Hard rules: never send prompts to training / non-local / out-of-region providers.</td></tr>
          <tr><td><strong>Messaging</strong></td><td>Optional Discord / Telegram bot + voice-note transcription for remote sessions.</td></tr>
        </tbody>
      </table>
    </section>

    <section class="guide-card">
      <h3>Key concepts</h3>
      <div class="guide-concept"><h4>Favourites vs fallback</h4>
      <p><strong>★ Favourite</strong> is a personal shortlist/bookmark — it does not change routing. Use the
      <em>★ Favs</em> filter to find your starred models quickly. <strong>Fallback</strong> is real routing:
      <em>“+ Fallback”</em> adds a model to the failover chain that's tried, in order, when your primary fails.</p></div>
      <div class="guide-concept"><h4>Fallback / auto-failover (never stops)</h4>
      <p>If your model's provider is down, rate-limited, or circuit-open, Freeway skips it and tries the next
      model in your fallback chain — no error to you. This works <strong>mid-request</strong> too: if a provider
      accepts a request but then fails before producing any output (rate-limit, overload, 5xx, bad model),
      Freeway re-routes to the next model and still completes the response. With a few keys across providers,
      a run keeps going instead of dying on one provider's hiccup.</p></div>
      <div class="guide-concept"><h4>Free-tier limits &amp; fallback (spread across providers)</h4>
      <p>Each free provider has its own cap (e.g. <strong>OpenRouter = 50 requests/day</strong>, resets at UTC
      midnight; see <em>Monitor → Limits</em> for live usage). As a provider nears its limit, Freeway routes
      <em>away</em> to your other providers, and fails over at 100%. So pick your favourites / fallback chain
      from <strong>2–3 different providers</strong> — if <em>every</em> model you select is from one provider,
      then when that provider's cap is hit there's nowhere to fall back and requests stop until it resets. A
      mixed chain (e.g. a big-context provider like Gemini + a couple of fast ones) keeps you running all day.</p></div>
      <div class="guide-concept"><h4>@-Directives (per-message model switching)</h4>
      <p>Define aliases in <em>Routing → Inline @-Directives</em> as <code>key=provider/model</code>, e.g.
      <span class="mono-example">fast=groq/llama-3.3-70b-versatile, big=cerebras/gpt-oss-120b</span>
      Then type <code>@big refactor this</code> in a prompt to route that one message to Cerebras.</p></div>
      <div class="guide-concept"><h4>Auto-fit (the “request too large” / 413 · 400 fix)</h4>
      <p>Editors like Claude Code send every tool's schema plus the whole conversation on every request (a real
      47-tool payload is ~31k tokens, 79% of it tool schemas), which grows past small free limits. When a request
      is over budget, auto-fit first <strong>compresses the tool schemas</strong> — shortens each tool's description
      and strips schema prose while <strong>keeping every tool</strong> — taking that ~31k request to ~13k. Only if
      it still doesn't fit does it drop the largest non-essential tools (core coding tools always kept), then the
      oldest whole turns. <strong>Default is automatic</strong>: the budget is 90% of the routed model's context, so
      it only touches requests that would exceed the model's own window (working requests are untouched). Set
      <em>Routing → Auto-fit Budget</em> explicitly only for tiers that cap below their advertised context, and set
      <code>AUTO_FIT_COMPRESS_TOOLS=false</code> to disable compression.</p>
      <p><strong>Hard ~8k tiers &amp; Claude Code:</strong> Claude Code's system prompt alone is a ~6.5k floor, so
      even full compression can't fit it under a hard 8k cap — use a <strong>big-context free provider</strong>
      (Gemini, NVIDIA NIM) as the primary for Claude Code, and reserve tiny 8k tiers for <strong>Codex</strong>
      (which sends ~4k and fits easily).</p></div>
      <div class="guide-concept"><h4>Bounded long sessions (compaction)</h4>
      <p>Because the whole conversation is resent each turn, long sessions grow. <code>freeway-claude</code> sizes
      Claude Code's compaction window to your budget / model context, so the conversation compacts and stays
      bounded instead of overflowing. Pair a <strong>big-context free provider</strong> (Gemini, NVIDIA NIM) with
      <strong>multiple keys</strong> (<code>PROVIDER_API_KEY=k1,k2,k3</code>, rotated round-robin for more per-minute
      budget) for long, uninterrupted sessions. <strong>Codex</strong> also sends ~10× smaller requests than Claude Code.</p></div>
      <div class="guide-concept"><h4>Picking the model</h4>
      <p><em>Use</em> on the Models page sets the default that every request routes to — you do <strong>not</strong> need to
      pick a model in the CLI. Freeway maps Claude Code's request to the current default on <strong>every request</strong>,
      so a change applies to the <strong>next request automatically</strong> (no restart). The only exception: if you pinned a
      specific model with Claude Code's own <code>/model</code> picker, that per-session choice overrides the default until
      you clear it or restart <code>freeway-claude</code>.</p></div>
      <div class="guide-concept"><h4>“Ready” vs “Verified”</h4>
      <p><strong>Ready</strong> is <em>provider-level</em>: if a provider's key works and it isn't rate-limited,
      down, or circuit-broken, all of its models show ready — an optimistic count, not a per-model test.
      To confirm an individual model, hit <em>⚡ Verify all</em> (pings every shown model) or a model's <em>Test</em>.
      Each tested model then regroups by its real result: <strong>✓ verified</strong> (Ready), <strong>⏳ Busy — retry later</strong>
      (rate-limited or overloaded — temporary), or <strong>✗ Verified down</strong> (unavailable / no key / unreachable).
      Results are saved until you re-check; real availability is otherwise proven at request time by failover.</p></div>
    </section>

    <section class="guide-card">
      <h3>Troubleshooting</h3>
      <table class="data-table">
        <tbody>
          <tr><td><strong>413 “request too large”</strong></td><td>Set <em>Routing → Auto-fit Budget</em> (e.g. 9000), or switch to a higher-limit provider on the Models page.</td></tr>
          <tr><td><strong>Port already in use</strong></td><td>Change <em>Providers → Runtime → PORT</em> (default 8082) and Apply.</td></tr>
          <tr><td><strong>“no key” on a provider</strong></td><td>Add its API key under Providers, Apply, then Refresh models.</td></tr>
          <tr><td><strong>Command not found</strong></td><td>Open a fresh terminal after install (PATH updates only apply to new shells).</td></tr>
          <tr><td><strong>Config location</strong></td><td><code>~/.freeway/.env</code> (created by <code>freeway-init</code>); logs in <code>~/.freeway/logs/</code>.</td></tr>
        </tbody>
      </table>
    </section>
  </div>`;

  // Populate the "Get your API keys" table from the live provider catalog so the
  // links always match the providers Freeway actually supports.
  const wrap = byId("guideKeyLinks");
  if (!wrap) return;
  const kd = await api("/admin/api/models").catch(() => null);
  if (!kd || !kd.providers) { wrap.innerHTML = '<p class="guide-note">Could not load the provider list — open Providers to add keys.</p>'; return; }
  const byName = (a, b) => (a.display_name || "").localeCompare(b.display_name || "");
  const remote = kd.providers.filter((p) => !p.is_local).sort(byName);
  const local = kd.providers.filter((p) => p.is_local).sort(byName);
  const linkCell = (p) => p.credential_url
    ? `<a href="${p.credential_url}" target="_blank" rel="noopener noreferrer">Create key ↗</a>`
    : "—";
  const remoteRows = remote.map((p) =>
    `<tr><td><strong>${p.display_name}</strong>${p.configured ? ' <span class="badge ok">key set</span>' : ""}</td>` +
    `<td><code>${p.credential_env || ""}</code></td><td>${linkCell(p)}</td></tr>`).join("");
  const localRows = local.map((p) =>
    `<tr><td><strong>${p.display_name}</strong></td>` +
    `<td colspan="2" class="guide-note">Runs locally — no key. Set its URL under Providers.</td></tr>`).join("");
  wrap.innerHTML =
    `<table class="data-table"><thead><tr><th>Provider</th><th>Env var</th><th>Get a key</th></tr></thead>` +
    `<tbody>${remoteRows}${localRows}</tbody></table>`;
}

function statusKind(status) {
  const s = String(status || "").toLowerCase();
  if (["ok", "closed", "healthy", "active", "reachable", "configured", "running"].includes(s)) return "ok";
  if (["warning", "half_open", "unknown", "missing_key"].includes(s)) return "warn";
  if (["exhausted", "open", "blocked", "offline", "error", "not active", "down"].includes(s)) return "error";
  return "neutral";
}

// ---- Providers config (keys) ----
function renderProviders(providerStatus) {
  const grid = byId("providerGrid");
  if (!grid) return;
  grid.innerHTML = "";
  providerStatus.forEach((provider) => {
    const card = el("article", "provider-card");
    card.dataset.provider = provider.provider_id;
    const title = el("div", "provider-title");
    title.innerHTML = `<strong>${provider.display_name || provider.provider_id}</strong>`;
    title.appendChild(el("span", `status-pill ${statusKind(provider.status)}`, provider.label));
    const meta = el("div", "provider-meta", provider.kind === "local" ? provider.base_url || "No local URL configured" : provider.credential_env);
    const button = el("button", "test-button", provider.kind === "local" ? "Test" : "Refresh models");
    button.type = "button";
    button.addEventListener("click", () => testProvider(provider.provider_id, button));
    card.append(title, meta, button);
    grid.appendChild(card);
  });
}
function updateProviderCard(id, status, label, meta) {
  const card = document.querySelector(`[data-provider="${id}"]`);
  if (!card) return;
  const pill = card.querySelector(".status-pill");
  pill.className = `status-pill ${statusKind(status)}`;
  pill.textContent = label;
  if (meta) card.querySelector(".provider-meta").textContent = meta;
}

// ---- config field rendering (settings) ----
function sourceLabel(source) {
  const labels = { default: "default", template: "template", repo_env: "repo .env", managed_env: "", explicit_env_file: "FREEWAY_ENV_FILE", process: "process env" };
  return Object.prototype.hasOwnProperty.call(labels, source) ? labels[source] : source;
}
function sourceText(field) {
  const parts = [];
  const label = sourceLabel(field.source);
  if (label) parts.push(label);
  if (field.locked) parts.push("locked");
  return parts.join(" ");
}

function renderSections(sections, fields) {
  CONFIG_VIEWS.forEach((v) => { const c = byId(v.containerId); if (c) c.innerHTML = ""; });
  const sectionById = new Map(sections.map((s) => [s.id, s]));
  const bySection = new Map();
  sections.forEach((s) => bySection.set(s.id, []));
  fields.forEach((f) => { if (!bySection.has(f.section)) bySection.set(f.section, []); bySection.get(f.section).push(f); });
  CONFIG_VIEWS.forEach((view) => {
    const container = byId(view.containerId);
    if (!container) return;
    view.sections.forEach((sid) => {
      const section = sectionById.get(sid);
      const fs = bySection.get(sid) || [];
      if (!section || !fs.length) return;
      const sEl = el("section", "settings-section");
      sEl.id = `section-${section.id}`;
      const heading = el("div", "section-heading");
      heading.innerHTML = `<div><h3>${section.label}</h3><p>${section.description}</p></div>`;
      sEl.appendChild(heading);
      const grid = el("div", "field-grid");
      fs.forEach((f) => grid.appendChild(renderField(f)));
      sEl.appendChild(grid);
      if (fs.some((f) => f.advanced)) {
        const t = el("button", "ghost-button advanced-toggle", "Show advanced");
        t.type = "button";
        t.addEventListener("click", () => { const on = sEl.classList.toggle("show-advanced"); t.textContent = on ? "Hide advanced" : "Show advanced"; });
        sEl.appendChild(t);
      }
      container.appendChild(sEl);
    });
  });
}

function renderField(field) {
  const wrap = el("div", `field${field.advanced ? " advanced-field" : ""}`);
  wrap.dataset.key = field.key;
  const label = el("label");
  label.htmlFor = `field-${field.key}`;
  label.appendChild(el("span", null, field.label));
  const source = sourceText(field);
  if (source) { const sourceEl = el("span", "field-source"); sourceEl.textContent = source; label.appendChild(sourceEl); }
  const input = inputForField(field);
  input.id = `field-${field.key}`;
  input.dataset.key = field.key;
  input.dataset.original = field.value || "";
  input.dataset.secret = field.secret ? "true" : "false";
  input.dataset.configured = field.configured ? "true" : "false";
  input.disabled = field.locked;
  input.addEventListener("input", updateDirtyState);
  input.addEventListener("change", updateDirtyState);
  wrap.append(label, input);
  if (field.description) wrap.appendChild(el("div", "field-description", field.description));
  // The fallback chain is a comma-separated string in a single-line input that
  // truncates — show the parsed, ordered entries as numbered removable chips so it's
  // obvious how many models are actually set.
  if (field.key === "MODEL_FALLBACKS") wrap.appendChild(fallbackChips(input));
  return wrap;
}

function fallbackChips(input) {
  const box = el("div", "chain-chips");
  const paint = () => {
    box.innerHTML = "";
    const items = (input.value || "").split(",").map((s) => s.trim()).filter(Boolean);
    if (!items.length) {
      box.appendChild(el("span", "chain-empty", "No fallbacks set — add them from the Models page (“+ Fallback”)."));
      return;
    }
    items.forEach((ref, idx) => {
      const chip = el("span", "chain-chip");
      chip.appendChild(el("span", "chain-num", String(idx + 1)));
      chip.appendChild(el("span", "chain-ref", ref));
      const x = el("button", "chain-x", "×");
      x.type = "button";
      x.title = "Remove from chain";
      x.addEventListener("click", () => {
        input.value = items.filter((_, i) => i !== idx).join(",");
        input.dispatchEvent(new Event("input", { bubbles: true }));
        paint();
      });
      chip.appendChild(x);
      box.appendChild(chip);
    });
  };
  input.addEventListener("input", paint);
  paint();
  return box;
}

function inputForField(field) {
  if (field.type === "boolean") {
    const i = document.createElement("input");
    i.type = "checkbox";
    i.checked = String(field.value).toLowerCase() === "true";
    i.dataset.original = i.checked ? "true" : "false";
    return i;
  }
  if (field.type === "tri_boolean") {
    const s = document.createElement("select");
    [["", "Inherit"], ["true", "Enabled"], ["false", "Disabled"]].forEach(([v, l]) => s.appendChild(option(v, l)));
    s.value = field.value || "";
    return s;
  }
  if (field.type === "select") {
    const s = document.createElement("select");
    field.options.forEach((v) => s.appendChild(option(v, v)));
    s.value = field.value || field.options[0] || "";
    return s;
  }
  if (field.type === "textarea") {
    const t = document.createElement("textarea");
    t.value = field.value || "";
    return t;
  }
  const i = document.createElement("input");
  i.type = field.type === "number" ? "number" : "text";
  if (field.type === "secret") {
    i.type = "password";
    i.placeholder = field.configured ? "Configured — enter a new value to replace" : "Not configured";
    i.value = "";
    i.autocomplete = "off";
  } else i.value = field.value || "";
  if (field.key.startsWith("MODEL")) i.setAttribute("list", "model-options");
  return i;
}
function option(value, label) { const o = document.createElement("option"); o.value = value; o.textContent = label; return o; }
function readFieldValue(input) {
  if (input.type === "checkbox") return input.checked ? "true" : "false";
  if (input.dataset.secret === "true" && input.dataset.configured === "true") return input.value ? input.value : MASKED_SECRET;
  return input.value;
}
function changedValues() {
  const values = {};
  document.querySelectorAll("[data-key]").forEach((input) => {
    if (input.disabled || !input.matches("input, select, textarea")) return;
    const v = readFieldValue(input);
    if (v !== input.dataset.original) values[input.dataset.key] = v;
  });
  return values;
}
function updateDirtyState() {
  const count = Object.keys(changedValues()).length;
  byId("dirtyState").textContent = count === 0 ? "No changes" : `${count} unsaved change${count === 1 ? "" : "s"}`;
  byId("applyButton").disabled = count === 0;
}
async function validate(showResult = true) {
  const result = await api("/admin/api/config/validate", { method: "POST", body: JSON.stringify({ values: changedValues() }) });
  if (showResult) showValidationResult(result);
  return result;
}
function showValidationResult(result) {
  if (result.valid) showMessage("Config looks valid", "ok");
  else showMessage(result.errors.join("; "), "error");
}
async function apply() {
  const result = await api("/admin/api/config/apply", { method: "POST", body: JSON.stringify({ values: changedValues() }) });
  if (!result.applied) { showValidationResult(result); return; }
  const restart = result.restart || {};
  if (restart.required && restart.automatic) {
    showMessage("Applied. Restarting server…", "ok");
    byId("applyButton").disabled = true;
    setTimeout(() => { window.location.href = restart.admin_url || "/admin"; }, 1600);
    return;
  }
  const pending = restart.required ? restart.fields || [] : result.pending_fields || [];
  await load();
  showMessage(pending.length ? `Applied. Restart freeway to use: ${pending.join(", ")}` : "Applied", "ok");
}
async function refreshLocalStatus() {
  const result = await api("/admin/api/providers/local-status");
  result.providers.forEach((p) => {
    const meta = p.status_code ? `${p.base_url} returned HTTP ${p.status_code}` : p.base_url;
    updateProviderCard(p.provider_id, p.status, p.label, meta);
  });
}
async function testProvider(id, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Testing…";
  try {
    const result = await api(`/admin/api/providers/${id}/test`, { method: "POST", body: "{}" });
    if (result.ok) {
      updateProviderCard(id, "reachable", `${result.models.length} models`, result.models.slice(0, 3).join(", ") || "No models returned");
      syncModelDatalist(result.models.map((m) => `${id}/${m}`));
    } else updateProviderCard(id, "offline", result.error_type, result.error_type);
  } finally { button.disabled = false; button.textContent = original; }
}
function syncModelDatalist(refs) {
  let dl = byId("model-options");
  if (!dl) { dl = document.createElement("datalist"); dl.id = "model-options"; document.body.appendChild(dl); }
  refs.forEach((r) => dl.appendChild(option(r, r)));
}
function showMessage(message, kind = "") {
  const area = byId("messageArea");
  area.textContent = message;
  area.className = `message-area ${kind}`.trim();
}

byId("validateButton").addEventListener("click", () => validate(true));
byId("applyButton").addEventListener("click", apply);
load().catch((e) => showMessage(e.message, "error"));
