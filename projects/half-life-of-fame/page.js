// Interactive charts for the half-life of fame page. All numbers come from data/results.js.
const F = window.FAME;
fillNumbers(F);
const $ = (id) => document.getElementById(id);
const whole = (n) => Math.round(n).toLocaleString("en-GB");
const pct = (v) => Math.round(v * 100) + "%";
const days = (v) => (v == null ? "not within 90 days" : v < 10 ? v.toFixed(1) + " days" : Math.round(v) + " days");
const COLORS = { "Person who died in 2025": "#ff8494", "Living person": "#f2b134", "Film": "#5fb0ff", "TV series": "#3fd0bf", "Sports event": "#a58bff", "Other": "#8f9abc" };
const DARK = { "Person who died in 2025": "#d7263d", "Living person": "#b97a00", "Film": "#2f7fd6", "TV series": "#12857a", "Sports event": "#6d4bd1", "Other": "#4d5875" };
const state = { i: Math.max(0, F.events.findIndex((e) => e.type === "Film")), log: true };   // start on the biggest film

// ------------------------------------------------------------ headline tiles
$("t-half").textContent = F.overall.half_life[0].toFixed(1);
$("t-under").textContent = pct(F.overall.half_life_under_one_day);
$("t-back").textContent = Math.round(F.overall.back_to_normal[0]);
$("t-still").textContent = pct(F.overall.still_elevated_after_90_days);
$("t-power").textContent = pct(F.overall.power_law_better);
$("t-sport").textContent = Math.round(F.types["Sports event"].back_to_normal[0]);
$("t-tv").textContent = Math.round(F.types["TV series"].back_to_normal[0]);

// ------------------------------------------------------------ one spike
const pick = $("pick");
function fillList(filter) {
  const f = filter.trim().toLowerCase();
  pick.innerHTML = "";
  F.events.forEach((e, i) => { if (!f || e.title.toLowerCase().includes(f)) pick.add(new Option(e.title, i)); });
  if (pick.options.length && ![...pick.options].some((o) => +o.value === state.i)) { state.i = +pick.options[0].value; }
  pick.value = state.i;
}
function drawSpike() {
  const e = F.events[state.i], W = 760, H = 420, m = { t: 16, r: 18, b: 40, l: 62 };
  const svg = d3.select("#spike").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const pts = e.views.map((v, k) => [k - 14, v]).filter((d) => d[1] != null && (!state.log || d[1] > 0));
  const x = d3.scaleLinear().domain([-14, 60]).range([m.l, W - m.r]);
  const top = e.peak * (state.log ? 1.6 : 1.05), bottom = state.log ? Math.max(1, Math.min(e.base, d3.min(pts, (d) => d[1])) * 0.6) : 0;
  const y = (state.log ? d3.scaleLog() : d3.scaleLinear()).domain([bottom, top]).range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([-14, 0, 7, 14, 30, 45, 60]).tickFormat((d) => (d === 0 ? "peak" : (d > 0 ? "+" : "") + d)).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5, "~s").tickSizeOuter(0));
  svg.append("text").attr("x", (m.l + W - m.r) / 2).attr("y", H - 4).attr("text-anchor", "middle").text("days from the peak");
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(Math.max(e.base, bottom))).attr("y2", y(Math.max(e.base, bottom))).attr("stroke", "#8f9abc").attr("stroke-dasharray", "5 4");
  if (e.half_life != null) {
    const hy = y(e.base + (e.peak - e.base) / 2);
    svg.append("line").attr("x1", x(0)).attr("x2", x(e.half_life)).attr("y1", hy).attr("y2", hy).attr("stroke", "#f2b134").attr("stroke-width", 2);
    svg.append("text").attr("x", x(e.half_life) + 8).attr("y", hy + 4).attr("fill", "#f2b134").style("fill", "#f2b134").text("half of the extra views");
  }
  const c = COLORS[e.type];
  svg.append("path").attr("d", d3.line().x((d) => x(d[0])).y((d) => y(d[1]))(pts)).attr("fill", "none").attr("stroke", c).attr("stroke-width", 2.5);
  svg.append("circle").attr("cx", x(0)).attr("cy", y(e.peak)).attr("r", 6).attr("fill", c).attr("stroke", "#fff").attr("stroke-width", 1.5);
  $("e-desc").textContent = (e.description ? e.description[0].toUpperCase() + e.description.slice(1) + ". " : "") + `Filed under: ${e.type.toLowerCase()}.`;
  $("e-date").textContent = new Date(e.peak_date + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  $("e-peak").textContent = whole(e.peak); $("e-ratio").textContent = e.base < 100 ? "new article" : "×" + whole(e.ratio);
  $("e-half").textContent = days(e.half_life); $("e-back").textContent = days(e.back_to_normal);
  $("lin").setAttribute("aria-pressed", !state.log); $("log").setAttribute("aria-pressed", state.log);
}
$("q").addEventListener("input", () => { fillList($("q").value); drawSpike(); });
pick.addEventListener("change", () => { state.i = +pick.value; drawSpike(); });
$("lin").addEventListener("click", () => { state.log = false; drawSpike(); });
$("log").addEventListener("click", () => { state.log = true; drawSpike(); });
fillList(""); drawSpike();

// ------------------------------------------------------------ half-life by type
(function () {
  const rows = Object.entries(F.types).map(([name, d]) => ({ name, n: d.events, v: d.half_life })).sort((a, b) => a.v[0] - b.v[0]);
  const W = 480, rowH = 44, H = rows.length * rowH + 44, left = 190;
  const svg = d3.select("#types").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.v[2]) * 1.1]).range([left, W - 56]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - 36})`).call(d3.axisBottom(x).ticks(5).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (left + W - 56) / 2).attr("y", H - 4).attr("text-anchor", "middle").text("half-life in days");
  const g = svg.selectAll("g.row").data(rows).join("g").attr("class", "row").attr("transform", (_, i) => `translate(0,${i * rowH + rowH / 2})`);
  g.append("text").attr("x", left - 12).attr("dy", "-0.1em").attr("text-anchor", "end").text((r) => r.name);
  g.append("text").attr("class", "note").attr("x", left - 12).attr("dy", "1.1em").attr("text-anchor", "end").text((r) => `${r.n} articles`);
  g.append("line").attr("x1", (r) => x(r.v[1])).attr("x2", (r) => x(r.v[2])).attr("stroke", (r) => DARK[r.name]).attr("stroke-width", 3);
  g.append("circle").attr("cx", (r) => x(r.v[0])).attr("r", 7).attr("fill", (r) => DARK[r.name]).attr("stroke", "#fff").attr("stroke-width", 2);
  g.append("text").attr("x", (r) => x(r.v[2]) + 8).attr("dy", "0.35em").style("font-weight", 700).text((r) => r.v[0].toFixed(1));
  const k = F.overall.kruskal_half_life;
  $("kw-line").textContent = `The groups ${k.p < 0.05 ? "differ more than chance would explain" : "do not differ more than chance would explain"} (Kruskal-Wallis test, p ${k.p < 0.001 ? "below 0.001" : "= " + k.p.toFixed(3)}).`;
})();

// ------------------------------------------------------------ typical fade by type
(function () {
  const W = 480, H = 300, m = { t: 12, r: 14, b: 40, l: 52 };
  const svg = d3.select("#curves").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0, 60]).range([m.l, W - m.r]), y = d3.scaleLog().domain([0.002, 1]).range([H - m.b, m.t]).clamp(true);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([0, 7, 14, 30, 45, 60]).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues([1, 0.1, 0.01]).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 4).attr("text-anchor", "middle").text("days after the peak");
  const names = Object.keys(F.types).filter((n) => n !== "Other");
  names.forEach((n) => svg.append("path").attr("d", d3.line().x((_, t) => x(t)).y((v) => y(Math.max(v, 0.002)))(F.types[n].curve)).attr("fill", "none").attr("stroke", DARK[n]).attr("stroke-width", 2.2));
  $("curve-key").innerHTML = names.map((n) => `<span><i style="border-color:${DARK[n]}"></i>${n}</span>`).join("");
})();
