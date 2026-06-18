/**
 * 3D Field Graph — explore present-moment connections
 */

const PLAYER = new URLSearchParams(location.search).get("player") || "bj";
const REFRESH_MS = 60_000;

const KINDS = ["player", "npc", "thread", "scene", "image", "object"];
const filters = new Set(KINDS);

let graphData = null;
let Graph = null;
let nodeById = new Map();

const el = {
  container: document.getElementById("graph-container"),
  filters: document.getElementById("filters"),
  inspector: document.getElementById("inspector"),
  insKind: document.getElementById("ins-kind"),
  insTitle: document.getElementById("ins-title"),
  insBody: document.getElementById("ins-body"),
  insMeta: document.getElementById("ins-meta"),
  insLinks: document.getElementById("ins-links"),
  insImageWrap: document.getElementById("ins-image-wrap"),
  insImage: document.getElementById("ins-image"),
  statNodes: document.getElementById("stat-nodes"),
  statLinks: document.getElementById("stat-links"),
};

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

async function fetchGraph() {
  const res = await fetch(`/api/graph?player=${encodeURIComponent(PLAYER)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`graph ${res.status}`);
  return res.json();
}

function filteredData(data) {
  const allowed = new Set(
    data.nodes.filter((n) => filters.has(n.kind)).map((n) => n.id)
  );
  return {
    nodes: data.nodes.filter((n) => allowed.has(n.id)),
    links: data.links.filter((l) => allowed.has(l.source) && allowed.has(l.target)),
  };
}

function initFilters() {
  el.filters.innerHTML = KINDS.map(
    (k) =>
      `<button type="button" class="filter-chip on" data-kind="${k}">${k}</button>`
  ).join("");
  el.filters.querySelectorAll(".filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.dataset.kind;
      if (filters.has(kind)) {
        filters.delete(kind);
        btn.classList.remove("on");
      } else {
        filters.add(kind);
        btn.classList.add("on");
      }
      if (graphData) renderGraph(graphData);
    });
  });
}

function linkColor(kind) {
  const map = {
    player_bond: "#f0b35a88",
    npc_stance: "#94a3b866",
    thread: "#5ee7ff55",
    anchors: "#b794f688",
    present: "#c084fcaa",
    in_scene: "#c084fc66",
    carries: "#d4a57455",
    portrayed: "#67e8f988",
    memory: "#64748b55",
  };
  return map[kind] || "#ffffff33";
}

function renderGraph(data) {
  const { nodes, links } = filteredData(data);
  nodeById = new Map(nodes.map((n) => [n.id, n]));

  el.statNodes.textContent = `${nodes.length} nodes`;
  el.statLinks.textContent = `${links.length} links`;

  const gData = {
    nodes: nodes.map((n) => ({
      ...n,
      val: n.size || 5,
    })),
    links: links.map((l) => ({
      ...l,
      color: linkColor(l.kind),
    })),
  };

  if (!Graph) {
    Graph = ForceGraph3D()(el.container)
      .backgroundColor("#04060c")
      .showNavInfo(false)
      .nodeLabel((n) => `${n.label} (${n.kind})`)
      .nodeColor((n) => n.color || "#94a3b8")
      .nodeOpacity(0.92)
      .linkOpacity(0.45)
      .linkWidth((l) => Math.max(0.2, (l.weight || 1) * 0.35))
      .linkDirectionalParticles((l) => (l.kind === "present" || l.kind === "anchors" ? 2 : 0))
      .linkDirectionalParticleWidth(0.5)
      .linkDirectionalParticleSpeed(0.004)
      .onNodeClick((node) => showInspector(node))
      .onNodeDoubleClick((node) => focusNode(node))
      .onBackgroundClick(() => hideInspector());

    Graph.d3Force("charge").strength(-120);
    Graph.d3Force("link").distance((l) => 28 / Math.max(0.4, l.weight || 1));
  }

  Graph.graphData(gData);

  const playerNode = nodes.find((n) => n.kind === "player");
  if (playerNode) {
    setTimeout(() => focusNode(playerNode, 800), 400);
  }
}

function focusNode(node, ms = 1200) {
  const dist = 140;
  Graph.cameraPosition(
    {
      x: node.x + dist * 0.4,
      y: node.y + dist * 0.25,
      z: node.z + dist,
    },
    node,
    ms
  );
}

function neighbors(nodeId) {
  if (!graphData) return [];
  const out = [];
  for (const l of graphData.links) {
    if (l.source === nodeId || l.target === nodeId) {
      const other = l.source === nodeId ? l.target : l.source;
      const n = nodeById.get(other);
      if (n) out.push({ node: n, link: l });
    }
  }
  return out.sort((a, b) => (b.link.weight || 0) - (a.link.weight || 0));
}

function showInspector(node) {
  el.inspector.hidden = false;
  el.insKind.textContent = node.kind;
  el.insTitle.textContent = node.label;

  const parts = [];
  if (node.detail) parts.push(node.detail);
  if (node.notes) parts.push(node.notes);
  if (node.status) parts.push(node.status);
  if (node.agenda) parts.push(`Agenda: ${node.agenda}`);
  el.insBody.textContent = parts.join("\n\n") || "—";

  const meta = [];
  if (node.score != null) meta.push(["Bond", `${node.score} (${node.tier || ""})`]);
  if (node.chapter) meta.push(["Chapter", node.chapter]);
  if (node.belief != null) meta.push(["Belief", node.belief]);
  if (node.phase) meta.push(["Phase", node.phase]);
  if (node.location) meta.push(["Location", node.location]);
  if (node.mode) meta.push(["Mode", node.mode]);
  if (node.palette) meta.push(["Palette", node.palette]);
  if (node.stance) meta.push(["Stance", node.stance]);
  el.insMeta.innerHTML = meta.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");

  if (node.image_url) {
    el.insImageWrap.hidden = false;
    el.insImage.src = node.image_url;
  } else {
    el.insImageWrap.hidden = true;
  }

  const nb = neighbors(node.id);
  el.insLinks.innerHTML = nb.length
    ? nb
        .map(
          ({ node: n, link }) =>
            `<li data-id="${esc(n.id)}"><strong>${esc(n.label)}</strong> · ${esc(link.kind)}${link.label ? ` (${esc(link.label)})` : ""}</li>`
        )
        .join("")
    : "<li>No edges in this filter set.</li>";

  el.insLinks.querySelectorAll("li[data-id]").forEach((li) => {
    li.addEventListener("click", () => {
      const n = nodeById.get(li.dataset.id);
      if (n) {
        showInspector(n);
        focusNode(n);
      }
    });
  });

  focusNode(node);
}

function hideInspector() {
  el.inspector.hidden = true;
}

async function load() {
  try {
    graphData = await fetchGraph();
    renderGraph(graphData);
  } catch (err) {
    el.inspector.hidden = false;
    el.insTitle.textContent = "Field could not load";
    el.insBody.textContent = String(err);
  }
}

initFilters();
document.getElementById("btn-refresh").addEventListener("click", load);
document.getElementById("btn-close").addEventListener("click", hideInspector);
document.getElementById("btn-center").addEventListener("click", () => {
  const p = [...nodeById.values()].find((n) => n.kind === "player");
  if (p && Graph) focusNode(p);
});

load();
setInterval(load, REFRESH_MS);

window.addEventListener("resize", () => {
  if (Graph) Graph.width(innerWidth).height(innerHeight);
});
