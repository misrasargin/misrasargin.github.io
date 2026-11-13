// Interactive parts of the A/B test planner. Statistics come from stats.js.
const R = window.ABTEST;
const looks = R.peeking.by_looks;
fillNumbers({ meta: R.meta, peek: { one: looks[0].false_alarm, daily: looks[looks.length - 1].false_alarm } });
const INK = "#16213e", SOFT = "#4d5875", RED = "#d7263d", TEAL = "#12857a";
const $ = (id) => document.getElementById(id);
const whole = (n) => Math.round(n).toLocaleString("en-GB");
const pct = (v, d = 1) => (v * 100).toFixed(d) + "%";
const plural = (n, word) => `${whole(n)} ${word}${n === 1 ? "" : "s"}`;

// ------------------------------------------------------------ planner
function plan() {
  const visitors = +$("v").value, p1 = +$("p").value / 100, lift = +$("l").value / 100;
  const alpha = +$("a").value, pw = +$("pw").value, p2 = Math.min(0.999, p1 * (1 + lift));
  const n = AB.sampleSize(p1, p2, alpha, pw), perDay = visitors / 2;
  const days = Math.ceil(n / perDay), weeks = Math.ceil(days / 7);
  $("v-out").textContent = whole(visitors); $("p-out").textContent = pct(p1); $("l-out").textContent = "+" + Math.round(lift * 100) + "%";
  $("weeks").textContent = weeks > 104 ? "Over 2 years" : plural(weeks, "week");
  $("plan-line").textContent = `${whole(n)} visitors in each group, to tell ${pct(p1)} from ${pct(p2)}. That is ${plural(days, "day")}, rounded up to full weeks.`;
  const two = AB.detectableLift(p1, perDay * 14, alpha, pw);
  $("short-line").textContent = two === null
    ? "With this traffic, two weeks cannot reliably detect any lift."
    : `If you can only run it for two weeks, the smallest lift you can reliably find is +${Math.round(two * 100)}%.`;

  const W = 480, H = 240, m = { t: 14, r: 16, b: 42, l: 48 };
  const svg = d3.select("#curve").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const maxDays = Math.max(14, Math.min(weeks * 7 * 1.6, 800));
  const x = d3.scaleLinear().domain([0, maxDays]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, 1]).range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle").text("days the test runs");
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(pw)).attr("y2", y(pw)).attr("stroke", INK).attr("stroke-dasharray", "4 4");
  const pts = d3.range(1, 121).map((i) => { const d = maxDays * i / 120; return [d, AB.power(p1, p2, perDay * d, alpha)]; });
  svg.append("path").attr("d", d3.line().x((d) => x(d[0])).y((d) => y(d[1]))(pts)).attr("fill", "none").attr("stroke", RED).attr("stroke-width", 2.5);
  const end = Math.min(weeks * 7, maxDays);
  svg.append("line").attr("x1", x(end)).attr("x2", x(end)).attr("y1", y(0)).attr("y2", y(AB.power(p1, p2, perDay * end, alpha))).attr("stroke", SOFT);
  svg.append("circle").attr("cx", x(end)).attr("cy", y(AB.power(p1, p2, perDay * end, alpha))).attr("r", 6).attr("fill", RED).attr("stroke", "#fff").attr("stroke-width", 2);
  svg.append("text").attr("x", m.l + 8).attr("y", y(pw) - 6).attr("class", "note").text("chance to catch a real lift");
}
["v", "p", "l", "a", "pw"].forEach((id) => $(id).addEventListener("input", plan));
plan();

// ------------------------------------------------------------ peeking
(function () {
  const W = 480, H = 260, m = { t: 14, r: 16, b: 42, l: 48 };
  const svg = d3.select("#peek").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([1, 28]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, 0.3]).range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([1, 7, 14, 21, 28]).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 6).attr("text-anchor", "middle").text("times you check the result");
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0.05)).attr("y2", y(0.05)).attr("stroke", INK).attr("stroke-dasharray", "4 4");
  svg.append("text").attr("class", "note").attr("x", W - m.r).attr("y", y(0.05) + 16).attr("text-anchor", "end").text("the 5% you signed up for");
  svg.append("path").attr("d", d3.line().x((d) => x(d.looks)).y((d) => y(d.false_alarm))(looks)).attr("fill", "none").attr("stroke", RED).attr("stroke-width", 2.5);
  svg.append("g").selectAll("circle").data(looks).join("circle").attr("cx", (d) => x(d.looks)).attr("cy", (d) => y(d.false_alarm)).attr("r", 5).attr("fill", RED).attr("stroke", "#fff").attr("stroke-width", 1.5)
    .append("title").text((d) => `${d.looks} checks: ${pct(d.false_alarm)} fake winners`);
  const last = looks[looks.length - 1];
  svg.append("text").attr("x", x(last.looks) - 8).attr("y", y(last.false_alarm) - 10).attr("text-anchor", "end").style("font-weight", 700).attr("fill", RED).text(pct(last.false_alarm, 0) + " fake winners");
})();

// ------------------------------------------------------------ planner check
(function () {
  const rows = R.power_check, W = 480, rowH = 34, H = rows.length * rowH + 40, left = 230;
  const svg = d3.select("#check").attr("viewBox", `0 0 ${W} ${H}`);
  const x = d3.scaleLinear().domain([0.7, 0.9]).range([left, W - 20]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - 30})`).call(d3.axisBottom(x).tickValues([0.7, 0.75, 0.8, 0.85, 0.9]).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("line").attr("x1", x(0.8)).attr("x2", x(0.8)).attr("y1", 0).attr("y2", H - 30).attr("stroke", INK).attr("stroke-dasharray", "4 4");
  const g = svg.selectAll("g.row").data(rows).join("g").attr("class", "row").attr("transform", (_, i) => `translate(0,${i * rowH + rowH / 2})`);
  g.append("text").attr("x", left - 12).attr("dy", "0.35em").attr("text-anchor", "end").text((r) => r.label.split(",").slice(0, 2).join(","));
  g.append("circle").attr("cx", (r) => x(r.power)).attr("r", 6).attr("fill", TEAL).attr("stroke", "#fff").attr("stroke-width", 1.5)
    .append("title").text((r) => `${r.label}: ${whole(r.n_per_group)} per group, caught ${pct(r.power)} of the time`);
})();

// ------------------------------------------------------------ results checker
function check() {
  const nA = Math.max(1, +$("nA").value), nB = Math.max(1, +$("nB").value);
  const xA = Math.min(nA, Math.max(0, +$("xA").value)), xB = Math.min(nB, Math.max(0, +$("xB").value));
  const r = AB.analyse(nA, xA, nB, xB);
  $("r-a").textContent = pct(r.pA, 2); $("r-b").textContent = pct(r.pB, 2);
  $("r-lift").textContent = r.lift === null ? "n/a" : (r.lift >= 0 ? "+" : "") + pct(r.lift, 1);
  $("r-p").textContent = r.p < 0.001 ? "below 0.001" : r.p.toFixed(3);
  const pp = (v) => (Math.abs(v) < 5e-5 ? "0" : (v > 0 ? "+" : "\u2212") + Math.abs(v * 100).toFixed(2));
  $("verdict").textContent = r.p >= 0.05
    ? "Not enough evidence either way. A gap this size shows up by chance too often to call it."
    : r.diff > 0 ? "The new offer is doing better, and chance alone is an unlikely explanation."
    : "The new offer is doing worse, and chance alone is an unlikely explanation.";
  $("ci-line").textContent = `The true difference is probably between ${pp(r.lo)} and ${pp(r.hi)} percentage points (95% interval).`;
  const W = 480, H = 98, m = { l: 20, r: 20 };
  const svg = d3.select("#ci").attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const ext = Math.max(Math.abs(r.lo), Math.abs(r.hi), 0.001) * 1.25;
  const x = d3.scaleLinear().domain([-ext, ext]).range([m.l, W - m.r]);
  svg.append("g").attr("class", "axis").attr("transform", "translate(0,52)").call(d3.axisBottom(x).ticks(5).tickFormat((v) => pp(v)).tickSizeOuter(0));
  svg.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 8).attr("y2", 52).attr("stroke", INK).attr("stroke-dasharray", "3 3");
  const c = r.p < 0.05 ? (r.diff > 0 ? TEAL : RED) : SOFT;
  svg.append("line").attr("x1", x(r.lo)).attr("x2", x(r.hi)).attr("y1", 30).attr("y2", 30).attr("stroke", c).attr("stroke-width", 5);
  svg.append("circle").attr("cx", x(r.diff)).attr("cy", 30).attr("r", 8).attr("fill", c).attr("stroke", "#fff").attr("stroke-width", 2);
  svg.append("text").attr("class", "note").attr("x", W / 2).attr("y", 94).attr("text-anchor", "middle").text("difference in percentage points (0 = no difference)");
}
["nA", "xA", "nB", "xB"].forEach((id) => $(id).addEventListener("input", check));
check();
