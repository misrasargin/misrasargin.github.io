// Interactive charts for the grocery markdown page. All numbers come from data/results.js.
const G = window.GROCERY;
fillNumbers(G);
const INK = "#16213e", SOFT = "#8f9abc", RED = "#d7263d", TEAL = "#12857a";
const $ = (id) => document.getElementById(id);
const pct = (v, d = 0) => (v * 100).toFixed(d) + "%";
const signedPct = (v, d = 1) => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(d) + "%";
const E = G.elasticity.value, liftAt = (p) => Math.pow(p, -E);
const state = { hour: 19, stock: 3, level: 1.3, btHour: 19 };
const band = (name) => G.lift.find((b) => b.band === name);
const bt = (level, hour) => G.backtest.find((b) => b.stock === level && b.hour === hour);

// ------------------------------------------------------------ headline tiles
(function () {
  const m = bt(1.3, 19);
  $("t-lift").textContent = band("10-20% off").lift.toFixed(2); $("t-lift2").textContent = band("30-40% off").lift.toFixed(2);
  $("t-left").textContent = pct(G.profile.remaining[19]);
  $("t-waste").textContent = pct(m.rule.waste); $("t-waste0").textContent = pct(m.none.waste); $("t-waste1").textContent = pct(m.flat.waste);
  $("t-rev").textContent = signedPct(m.rule.revenue_change); $("t-rev1").textContent = signedPct(m.flat.revenue_change);
})();

// ------------------------------------------------------------ lift curve
(function () {
  const W = 480, H = 300, m = { t: 12, r: 16, b: 44, l: 44 };
  const svg = d3.select("#lift").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0, 0.5]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([1, 3.8]).range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat((v) => "×" + v).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle").text("discount");
  const curve = d3.range(0, 0.501, 0.01).map((d) => [d, liftAt(1 - d)]);
  svg.append("path").attr("d", d3.line().x((d) => x(d[0])).y((d) => y(d[1]))(curve)).attr("fill", "none").attr("stroke", INK).attr("stroke-width", 1.8).attr("stroke-dasharray", "5 4");
  const g = svg.append("g").selectAll("g").data(G.lift).join("g");
  g.append("line").attr("x1", (b) => x(1 - b.price)).attr("x2", (b) => x(1 - b.price)).attr("y1", (b) => y(b.lo)).attr("y2", (b) => y(b.hi)).attr("stroke", RED).attr("stroke-width", 3);
  g.append("circle").attr("cx", (b) => x(1 - b.price)).attr("cy", (b) => y(b.lift)).attr("r", 6).attr("fill", RED).attr("stroke", "#fff").attr("stroke-width", 1.5)
    .append("title").text((b) => `${b.band}: ×${b.lift.toFixed(2)} (${b.lo.toFixed(2)} to ${b.hi.toFixed(2)}), ${b.days.toLocaleString("en-GB")} product-days`);
  g.append("circle").attr("cx", (b) => x(1 - b.price) + 9).attr("cy", (b) => y(b.test_lift)).attr("r", 5).attr("fill", "#fff").attr("stroke", INK).attr("stroke-width", 2)
    .append("title").text((b) => `${b.band}, last 30 days: ×${b.test_lift.toFixed(2)}`);
})();

// ------------------------------------------------------------ shape of a day
function drawDay() {
  const W = 480, H = 300, m = { t: 12, r: 12, b: 44, l: 44 }, hrs = d3.range(6, 23);
  const svg = d3.select("#day").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleBand().domain(hrs).range([m.l, W - m.r]).padding(0.15), y = d3.scaleLinear().domain([0, d3.max(G.profile.full)]).nice().range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([6, 9, 12, 15, 18, 21]).tickFormat((h) => h + ":00").tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("g").selectAll("rect").data(hrs).join("rect").attr("x", (h) => x(h)).attr("width", x.bandwidth())
    .attr("y", (h) => y(G.profile.full[h])).attr("height", (h) => y(0) - y(G.profile.full[h])).attr("fill", (h) => (h >= state.hour ? INK : SOFT));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle")
    .text(`${pct(G.profile.remaining[state.hour])} of the day is still to come at ${state.hour}:00`);
}

// ------------------------------------------------------------ advisor
function outcome(stock, price, hour) {             // expected share of the stock sold, averaged over good and bad evenings
  const xi = G.noise[hour], k = liftAt(price);
  return d3.mean(xi, (v) => Math.min(stock, k * v)) / stock;
}
function advise() {
  const s = state.stock, h = state.hour;
  const rows = G.prices.map((p) => ({ p, sold: outcome(s, p, h) })).map((r) => ({ ...r, rev: r.p * r.sold }));
  const best = rows.reduce((a, b) => (b.rev > a.rev + 1e-12 ? b : a), rows[0]), full = rows[0];
  document.querySelectorAll("#hours button").forEach((b) => b.setAttribute("aria-pressed", +b.dataset.h === h));
  $("s-out").textContent = "×" + s.toFixed(2);
  $("s-help").textContent = `×${s.toFixed(2)} means the shelf holds ${s.toFixed(2)} times what this product normally sells between ${h}:00 and closing.`;
  $("advice").textContent = best.p === 1 ? "Keep full price" : `${Math.round((1 - best.p) * 100)}% off`;
  $("advice-line").textContent = best.p === 1
    ? "The stock is likely to sell without help. A discount would only give money away."
    : `At ${Math.round((1 - best.p) * 100)}% off, demand is about ×${liftAt(best.p).toFixed(1)}, and the extra sales outweigh the lower price.`;
  $("a-full").textContent = pct(full.sold); $("a-best").textContent = pct(best.sold); $("a-rev").textContent = signedPct(best.rev / full.rev - 1, 0);
  const W = 480, H = 220, m = { t: 14, r: 10, b: 44, l: 44 };
  const svg = d3.select("#options").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleBand().domain(rows.map((r) => r.p)).range([m.l, W - m.r]).padding(0.2), y = d3.scaleLinear().domain([0, Math.max(0.2, d3.max(rows, (r) => r.rev))]).nice().range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickFormat((p) => (p === 1 ? "full" : "−" + Math.round((1 - p) * 100) + "%")).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("g").selectAll("rect").data(rows).join("rect").attr("x", (r) => x(r.p)).attr("width", x.bandwidth()).attr("y", (r) => y(r.rev)).attr("height", (r) => y(0) - y(r.rev)).attr("fill", (r) => (r === best ? RED : SOFT));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle").text("price");
  drawDay();
}
Object.keys(G.noise).forEach((h) => { const b = document.createElement("button"); b.type = "button"; b.textContent = h + ":00"; b.dataset.h = h; b.addEventListener("click", () => { state.hour = +h; advise(); }); $("hours").append(b); });
$("s").addEventListener("input", () => { state.stock = +$("s").value; advise(); });
advise();

// ------------------------------------------------------------ replay
function bars(sel, rows, fmt, zero = false) {
  const W = 480, rowH = 46, H = rows.length * rowH + 8, left = 150;
  const svg = d3.select(sel).attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.v) || 1]).range([left, W - 76]);
  const g = svg.selectAll("g").data(rows).join("g").attr("transform", (_, i) => `translate(0,${i * rowH + 4})`);
  g.append("text").attr("x", left - 10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end").text((r) => r.label);
  g.append("rect").attr("x", left).attr("y", 9).attr("height", rowH - 18).attr("width", (r) => Math.max(zero ? 0 : 1, x(r.v) - left)).attr("fill", (r) => r.c);
  g.append("text").attr("x", (r) => x(r.v) + 8).attr("y", rowH / 2).attr("dy", "0.35em").style("font-weight", 700).text((r) => fmt(r.v));
}
function replay() {
  const b = bt(state.level, state.btHour);
  document.querySelectorAll("#stocks button").forEach((x) => x.setAttribute("aria-pressed", +x.dataset.v === state.level));
  document.querySelectorAll("#bt-hours button").forEach((x) => x.setAttribute("aria-pressed", +x.dataset.v === state.btHour));
  bars("#waste", [{ label: "Never discount", v: b.none.waste, c: "#4d5875" }, { label: "Flat 30% off", v: b.flat.waste, c: SOFT }, { label: "The rule", v: b.rule.waste, c: RED }], (v) => pct(v, 1));
  bars("#rev", [{ label: "Never discount", v: 0, c: "#4d5875" }, { label: "Flat 30% off", v: b.flat.revenue_change, c: SOFT }, { label: "The rule", v: b.rule.revenue_change, c: RED }], (v) => (v === 0 ? "0%" : signedPct(v)), true);
  $("bt-line").textContent = `${b.days.toLocaleString("en-GB")} held-out product-days. At ${b.hour}:00, ${pct(b.stock_left_share)} of the morning stock is still on the shelf, and the rule discounts on ${pct(b.rule.discounted_days)} of days.`;
}
[["stocks", "level", [[1, "A normal day’s sales"], [1.3, "30% more"], [1.6, "60% more"]]], ["bt-hours", "btHour", Object.keys(G.noise).map((h) => [+h, h + ":00"])]].forEach(([id, key, opts]) =>
  opts.forEach(([v, label]) => { const b = document.createElement("button"); b.type = "button"; b.textContent = label; b.dataset.v = v; b.addEventListener("click", () => { state[key] = v; replay(); }); $(id).append(b); }));
replay();
