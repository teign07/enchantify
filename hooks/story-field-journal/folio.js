/**
 * Cinematic Story-Field Journal — player folio UI
 * Reads /api/folio; Mission Control stays on :9191
 */

const PLAYER = new URLSearchParams(location.search).get("player") || "bj";
const REFRESH_MS = 45_000;

const phaseColor = {
  dormant: "#6b7280",
  setup: "#60a5fa",
  rising: "#fbbf24",
  climax: "#fb7185",
  resolution: "#4ade80",
  permanent: "#a78bfa",
};

let folioState = null;
let focusedThreadId = null;

// ── Three.js ley field ──────────────────────────────────────────────
function initField() {
  const canvas = document.getElementById("field-canvas");
  if (!window.THREE || !canvas) return null;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 120);
  camera.position.z = 28;

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);

  const count = 900;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 80;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 40;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color: 0x5ee7ff,
    size: 0.12,
    transparent: true,
    opacity: 0.55,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const points = new THREE.Points(geo, mat);
  scene.add(points);

  const grid = new THREE.GridHelper(90, 40, 0x1a3a4a, 0x0a1820);
  grid.position.y = -12;
  grid.material.opacity = 0.25;
  grid.material.transparent = true;
  scene.add(grid);

  const threadNodes = [];
  const nodeGroup = new THREE.Group();
  scene.add(nodeGroup);

  let t = 0;
  function resize() {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  }
  window.addEventListener("resize", resize);

  function rebuildNodes(threads) {
    while (nodeGroup.children.length) nodeGroup.remove(nodeGroup.children[0]);
    threadNodes.length = 0;
    const n = Math.min(threads.length, 24);
    for (let i = 0; i < n; i++) {
      const angle = (i / n) * Math.PI * 2;
      const r = 8 + (threads[i].belief || 0) * 0.04;
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.35 + Math.min(threads[i].belief || 0, 80) / 120, 12, 12),
        new THREE.MeshBasicMaterial({
          color: phaseColor[threads[i].phase] || 0x5ee7ff,
          transparent: true,
          opacity: focusedThreadId === threads[i].id ? 1 : 0.75,
        })
      );
      sphere.position.set(Math.cos(angle) * r, Math.sin(i * 0.7) * 2, Math.sin(angle) * r);
      sphere.userData = threads[i];
      nodeGroup.add(sphere);
      threadNodes.push(sphere);
    }
  }

  function animate() {
    requestAnimationFrame(animate);
    t += 0.004;
    points.rotation.y = t * 0.15;
    nodeGroup.rotation.y = t * 0.08;
    threadNodes.forEach((node, i) => {
      node.position.y = Math.sin(t * 2 + i) * 0.4;
    });
    renderer.render(scene, camera);
  }
  animate();

  return { rebuildNodes };
}

// ── Data + render ───────────────────────────────────────────────────
async function fetchFolio() {
  const res = await fetch(`/api/folio?player=${encodeURIComponent(PLAYER)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`folio ${res.status}`);
  return res.json();
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function renderThreads(threads, field) {
  const list = document.getElementById("thread-list");
  list.innerHTML = threads
    .map(
      (t) => `
    <li data-id="${esc(t.id)}" class="${focusedThreadId === t.id ? "focused" : ""}">
      <span class="phase-dot" style="background:${phaseColor[t.phase] || phaseColor.dormant};color:${phaseColor[t.phase] || phaseColor.dormant}"></span>
      <span class="name">${esc(t.name)}</span>
      <span class="meta">belief ${t.belief} · ${esc(t.phase)}</span>
    </li>`
    )
    .join("");

  list.querySelectorAll("li").forEach((li) => {
    li.addEventListener("click", () => {
      focusedThreadId = li.dataset.id;
      renderThreads(threads, field);
      if (field) field.rebuildNodes(threads);
    });
  });

  if (field) field.rebuildNodes(threads);
}

function renderToday(data) {
  const mobile = data.mobile || {};
  const today = mobile.today || {};
  const page = mobile.page || {};
  const scene = mobile.scene || {};
  const card = data.player_card || {};

  document.getElementById("stat-belief").textContent = card.belief ?? "—";
  document.getElementById("stat-chapter").textContent = card.chapter ?? "—";
  document.getElementById("stat-page").textContent = page.page_type || page.page_label || "—";

  document.getElementById("today-kicker").textContent = today.block || page.page_type || "Today";
  document.getElementById("today-title").textContent = today.title || page.page_label || "The Book is open";
  document.getElementById("today-schedule").textContent = [today.day, today.now, today.next]
    .filter(Boolean)
    .join(" · ");

  document.getElementById("today-note").textContent = today.note || "";

  const img = document.getElementById("today-image");
  const ph = document.getElementById("hero-placeholder");
  img.hidden = true;
  ph.hidden = false;
  img.onload = () => {
    img.hidden = false;
    ph.hidden = true;
  };
  img.src = `/api/widget-image?t=${Date.now()}`;

  const excerpt = document.getElementById("scene-excerpt");
  if (scene.text) {
    excerpt.textContent = scene.text.slice(0, 2800);
  } else {
    excerpt.textContent =
      "No live scene packet on the desk. Open the Book in Telegram to write the next page into the field.";
  }

  const choices = document.getElementById("choice-sigils");
  const ch = mobile.choices || scene.choices || [];
  choices.innerHTML = ch.length
    ? ch
        .map((c) => {
          const kind = (c.kind || "").toLowerCase();
          const cls = kind === "life" ? "life" : kind === "arc" ? "arc" : kind === "surprise" ? "surprise" : "";
          return `<li>${cls ? `<span class="tag ${cls}">${esc(c.kind)}</span>` : ""}${esc(c.text)}</li>`;
        })
        .join("")
    : "<li class='muted'>Choices appear when a scene is live in the outbox.</li>";

  const quests = document.getElementById("quest-list");
  quests.innerHTML = (card.quests || [])
    .map((q) => `<li><strong>${esc(q.title)}</strong> — ${esc(q.status)}${q.note ? ` · ${esc(q.note)}` : ""}</li>`)
    .join("") || "<li>No quests on the Inside Cover yet.</li>";
}

function renderCompass(mobile) {
  const c = mobile.compass || {};
  const el = document.getElementById("compass-body");
  if (!c.status || c.status === "idle") {
    el.innerHTML = "<p>The Compass rests. Rub it in play when you are ready for a run.</p>";
    return;
  }
  el.innerHTML = `<dl>${Object.entries(c)
    .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(String(v))}</dd>`)
    .join("")}</dl>`;
}

function renderEnchantments(mobile) {
  const el = document.getElementById("enchantments-body");
  el.innerHTML =
    "<p>Your Flyleaf spells are invoked in Telegram during active play. This tab will list known enchantments and daily offers when mutation routes land on the gateway.</p>";
  const page = mobile.page || {};
  if (page.enchantment_opportunity) {
    el.innerHTML += `<p class="margin-note">${esc(page.enchantment_opportunity)}</p>`;
  }
}

function renderLibrary(data) {
  const lib = data.mobile?.library || {};
  const threads = data.threads || [];
  document.getElementById("library-body").innerHTML = `
    <p>${esc(lib.story_threads_source || "lore/threads.md")} · ${threads.length} active threads in the register.</p>
    <ul class="thread-list" style="margin-top:1rem">
      ${threads.map((t) => `<li><span class="name">${esc(t.name)}</span><span class="meta">${esc(t.status)}</span></li>`).join("")}
    </ul>
    <p style="margin-top:1rem;font-family:var(--font-mono);font-size:0.7rem;color:var(--muted)">
      Bleed: ${esc(lib.bleed_archive_source || "")} · Letters: ${esc(lib.letters_source || "")}
    </p>`;
}

function renderDesk(mobile) {
  const desk = mobile.desk || {};
  const margins = mobile.margins || [];
  const pending = desk.pending_actions || [];
  document.getElementById("desk-body").innerHTML = `
    <h3 style="font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--hud-cyan)">Pending</h3>
    <ul>${pending.length ? pending.map((p) => `<li>${esc(p.proposal || p.chapter || JSON.stringify(p))}</li>`).join("") : "<li>Nothing waiting at the Desk.</li>"}</ul>
    <h3 style="margin-top:1rem;font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--hud-violet)">Support traces</h3>
    <p style="font-size:0.88rem">${esc(desk.support?.inkrest?.latest?.word || "—")} · Inkrest latest mood word</p>`;
  renderMargins(margins);
}

function renderMargins(margins) {
  document.getElementById("margin-feed").innerHTML = (margins || [])
    .map(
      (m) => `<li><span class="kind">${esc(m.kind)}</span> <strong>${esc(m.title)}</strong><br>${esc(m.text)}</li>`
    )
    .join("");
}

function renderRails(sc) {
  const rails = document.getElementById("scene-rails");
  if (!sc || !Object.keys(sc).length) {
    rails.innerHTML = "<dt>—</dt><dd>Awaiting scene contract</dd>";
    return;
  }
  const picks = [
    ["mode", sc.scene_mode],
    ["page", sc.page_type],
    ["drama", sc.drama_budget],
    ["location", sc.current_location],
    ["lens", sc.story_lens],
  ].filter(([, v]) => v);
  rails.innerHTML = picks.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(String(v))}</dd>`).join("");
}

function renderHealth(data) {
  const nh = data.narrative_health || {};
  const phrase =
    nh.summary ||
    (nh.status === "OK"
      ? "The shelves are steady."
      : nh.status
        ? `Narrative health: ${nh.status}`
        : "The Book is awake.");
  document.getElementById("narrative-health").textContent = phrase;
  document.getElementById("freshness").textContent = `Updated ${esc(data.generated_at || "")}`;
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((btn) => {
    const on = btn.dataset.tab === name;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.panel !== name);
  });
}

function bindUi(field) {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  document.getElementById("btn-refresh").addEventListener("click", () => load(field));
  document.getElementById("btn-immersive").addEventListener("click", () => {
    document.body.classList.toggle("immersive");
  });
}

async function load(field) {
  try {
    const data = await fetchFolio();
    folioState = data;
    renderThreads(data.threads || [], field);
    renderToday(data);
    renderCompass(data.mobile || {});
    renderEnchantments(data.mobile || {});
    renderLibrary(data);
    renderDesk(data.mobile || {});
    renderRails(data.scene_contract || {});
    renderHealth(data);
  } catch (err) {
    document.getElementById("today-title").textContent = "The folio could not refresh";
    document.getElementById("today-note").textContent = String(err);
  }
}

const field = initField();
bindUi(field);
load(field);
setInterval(() => load(field), REFRESH_MS);
