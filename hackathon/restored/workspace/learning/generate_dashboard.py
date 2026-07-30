#!/usr/bin/env python3
"""Generate the interactive learning dashboard HTML from graph.yaml + mastery-state.json."""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Ensure nix-profile site-packages is visible (nix python doesn't include it by default)
_nix_sp = Path.home() / ".nix-profile/lib/python3.11/site-packages"
if _nix_sp.exists() and str(_nix_sp) not in sys.path:
    sys.path.insert(0, str(_nix_sp))

import yaml

HERE = Path(__file__).resolve().parent
GRAPH_PATH = HERE / "graph.yaml"
STATE_PATH = HERE / "mastery-state.json"
OUTPUT_PATH = HERE / "dashboard.html"


def load_graph() -> list[dict]:
    with open(GRAPH_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("nodes", [])


def load_state() -> dict:
    with open(STATE_PATH) as f:
        return json.load(f)


def compute_downstream_counts(nodes: list[dict]) -> dict[str, int]:
    """For each node, count how many nodes transitively depend on it."""
    # Build reverse edge map: node_id -> set of nodes that require it
    dependents: dict[str, set] = {n["id"]: set() for n in nodes}
    for n in nodes:
        for req in n.get("requires", []):
            if req in dependents:
                dependents[req].add(n["id"])

    # BFS from each node to count transitive dependents
    counts: dict[str, int] = {}
    for node_id in dependents:
        visited = set()
        queue = list(dependents[node_id])
        while queue:
            curr = queue.pop()
            if curr in visited:
                continue
            visited.add(curr)
            queue.extend(dependents.get(curr, set()) - visited)
        counts[node_id] = len(visited)
    return counts


def build_data(nodes: list[dict], state: dict) -> dict:
    """Build the JSON data structure for the dashboard."""
    downstream = compute_downstream_counts(nodes)
    today = date.today().isoformat()

    # Build node list (lightweight for graph) and detail lookup (for sidebar)
    node_list = []
    node_detail = {}
    for n in nodes:
        node_id = n["id"]
        s = state.get(node_id, {})
        tier = s.get("tier", "untested")
        next_review = s.get("next_review")
        last_tested = s.get("last_tested")
        consecutive_passes = s.get("consecutive_passes", 0)

        overdue = False
        if next_review and next_review <= today:
            overdue = True

        # Lightweight node for graph rendering (no large text fields)
        node_list.append({
            "id": node_id,
            "name": n.get("name", node_id),
            "layer": n.get("layer", 0),
            "requires": n.get("requires", []),
            "tier": tier,
            "overdue": overdue,
            "downstream_count": downstream.get(node_id, 0),
        })

        # Detail data loaded on-demand (sidebar click)
        node_detail[node_id] = {
            "chapter": str(n.get("chapter", "")),
            "key_points": n.get("key_points", []),
            "why_it_matters": n.get("why_it_matters", ""),
            "next_review": next_review,
            "last_tested": last_tested,
            "consecutive_passes": consecutive_passes,
        }

    # Build edge list
    edges = []
    for n in nodes:
        for req in n.get("requires", []):
            edges.append({"source": req, "target": n["id"]})

    # Layer summary
    layers: dict[int, dict] = {}
    for n in node_list:
        layer = n["layer"]
        if layer not in layers:
            layers[layer] = {"total": 0, "untested": 0, "recognized": 0, "understood": 0, "mastered": 0}
        layers[layer]["total"] += 1
        layers[layer][n["tier"]] += 1

    layer_names = {0: "HAR Core", 1: "Noise + Asymmetry", 99: "Evaluation", 2: "Options", 3: "Microstructure", 4: "Cross-Asset"}

    layer_summary = []
    for layer_id in sorted(layers.keys()):
        info = layers[layer_id]
        layer_summary.append({
            "id": layer_id,
            "name": layer_names.get(layer_id, f"Layer {layer_id}"),
            **info,
        })

    # Due today (just IDs for count display)
    due_today = [n["id"] for n in node_list if n["overdue"]]

    return {
        "nodes": node_list,
        "edges": edges,
        "layers": layer_summary,
        "due_today": due_today,
        "detail": node_detail,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "today": today,
    }


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vol Learning Dashboard</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #0d1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --text-dim: #484f58;
  --red: #f85149;
  --orange: #e07d3c;
  --yellow: #f0db4f;
  --green: #3fb950;
  --blue: #58a6ff;
  --purple: #bc8cff;
  --sidebar-width: 380px;
  --header-height: 56px;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  overflow: hidden;
  height: 100vh;
  width: 100vw;
}

/* Header */
.header {
  height: var(--header-height);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 24px;
  z-index: 10;
  position: relative;
}

.header h1 {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.header-stats {
  display: flex;
  gap: 16px;
  align-items: center;
}

.stat-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.stat-badge .count {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 2px 8px;
  font-weight: 600;
  color: var(--text);
}

.stat-badge .count.urgent {
  background: rgba(248, 81, 73, 0.15);
  border-color: var(--red);
  color: var(--red);
}

/* Layer progress bars in header */
.layer-bars {
  display: flex;
  gap: 12px;
  margin-left: auto;
  align-items: center;
}

.layer-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.layer-bar:hover {
  background: var(--bg-tertiary);
}

.layer-bar.active {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
}

.bar-track {
  width: 48px;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* Main layout */
.main {
  display: flex;
  height: calc(100vh - var(--header-height));
}

/* Graph container */
.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.graph-container svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* Tooltip */
.tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 100;
  max-width: 280px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.tooltip.visible { opacity: 1; }

.tooltip .node-name {
  font-weight: 600;
  margin-bottom: 2px;
}

.tooltip .node-tier {
  color: var(--text-muted);
  font-size: 11px;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  transform: translateX(100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 20;
  padding: 20px;
}

.sidebar.open { transform: translateX(0); }

.sidebar-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 18px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background 0.15s;
}

.sidebar-close:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}

.sidebar h2 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  padding-right: 32px;
  line-height: 1.4;
}

.sidebar .tier-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  margin-bottom: 16px;
}

.tier-untested { background: rgba(248, 81, 73, 0.15); color: var(--red); }
.tier-recognized { background: rgba(224, 125, 60, 0.15); color: var(--orange); }
.tier-understood { background: rgba(240, 219, 79, 0.15); color: var(--yellow); }
.tier-mastered { background: rgba(63, 185, 80, 0.15); color: var(--green); }

.sidebar section {
  margin-bottom: 20px;
}

.sidebar section h3 {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.sidebar ul {
  list-style: none;
  padding: 0;
}

.sidebar ul li {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  padding-left: 12px;
  position: relative;
}

.sidebar ul li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--text-dim);
}

.sidebar .why-text {
  font-size: 13px;
  color: var(--text);
  font-style: italic;
  line-height: 1.5;
}

.sidebar .chapter-ref {
  font-size: 12px;
  color: var(--blue);
}

.sidebar .mastery-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mastery-item {
  font-size: 12px;
}

.mastery-item .label {
  color: var(--text-muted);
}

.mastery-item .value {
  color: var(--text);
  font-weight: 500;
}

.prereq-list {
  list-style: none;
  padding: 0;
}

.prereq-list li {
  font-size: 12px;
  padding: 3px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.prereq-list li::before { content: none !important; }

.prereq-icon {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  flex-shrink: 0;
}

.prereq-icon.met { background: rgba(63, 185, 80, 0.2); color: var(--green); }
.prereq-icon.unmet { background: rgba(248, 81, 73, 0.2); color: var(--red); }

/* Graph styling */
.node-circle {
  cursor: pointer;
  stroke-width: 1.5;
  will-change: transform;
}

.node-circle:hover {
  filter: brightness(1.3) drop-shadow(0 0 8px currentColor);
}

.node-label {
  font-size: 10px;
  fill: var(--text-muted);
  pointer-events: none;
  text-anchor: middle;
  opacity: 0.85;
  font-weight: 500;
}

.node-group:hover .node-label {
  opacity: 1;
  fill: var(--text);
}

.link {
  stroke-opacity: 0.55;
}

.link-arrow {
  fill-opacity: 0.7;
}

/* Highlight mode */
.graph-highlight .node-circle { opacity: 0.15; filter: none; }
.graph-highlight .node-label { opacity: 0; }
.graph-highlight .link { stroke-opacity: 0.05; }
.graph-highlight .link-arrow { fill-opacity: 0.05; }

.graph-highlight .node-highlighted .node-circle { opacity: 1; filter: drop-shadow(0 0 6px currentColor); }
.graph-highlight .node-highlighted .node-label { opacity: 1; }
.graph-highlight .link-highlighted { stroke-opacity: 0.7; stroke: var(--blue) !important; }
.graph-highlight .link-highlighted .link-arrow { fill-opacity: 0.7; }

/* Overdue indicator — static glow (no animation for perf) */
.node-overdue .node-circle {
  filter: drop-shadow(0 0 6px var(--red)) drop-shadow(0 0 12px rgba(248, 81, 73, 0.25));
}

/* Cluster hulls */
.layer-hull {
  fill-opacity: 0.06;
  stroke-opacity: 0.18;
  stroke-width: 1;
  stroke-dasharray: 4 2;
}

/* Generated timestamp */
.generated-stamp {
  position: absolute;
  bottom: 12px;
  left: 16px;
  font-size: 10px;
  color: var(--text-dim);
}

/* Scrollbar */
.sidebar::-webkit-scrollbar { width: 6px; }
.sidebar::-webkit-scrollbar-track { background: transparent; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
  <h1>Vol Learning Graph</h1>
  <div class="header-stats">
    <div class="stat-badge">
      <span>Mastered</span>
      <span class="count" id="mastered-count">0/0</span>
    </div>
    <div class="stat-badge">
      <span>Due today</span>
      <span class="count" id="due-count">0</span>
    </div>
  </div>
  <div class="layer-bars" id="layer-bars"></div>
</div>

<div class="main">
  <div class="graph-container" id="graph-container">
    <div class="tooltip" id="tooltip"></div>
    <div class="generated-stamp" id="gen-stamp"></div>
  </div>
  <div class="sidebar" id="sidebar">
    <button class="sidebar-close" id="sidebar-close">&times;</button>
    <div id="sidebar-content"></div>
  </div>
</div>

<script>
// ===== DATA (injected at generation time) =====
const DATA = __DATA_JSON__;

// ===== CONSTANTS =====
const TIER_COLORS = {
  untested: '#f85149',
  recognized: '#e07d3c',
  understood: '#f0db4f',
  mastered: '#3fb950'
};

const LAYER_COLORS = {
  0: '#58a6ff',
  1: '#bc8cff',
  99: '#f778ba'
};

// ===== STATE =====
let selectedNode = null;
let activeLayer = null;

// ===== INIT =====
function init() {
  renderHeader();
  renderGraph();
  document.getElementById('gen-stamp').textContent = `Generated: ${DATA.generated}`;
  document.getElementById('sidebar-close').addEventListener('click', closeSidebar);
  document.getElementById('graph-container').addEventListener('click', (e) => {
    if (e.target === e.currentTarget || e.target.tagName === 'svg') {
      closeSidebar();
      clearHighlight();
    }
  });
}

// ===== HEADER =====
function renderHeader() {
  const totalNodes = DATA.nodes.length;
  const masteredCount = DATA.nodes.filter(n => n.tier === 'mastered').length;
  document.getElementById('mastered-count').textContent = `${masteredCount}/${totalNodes}`;

  const dueCount = DATA.due_today.length;
  const dueEl = document.getElementById('due-count');
  dueEl.textContent = dueCount;
  if (dueCount > 0) dueEl.classList.add('urgent');

  const barsEl = document.getElementById('layer-bars');
  DATA.layers.forEach(layer => {
    const pct = layer.total > 0 ? ((layer.mastered + layer.understood) / layer.total * 100) : 0;
    const color = layer.mastered > 0 ? TIER_COLORS.mastered :
                  layer.understood > 0 ? TIER_COLORS.understood :
                  layer.recognized > 0 ? TIER_COLORS.recognized : TIER_COLORS.untested;
    const div = document.createElement('div');
    div.className = 'layer-bar';
    div.dataset.layer = layer.id;
    div.innerHTML = `
      <span>L${layer.id === 99 ? 'E' : layer.id}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
      <span>${layer.understood + layer.mastered}/${layer.total}</span>
    `;
    div.addEventListener('click', () => toggleLayerFilter(layer.id));
    barsEl.appendChild(div);
  });
}

// ===== GRAPH =====
function renderGraph() {
  const container = document.getElementById('graph-container');
  let width = container.clientWidth;
  let height = container.clientHeight;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  // Zoom
  const g = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.2, 5])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);

  // Center initially
  svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.7));

  // Resize handler (debounced)
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      width = container.clientWidth;
      height = container.clientHeight;
      svg.attr('width', width).attr('height', height);
      const currentTransform = d3.zoomTransform(svg.node());
      svg.call(zoom.transform, d3.zoomIdentity
        .translate(width / 2, height / 2)
        .scale(currentTransform.k));
    }, 150);
  });

  // Arrow marker (adjusted refX for line endpoints)
  svg.append('defs').append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('markerWidth', 4)
    .attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-4L10,0L0,4')
    .attr('fill', '#6e7681')
    .attr('class', 'link-arrow');

  // Build node map for lookup
  const nodeMap = new Map(DATA.nodes.map(n => [n.id, n]));

  // Compute topological depth for Y positioning
  const depths = computeDepths(DATA.nodes, nodeMap);
  const maxDepth = Math.max(...Object.values(depths), 1);

  // Prepare link data
  const links = DATA.edges.filter(e => nodeMap.has(e.source) && nodeMap.has(e.target));

  // Simulation — structured top-down layout
  const simulation = d3.forceSimulation(DATA.nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(90).strength(0.15))
    .force('charge', d3.forceManyBody().strength(-350).distanceMax(350))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 12).strength(0.7))
    .force('x', d3.forceX(d => layerXPosition(d.layer, width)).strength(0.12))
    .force('y', d3.forceY(d => depthYPosition(depths[d.id] || 0, maxDepth, height)).strength(0.35))
    .velocityDecay(0.55)
    .alphaDecay(0.06)
    .alphaMin(0.02)
    .stop();  // Don't auto-start — we batch ticks off-screen

  // Batch simulation off-screen (no DOM updates until settled)
  for (let i = 0; i < 300; i++) simulation.tick();

  // Layer hull groups
  const hullGroup = g.append('g').attr('class', 'hulls');

  // Links — straight lines (much faster than curved paths per frame)
  const linkGroup = g.append('g').attr('class', 'links');
  const link = linkGroup.selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'link')
    .attr('stroke', '#6e7681')
    .attr('stroke-width', 1.4)
    .attr('marker-end', 'url(#arrow)');

  // Nodes
  const nodeGroup = g.append('g').attr('class', 'nodes');
  const node = nodeGroup.selectAll('g')
    .data(DATA.nodes)
    .join('g')
    .attr('class', d => {
      let cls = 'node-group';
      if (d.overdue) cls += ' node-overdue';
      return cls;
    });

  node.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => TIER_COLORS[d.tier] || TIER_COLORS.untested)
    .attr('stroke', d => d.overdue ? TIER_COLORS.untested : darken(TIER_COLORS[d.tier] || TIER_COLORS.untested))
    .attr('stroke-width', d => d.overdue ? 2.5 : 1.5);

  node.append('text')
    .attr('class', 'node-label')
    .attr('dy', d => nodeRadius(d) + 14)
    .text(d => formatLabel(d.id));

  // Render settled positions in one paint
  function renderPositions() {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  }

  renderPositions();
  updateHulls(hullGroup, DATA.nodes);

  // Interactions — tooltip with RAF-debounced mousemove
  const tooltip = document.getElementById('tooltip');
  let tooltipRaf = false;

  node.on('mouseenter', (event, d) => {
    tooltip.innerHTML = `<div class="node-name">${d.name}</div><div class="node-tier">${d.tier}${d.overdue ? ' • OVERDUE' : ''}</div>`;
    tooltip.classList.add('visible');
  })
  .on('mousemove', (event) => {
    if (tooltipRaf) return;
    tooltipRaf = true;
    requestAnimationFrame(() => {
      tooltipRaf = false;
      const rect = container.getBoundingClientRect();
      tooltip.style.left = (event.clientX - rect.left + 12) + 'px';
      tooltip.style.top = (event.clientY - rect.top - 8) + 'px';
    });
  })
  .on('mouseleave', () => {
    tooltip.classList.remove('visible');
  })
  .on('click', (event, d) => {
    event.stopPropagation();
    selectNode(d);
    highlightPrereqs(d, nodeMap, links);
  });

  // Drag — restart simulation only during drag, freeze after
  node.call(d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.1).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on('drag', (event, d) => {
      d.fx = event.x; d.fy = event.y;
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null;
    })
  );

  // Tick handler — only active during drag interactions
  let rafScheduled = false;
  simulation.on('tick', () => {
    if (!rafScheduled) {
      rafScheduled = true;
      requestAnimationFrame(() => {
        rafScheduled = false;
        renderPositions();
      });
    }
  });

  simulation.on('end', () => {
    renderPositions();
    updateHulls(hullGroup, DATA.nodes);
  });

  // Store references for highlight and resize
  window._graph = { node, link, nodeMap, svg: g, simulation, zoom, svgEl: svg };
}

function nodeRadius(d) {
  const base = 10;
  const extra = Math.min(d.downstream_count * 1.2, 12);
  return base + extra;
}

function layerXPosition(layer, w) {
  // Spread layers horizontally across available space
  const spread = Math.min(w || 1200, 1400) * 0.35;
  const positions = { 0: -spread, 1: 0, 99: spread };
  return positions[layer] || 0;
}

function depthYPosition(depth, maxDepth, h) {
  // Roots at top, deepest nodes at bottom
  const usable = Math.min(h || 800, 1000) * 0.7;
  return -usable / 2 + (depth / Math.max(maxDepth, 1)) * usable;
}

function computeDepths(nodes, nodeMap) {
  // BFS from roots to assign depth (longest path from any root)
  const depths = {};
  const children = {};
  nodes.forEach(n => { depths[n.id] = 0; children[n.id] = []; });
  nodes.forEach(n => {
    n.requires.forEach(req => {
      if (children[req]) children[req].push(n.id);
    });
  });
  // Topological sort via Kahn's
  const inDegree = {};
  nodes.forEach(n => { inDegree[n.id] = n.requires.filter(r => nodeMap.has(r)).length; });
  const queue = nodes.filter(n => inDegree[n.id] === 0).map(n => n.id);
  while (queue.length) {
    const id = queue.shift();
    children[id].forEach(childId => {
      depths[childId] = Math.max(depths[childId], depths[id] + 1);
      inDegree[childId]--;
      if (inDegree[childId] === 0) queue.push(childId);
    });
  }
  return depths;
}

function formatLabel(id) {
  // Convert snake_case to readable: "har_model" -> "HAR Model"
  return id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function darken(hex) {
  // Return a slightly darker/more transparent version for stroke
  return hex + '99';
}

function updateHulls(hullGroup, nodes) {
  const layerGroups = {};
  nodes.forEach(n => {
    if (n.x === undefined) return;
    if (!layerGroups[n.layer]) layerGroups[n.layer] = [];
    layerGroups[n.layer].push([n.x, n.y]);
  });

  hullGroup.selectAll('path').remove();
  Object.entries(layerGroups).forEach(([layer, points]) => {
    if (points.length < 3) return;
    const hull = d3.polygonHull(points);
    if (!hull) return;
    const color = LAYER_COLORS[layer] || '#8b949e';
    hullGroup.append('path')
      .attr('class', 'layer-hull')
      .attr('d', hullPath(hull, 30))
      .attr('fill', color)
      .attr('stroke', color);
  });
}

function hullPath(hull, padding) {
  // Expand hull outward by padding
  const centroid = d3.polygonCentroid(hull);
  const expanded = hull.map(p => {
    const dx = p[0] - centroid[0];
    const dy = p[1] - centroid[1];
    const dist = Math.sqrt(dx * dx + dy * dy);
    const scale = (dist + padding) / dist;
    return [centroid[0] + dx * scale, centroid[1] + dy * scale];
  });
  return `M${expanded.map(p => p.join(',')).join('L')}Z`;
}

// ===== HIGHLIGHT =====
function highlightPrereqs(d, nodeMap, links) {
  const ancestors = new Set();
  const queue = [...d.requires];
  while (queue.length) {
    const id = queue.pop();
    if (ancestors.has(id)) continue;
    ancestors.add(id);
    const n = nodeMap.get(id);
    if (n) queue.push(...n.requires);
  }
  ancestors.add(d.id);

  const { node, link, svg } = window._graph;
  svg.classed('graph-highlight', true);
  node.classed('node-highlighted', n => ancestors.has(n.id));
  link.classed('link-highlighted', l => ancestors.has(l.source.id) && ancestors.has(l.target.id));
}

function clearHighlight() {
  const { node, link, svg } = window._graph;
  if (!svg) return;
  svg.classed('graph-highlight', false);
  node.classed('node-highlighted', false);
  link.classed('link-highlighted', false);
}

// ===== SIDEBAR =====
function selectNode(d) {
  selectedNode = d;
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('sidebar-content');
  const nodeMap = window._graph.nodeMap;
  const detail = DATA.detail[d.id] || {};

  const prereqsHtml = d.requires.length > 0
    ? d.requires.map(rid => {
        const rn = nodeMap.get(rid);
        const met = rn && (rn.tier === 'understood' || rn.tier === 'mastered');
        return `<li><span class="prereq-icon ${met ? 'met' : 'unmet'}">${met ? '✓' : '✗'}</span>${rn ? rn.name : rid}</li>`;
      }).join('')
    : '<li style="color:var(--text-muted)">None (root node)</li>';

  const keyPoints = detail.key_points || [];
  const whyItMatters = detail.why_it_matters || '';
  const chapter = detail.chapter || '';
  const consecutivePasses = detail.consecutive_passes || 0;
  const lastTested = detail.last_tested || 'never';
  const nextReview = detail.next_review || '—';

  content.innerHTML = `
    <h2>${d.name}</h2>
    <span class="tier-badge tier-${d.tier}">${d.tier}</span>

    <section>
      <h3>Key Points</h3>
      <ul>${keyPoints.map(kp => `<li>${kp}</li>`).join('')}</ul>
    </section>

    ${whyItMatters ? `<section><h3>Why It Matters</h3><p class="why-text">${whyItMatters}</p></section>` : ''}

    ${chapter ? `<section><h3>Chapter</h3><span class="chapter-ref">Ch. ${chapter}</span></section>` : ''}

    <section>
      <h3>Mastery</h3>
      <div class="mastery-info">
        <div class="mastery-item"><div class="label">Tier</div><div class="value">${d.tier}</div></div>
        <div class="mastery-item"><div class="label">Passes</div><div class="value">${consecutivePasses}</div></div>
        <div class="mastery-item"><div class="label">Last tested</div><div class="value">${lastTested}</div></div>
        <div class="mastery-item"><div class="label">Next review</div><div class="value">${nextReview}</div></div>
      </div>
    </section>

    <section>
      <h3>Prerequisites</h3>
      <ul class="prereq-list">${prereqsHtml}</ul>
    </section>
  `;

  sidebar.classList.add('open');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  selectedNode = null;
  clearHighlight();
}

// ===== LAYER FILTER =====
function toggleLayerFilter(layerId) {
  const bars = document.querySelectorAll('.layer-bar');
  if (activeLayer === layerId) {
    activeLayer = null;
    bars.forEach(b => b.classList.remove('active'));
    window._graph.node.style('display', null);
    window._graph.link.style('display', null);
  } else {
    activeLayer = layerId;
    bars.forEach(b => b.classList.toggle('active', parseInt(b.dataset.layer) === layerId));
    window._graph.node.style('display', d => d.layer === layerId ? null : 'none');
    window._graph.link.style('display', l => {
      const sameLayer = l.source.layer === layerId && l.target.layer === layerId;
      const crossesIn = l.target.layer === layerId;
      return (sameLayer || crossesIn) ? null : 'none';
    });
  }
}

// ===== GO =====
init();
</script>
</body>
</html>
"""


def generate():
    nodes = load_graph()
    state = load_state()
    data = build_data(nodes, state)

    data_json = json.dumps(data, indent=None, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {OUTPUT_PATH}")
    return str(OUTPUT_PATH)


# ============================================================
# TEXT DASHBOARD (--text mode)
# ============================================================

LAYER_NAMES = {
    -1: "Math Foundations",
    0: "HAR Core",
    1: "Noise + Asymmetry",
    2: "Options",
    3: "Microstructure",
    4: "Cross-Asset",
    99: "Evaluation",
}

TIER_ORDER = ["untested", "recognized", "understood", "mastered"]


def _progress_bar(done: int, total: int, width: int = 20) -> str:
    """Render a block-character progress bar."""
    if total == 0:
        return "░" * width
    filled = round(done / total * width)
    return "█" * filled + "░" * (width - filled)


def _parse_review_date(dt_str: str | None) -> date | None:
    """Parse next_review (ISO datetime or date) to a date object."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def generate_text_status() -> str:
    """Compute and return the full text dashboard as markdown."""
    nodes = load_graph()
    state = load_state()
    downstream = compute_downstream_counts(nodes)
    today = date.today()

    # Enrich nodes with state
    enriched = []
    for n in nodes:
        nid = n["id"]
        s = state.get(nid, {})
        tier = s.get("tier", "untested")
        next_review = _parse_review_date(s.get("next_review"))
        last_tested_str = s.get("last_tested")
        last_tested = None
        if last_tested_str:
            try:
                last_tested = date.fromisoformat(last_tested_str)
            except ValueError:
                pass
        enriched.append({
            "id": nid,
            "name": n.get("name", nid),
            "layer": n.get("layer", 0),
            "requires": n.get("requires", []),
            "tier": tier,
            "next_review": next_review,
            "last_tested": last_tested,
            "consecutive_passes": s.get("consecutive_passes", 0),
            "downstream_count": downstream.get(nid, 0),
        })

    lines: list[str] = []
    lines.append("## Learning Dashboard\n")

    # --- 1. PER-LAYER PROGRESS BARS ---
    lines.append("### Per-Layer Progress\n")
    layers: dict[int, dict] = {}
    for n in enriched:
        layer = n["layer"]
        if layer not in layers:
            layers[layer] = {"total": 0, "untested": 0, "recognized": 0, "understood": 0, "mastered": 0}
        layers[layer]["total"] += 1
        layers[layer][n["tier"]] += 1

    for layer_id in sorted(layers.keys()):
        info = layers[layer_id]
        name = LAYER_NAMES.get(layer_id, f"Layer {layer_id}")
        done = info["understood"] + info["mastered"]
        total = info["total"]
        pct = round(done / total * 100) if total else 0
        bar = _progress_bar(done, total)
        label = f"L{layer_id}" if layer_id != 99 else "LEval"
        lines.append(f"{label} ({name}):".ljust(28) + f" {bar}  {done}/{total} ({pct}%)")

    lines.append("")

    # --- 2. DUE TODAY ---
    lines.append("### Due Today\n")
    due_today = [n for n in enriched if n["next_review"] and n["next_review"] <= today]
    due_today.sort(key=lambda n: TIER_ORDER.index(n["tier"]) if n["tier"] in TIER_ORDER else 0)
    if due_today:
        for n in due_today:
            tested = n["last_tested"].isoformat() if n["last_tested"] else "never"
            lines.append(f"- **{n['name']}** ({n['tier']}, last tested {tested})")
    else:
        lines.append("- None")
    lines.append("")

    # --- 3. DUE THIS WEEK ---
    lines.append("### Due This Week\n")
    week_end = today + timedelta(days=7)
    due_week = [
        n for n in enriched
        if n["next_review"] and today < n["next_review"] <= week_end
    ]
    due_week.sort(key=lambda n: n["next_review"])
    if due_week:
        for n in due_week:
            days_until = (n["next_review"] - today).days
            lines.append(f"- **{n['name']}** ({n['tier']}, review in {days_until}d)")
    else:
        lines.append("- None")
    lines.append("")

    # --- 4. FRONTIER NODES ---
    lines.append("### Frontier Nodes (ready to learn)\n")
    tier_rank = {"untested": 0, "recognized": 1, "understood": 2, "mastered": 3}
    node_tier_map = {n["id"]: n["tier"] for n in enriched}

    frontiers = []
    for n in enriched:
        # Frontier = not yet understood/mastered, but all prereqs are >= understood
        if n["tier"] in ("understood", "mastered"):
            continue
        prereqs = n["requires"]
        if not prereqs:
            all_met = True
        else:
            all_met = all(
                tier_rank.get(node_tier_map.get(req, "untested"), 0) >= 2
                for req in prereqs
            )
        if all_met:
            frontiers.append(n)

    frontiers.sort(key=lambda n: -n["downstream_count"])
    if frontiers:
        for i, n in enumerate(frontiers[:10], 1):
            lines.append(
                f"{i}. **{n['id']}** - \"{n['name']}\" "
                f"({n['tier']}, unlocks {n['downstream_count']} nodes, "
                f"L{n['layer']})"
            )
    else:
        lines.append("- None (all prerequisites unmet or everything mastered)")
    lines.append("")

    # --- 5. STALE ALERTS ---
    lines.append("### Stale Alerts\n")
    stale_threshold = timedelta(days=14)
    stale = []
    for n in enriched:
        if n["tier"] != "understood":
            continue
        if n["next_review"] and (today - n["next_review"]) >= stale_threshold:
            stale.append(n)
        elif n["last_tested"] and (today - n["last_tested"]) >= stale_threshold:
            stale.append(n)
    if stale:
        for n in stale:
            days_ago = (today - n["last_tested"]).days if n["last_tested"] else "?"
            lines.append(f"- **{n['name']}** - understood but not reviewed in {days_ago} days")
    else:
        lines.append("- None")
    lines.append("")

    # --- 6. RECOMMENDATION ---
    lines.append("### Recommendation\n")
    n_due = len(due_today)
    n_frontier = len(frontiers)
    top_frontier = frontiers[0]["id"] if frontiers else None

    if n_due > 0 and n_frontier > 0:
        lines.append(
            f"You have {n_due} review(s) due and {n_frontier} frontier nodes ready. "
            f"Start with `/quiz` for reviews, then `/teach {top_frontier}`."
        )
    elif n_due > 0:
        lines.append(f"You have {n_due} review(s) due. Run `/quiz` to lock them in.")
    elif n_frontier > 0:
        lines.append(
            f"No reviews due. Pick up `/teach {top_frontier}` "
            f"(unlocks {frontiers[0]['downstream_count']} downstream nodes)."
        )
    else:
        lines.append("All caught up! Consider expanding the graph with `/expand-learning-graph`.")
    lines.append("")

    # --- SUMMARY LINE ---
    total_nodes = len(enriched)
    mastered = sum(1 for n in enriched if n["tier"] == "mastered")
    understood = sum(1 for n in enriched if n["tier"] == "understood")
    lines.append(f"**Total:** {total_nodes} nodes | {mastered} mastered | {understood} understood | {n_due} due today | {n_frontier} frontiers ready")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate learning dashboard")
    parser.add_argument("--text", action="store_true", help="Output text/markdown dashboard to stdout")
    args = parser.parse_args()

    if args.text:
        print(generate_text_status())
    else:
        generate()
