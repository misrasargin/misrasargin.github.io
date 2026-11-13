// The "conspiracy board": countries are pins, a red string joins two countries
// when at least one of them gives the other more points than chance explains.
const BLOC_STYLE = [
  { anchor: "rs", name: "Balkans and their diasporas", color: "#f2b134" },
  { anchor: "ru", name: "Former Soviet states", color: "#a58bff" },
  { anchor: "se", name: "Nordic and Baltic", color: "#5fb0ff" },
  { anchor: "es", name: "South and west", color: "#3fd0bf" },
  { anchor: "gr", name: "Greece and Cyprus", color: "#ff8fb3" },
];

function boardModel(data) {
  const byId = new Map(data.countries.map((c) => [c.id, c]));
  const style = new Map();
  BLOC_STYLE.forEach((s) => { const c = byId.get(s.anchor); if (c) style.set(c.bloc, s); });
  const sig = data.pairs.filter((p) => p.sig);
  const strings = new Map();
  sig.forEach((p) => {
    const key = [p.from, p.to].sort().join("-");
    const s = strings.get(key) || { source: p.from, target: p.to, bias: 0, both: false };
    if (strings.has(key)) s.both = true;
    s.bias = Math.max(s.bias, p.bias);
    strings.set(key, s);
  });
  const ids = new Set(sig.flatMap((p) => [p.from, p.to]));
  const nodes = [...ids].map((id) => ({ id, ...byId.get(id) }));
  return { nodes, links: [...strings.values()], sig, byId, style };
}

function drawBoard(svgSel, data, opts = {}) {
  const { labels = true, onPick = null, width = 760, height = 600 } = opts;
  const m = boardModel(data);
  const svg = d3.select(svgSel).attr("viewBox", `0 0 ${width} ${height}`);
  svg.selectAll("*").remove();

  const sim = d3.forceSimulation(m.nodes)
    .force("link", d3.forceLink(m.links).id((d) => d.id).distance((l) => 95 - l.bias * 5).strength((l) => 0.15 + l.bias / 14))
    .force("charge", d3.forceManyBody().strength(-330))
    .force("x", d3.forceX(width / 2).strength(0.07))
    .force("y", d3.forceY(height / 2).strength(0.09))
    .force("collide", d3.forceCollide(26))
    .stop();
  for (let i = 0; i < 400; i++) sim.tick();
  const pad = labels ? 46 : 20;
  m.nodes.forEach((n) => { n.x = Math.max(pad, Math.min(width - pad, n.x)); n.y = Math.max(pad, Math.min(height - pad, n.y)); });

  const string = svg.append("g").selectAll("line").data(m.links).join("line")
    .attr("class", "string").attr("stroke-width", (l) => 0.6 + l.bias * (labels ? 0.55 : 0.8))
    .attr("x1", (l) => l.source.x).attr("y1", (l) => l.source.y).attr("x2", (l) => l.target.x).attr("y2", (l) => l.target.y);

  const pin = svg.append("g").selectAll("g").data(m.nodes).join("g").attr("class", "pin")
    .attr("transform", (n) => `translate(${n.x},${n.y})`);
  pin.append("circle").attr("r", labels ? 7 : 10).attr("fill", (n) => (m.style.get(n.bloc) || { color: "#fff" }).color);
  if (labels) {
    pin.append("text").attr("y", -11).attr("text-anchor", "middle").text((n) => n.name);
    pin.append("title").text((n) => n.name);
    pin.select("circle").attr("tabindex", 0).attr("role", "button").attr("aria-label", (n) => `Show ${n.name}`)
      .on("click", (_, n) => onPick && onPick(n.id))
      .on("keydown", (e, n) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onPick && onPick(n.id); } });
  }

  function highlight(id) {
    const near = new Set([id]);
    m.links.forEach((l) => { if (l.source.id === id) near.add(l.target.id); if (l.target.id === id) near.add(l.source.id); });
    string.classed("hot", (l) => l.source.id === id || l.target.id === id).classed("dim", (l) => id && l.source.id !== id && l.target.id !== id);
    pin.classed("dim", (n) => id && !near.has(n.id));
  }
  return { model: m, highlight };
}
