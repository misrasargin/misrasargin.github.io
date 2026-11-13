// Interactive charts for the bike rebalancing page. All numbers come from data/results.js.
const B = window.BIKES;
fillNumbers(B);
const whole = (n) => Math.round(n).toLocaleString("en-GB");
const money = (v) => "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const signed1 = (v) => (v > 0.04 ? "+" : "") + (Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1));
const hourLabel = (h) => `${String(h).padStart(2, "0")}:00 to ${String((h + 1) % 24).padStart(2, "0")}:00`;
const INK = "#16213e", SOFT = "#4d5875", RED = "#d7263d", TEAL = "#12857a";

// ---------------------------------------------------------------- map
const S = B.stations;
const state = { hour: 8, day: "weekday", pick: d3.maxIndex(S, (s) => s.fail_none) };
const MW = 760, MH = 620;
const map = d3.select("#map").attr("viewBox", `0 0 ${MW} ${MH}`);
const proj = d3.geoMercator().fitExtent([[40, 34], [MW - 40, MH - 34]], { type: "MultiPoint", coordinates: S.map((s) => [s.lon, s.lat]) });
const flow = d3.scaleLinear().domain([-5, 0, 5]).range(["#f2b134", "#8f9abc", "#5fb0ff"]).clamp(true);
[["Hoboken", 440, 64], ["Jersey City", 400, 462]].forEach(([name, x, y]) => {
  map.append("text").attr("class", "place").attr("x", x).attr("y", y).text(name);
});
const dots = map.append("g").selectAll("g").data(S.map((s, i) => ({ ...s, i })).sort((a, b) => b.docks - a.docks)).join("g")
  .attr("class", "dot").attr("transform", (s) => `translate(${proj([s.lon, s.lat])})`);
dots.append("circle").attr("r", (s) => 2.5 + Math.sqrt(s.docks) * 1.35).attr("tabindex", 0).attr("role", "button")
  .attr("aria-label", (s) => `Show ${s.name}`)
  .on("click", (_, s) => pickStation(s.i))
  .on("keydown", (e, s) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pickStation(s.i); } });
dots.append("title").text((s) => s.name);

const pick = document.getElementById("pick");
S.map((s, i) => [s.name, i]).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, i]) => pick.add(new Option(name, i)));
pick.addEventListener("change", () => pickStation(+pick.value));

function drawSpark() {
  const s = S[state.pick], W = 290, H = 140, m = { t: 10, r: 8, b: 30, l: 34 };
  const svg = d3.select("#spark").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleLinear().domain([0, 23]).range([m.l, W - m.r]);
  const ext = Math.max(1, d3.max([...s.weekday, ...s.weekday_forecast], Math.abs));
  const y = d3.scaleLinear().domain([-ext, ext]).range([H - m.b, m.t]);
  const line = d3.line().x((_, h) => x(h)).y((v) => y(v));
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0)).attr("stroke", "#5b6894");
  svg.append("line").attr("x1", x(state.hour)).attr("x2", x(state.hour)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", "#5b6894").attr("stroke-dasharray", "2 3");
  svg.append("path").attr("d", line(s.weekday_forecast)).attr("fill", "none").attr("stroke", "#ff8494").attr("stroke-width", 2).attr("stroke-dasharray", "5 4");
  svg.append("path").attr("d", line(s.weekday)).attr("fill", "none").attr("stroke", "#e8ecf7").attr("stroke-width", 2);
  [0, 6, 12, 18].forEach((h) => svg.append("text").attr("x", x(h)).attr("y", H - 6).attr("text-anchor", "middle").text(`${String(h).padStart(2, "0")}:00`));
  [-ext, 0, ext].forEach((v) => svg.append("text").attr("x", m.l - 5).attr("y", y(v) + 4).attr("text-anchor", "end").text(v === 0 ? "0" : signed1(v)));
}
function drawMap() {
  dots.select("circle").attr("fill", (s) => flow(s[state.day][state.hour]));
  dots.classed("picked", (s) => s.i === state.pick);
  document.getElementById("hour-out").textContent = hourLabel(state.hour);
  document.getElementById("s-net").textContent = signed1(S[state.pick][state.day][state.hour]);
  drawSpark();
}
function pickStation(i) {
  state.pick = i; pick.value = i;
  const s = S[i];
  document.getElementById("s-docks").textContent = s.docks;
  document.getElementById("s-rides").textContent = whole(s.rides_per_day);
  document.getElementById("s-none").textContent = whole(s.fail_none);
  document.getElementById("s-disc").textContent = whole(s.fail_discounts);
  document.getElementById("s-truck").textContent = whole(s.fail_truck);
  drawMap();
}
const hourInput = document.getElementById("hour");
hourInput.addEventListener("input", () => { state.hour = +hourInput.value; drawMap(); });
[["wd", "weekday"], ["we", "weekend"]].forEach(([id, day]) => document.getElementById(id).addEventListener("click", () => {
  state.day = day;
  document.getElementById("wd").setAttribute("aria-pressed", day === "weekday");
  document.getElementById("we").setAttribute("aria-pressed", day === "weekend");
  drawMap();
}));
let timer = null;
const playBtn = document.getElementById("play");
function stopPlay() { clearInterval(timer); timer = null; playBtn.textContent = "Play the day"; }
playBtn.addEventListener("click", () => {
  if (timer) return stopPlay();
  playBtn.textContent = "Stop";
  state.hour = 4; let steps = 0;
  timer = setInterval(() => {
    state.hour = (state.hour + 1) % 24; hourInput.value = state.hour; drawMap();
    if (++steps >= 24) stopPlay();
  }, 650);
});
pickStation(state.pick);

// ---------------------------------------------------------------- forecast error bars
function hbars(sel, rows, { W = 480, rowH = 44, left = 190, fmt = (v) => v.toFixed(2), max } = {}) {
  const H = rows.length * rowH + 8, svg = d3.select(sel).attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleLinear().domain([0, max || d3.max(rows, (r) => r.v)]).range([left, W - 70]);
  const g = svg.selectAll("g").data(rows).join("g").attr("transform", (_, i) => `translate(0,${i * rowH + 4})`);
  g.append("text").attr("x", left - 10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end").text((r) => r.label);
  g.append("rect").attr("x", left).attr("y", 8).attr("height", rowH - 16).attr("width", (r) => Math.max(1, x(r.v) - left)).attr("fill", (r) => r.c);
  g.append("text").attr("x", (r) => x(r.v) + 8).attr("y", rowH / 2).attr("dy", "0.35em").style("font-weight", 700).text((r) => fmt(r.v));
}
const T = B.forecast.test;
hbars("#mae", [
  { label: "Same hour last week", v: T.last_week.net_mae, c: SOFT },
  { label: "Average of last 4 weeks", v: T.baseline.net_mae, c: SOFT },
  { label: "Model", v: T.model.net_mae, c: RED },
  { label: "Model without weather", v: T.model_no_weather.net_mae, c: "#e58a96" },
]);

// ---------------------------------------------------------------- reliability
(function () {
  const W = 480, H = 300, m = { t: 12, r: 16, b: 44, l: 68 };
  const svg = d3.select("#rel").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0, 1]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, 1]).range([H - m.b, m.t]);
  const pct = d3.format(".0%");
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickFormat(pct).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(pct).tickSizeOuter(0));
  svg.append("line").attr("x1", x(0)).attr("y1", y(0)).attr("x2", x(1)).attr("y2", y(1)).attr("stroke", INK).attr("stroke-dasharray", "4 4");
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle").text("chance the forecast gave");
  svg.append("text").attr("class", "note").attr("transform", `translate(14,${(m.t + H - m.b) / 2}) rotate(-90)`).attr("text-anchor", "middle").text("how often it happened");
  [["loses", RED], ["gains", TEAL]].forEach(([k, c]) => {
    const bins = B.forecast.reliability[k].bins;
    svg.append("path").attr("d", d3.line().x((b) => x(b.predicted)).y((b) => y(b.observed))(bins)).attr("fill", "none").attr("stroke", c).attr("stroke-width", 2);
    svg.append("g").selectAll("circle").data(bins).join("circle").attr("cx", (b) => x(b.predicted)).attr("cy", (b) => y(b.observed)).attr("r", 4.5).attr("fill", c).attr("stroke", "#fff").attr("stroke-width", 1.5)
      .append("title").text((b) => `Forecast ${pct(b.predicted)}, happened ${pct(b.observed)} (${whole(b.n)} station-hours)`);
  });
})();

// ---------------------------------------------------------------- one week
const wk = document.getElementById("wk");
B.week.stations.forEach((s, i) => wk.add(new Option(s.name, i)));
function drawWeek() {
  const s = B.week.stations[+wk.value], W = 1000, H = 300, m = { t: 12, r: 12, b: 34, l: 44 };
  const svg = d3.select("#week").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const x = d3.scaleLinear().domain([0, 167]).range([m.l, W - m.r]);
  const ext = d3.max([...s.actual, ...s.model], Math.abs) || 1;
  const y = d3.scaleLinear().domain([-ext, ext]).nice().range([H - m.b, m.t]);
  const line = d3.line().x((_, h) => x(h)).y((v) => y(v));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSizeOuter(0));
  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach((d, i) => {
    svg.append("line").attr("x1", x(i * 24)).attr("x2", x(i * 24)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", "#cfd6e4");
    svg.append("text").attr("x", x(i * 24 + 12)).attr("y", H - 10).attr("text-anchor", "middle").text(d);
  });
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0)).attr("stroke", INK);
  svg.append("path").attr("d", line(s.actual)).attr("fill", "none").attr("stroke", INK).attr("stroke-width", 1.8);
  svg.append("path").attr("d", line(s.model)).attr("fill", "none").attr("stroke", RED).attr("stroke-width", 1.8);
}
wk.addEventListener("change", drawWeek); drawWeek();

// ---------------------------------------------------------------- discount or truck calculator
const calc = { acc: String(B.meta.main_accept_rate), d: 1, t: 3 };
const accBox = document.getElementById("acc");
Object.keys(B.sim.discounts).forEach((p) => {
  const b = document.createElement("button"); b.type = "button"; b.textContent = Math.round(p * 100) + "%"; b.dataset.p = p;
  b.addEventListener("click", () => { calc.acc = p; drawCalc(); }); accBox.append(b);
});
const dIn = document.getElementById("d"), tIn = document.getElementById("t");
dIn.addEventListener("input", () => { calc.d = +dIn.value; drawCalc(); });
tIn.addEventListener("input", () => { calc.t = +tIn.value; drawCalc(); });
function drawCalc() {
  const none = B.sim.none.failures, D = B.sim.discounts[calc.acc], K = B.sim.truck[String(B.meta.main_truck)], Both = B.sim.both[calc.acc];
  const avD = none - D.failures, avT = none - K.failures;
  const costD = D.discounts * calc.d, costT = K.bikes_moved * calc.t, perD = costD / avD, perT = costT / avT;
  accBox.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.p === calc.acc));
  document.getElementById("d-out").textContent = money(calc.d);
  document.getElementById("t-out").textContent = money(calc.t);
  const set = (id, v) => (document.getElementById(id).textContent = v);
  set("c-av-d", whole(avD)); set("c-av-t", whole(avT));
  set("c-n-d", whole(D.discounts)); set("c-n-t", whole(K.bikes_moved));
  set("c-cost-d", "$" + whole(costD)); set("c-cost-t", "$" + whole(costT));
  set("c-per-d", money(perD)); set("c-per-t", money(perT));
  set("be", money(calc.t * (K.bikes_moved / avT) / (D.discounts / avD)));
  set("verdict", perD < perT
    ? `At these prices the discount is cheaper per failed ride avoided, but it avoids fewer: ${whole(avD)} against ${whole(avT)}.`
    : `At these prices the truck is cheaper per failed ride avoided, and it avoids more: ${whole(avT)} against ${whole(avD)}.`);
  hbars("#bars", [
    { label: "Nobody moves bikes", v: none, c: SOFT },
    { label: "Discounts", v: D.failures, c: RED },
    { label: "One truck", v: K.failures, c: TEAL },
    { label: "Truck and discounts", v: Both.failures, c: "#6d4bd1" },
  ], { fmt: whole, left: 160, max: none });
}
drawCalc();

// ---------------------------------------------------------------- failures by hour
(function () {
  const W = 480, H = 230, m = { t: 10, r: 12, b: 30, l: 48 }, bh = B.sim.by_hour;
  const svg = d3.select("#byhour").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0, 23]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, d3.max(bh.none)]).nice().range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([0, 3, 6, 9, 12, 15, 18, 21]).tickFormat((h) => String(h).padStart(2, "0") + ":00").tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickSizeOuter(0));
  const line = d3.line().x((_, h) => x(h)).y((v) => y(v));
  [[bh.none, SOFT], [bh.discounts, RED], [bh.truck, TEAL]].forEach(([v, c]) => svg.append("path").attr("d", line(v)).attr("fill", "none").attr("stroke", c).attr("stroke-width", 2.2));
})();

// ---------------------------------------------------------------- sentences built from the data
const worst = S[d3.maxIndex(S, (s) => s.fail_none)];
document.getElementById("worst").textContent = `${worst.name} (${whole(worst.fail_none)} failed rides)`;
document.getElementById("perfect").textContent = whole(B.sim.by_forecast.model.failures - B.sim.by_forecast.perfect.failures);
