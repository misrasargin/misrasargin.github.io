// Interactive charts for the job-skills page. All numbers come from data/results.js.
const J = window.JOBS;
document.querySelectorAll('[data-f="1dp"]').forEach((el) => { el.textContent = el.dataset.k.split(".").reduce((o, k) => o[k], J).toFixed(1); el.removeAttribute("data-k"); });
fillNumbers(J);
const INK = "#16213e", SOFT = "#8f9abc", RED = "#d7263d", TEAL = "#12857a";
const pct = (v, d = 0) => (v * 100).toFixed(d) + "%";
const whole = (n) => Math.round(n).toLocaleString("en-GB");
const ROLES = ["Data analyst", "Data scientist", "Data engineer", "ML / AI engineer"];
const state = { role: "Data analyst", view: "distinct" };

// ------------------------------------------------------------ skills per role
function dumbbell(sel, rows, { a, b, colA, colB, label, whisker, left = 190, W = 760, rowH = 30 }) {
  const H = rows.length * rowH + 44, m = { r: 70 };
  const svg = d3.select(sel).attr("viewBox", `0 0 ${W} ${H}`); svg.selectAll("*").remove();
  const max = d3.max(rows, (r) => Math.max(r[a], r[b], whisker ? r.hi : 0));
  const x = d3.scaleLinear().domain([0, max]).nice().range([left, W - m.r]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - 34})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  svg.append("text").attr("class", "note").attr("x", (left + W - m.r) / 2).attr("y", H - 2).attr("text-anchor", "middle").text(W > 600 ? "share of posts that mention the skill" : "share of posts");
  const g = svg.selectAll("g.row").data(rows).join("g").attr("class", "row").attr("transform", (_, i) => `translate(0,${i * rowH + rowH / 2})`);
  g.append("line").attr("x1", left).attr("x2", W - m.r).attr("stroke", "#e3e8f1");
  g.append("text").attr("x", left - 12).attr("dy", "0.35em").attr("text-anchor", "end").text((r) => r.skill);
  g.append("line").attr("x1", (r) => x(r[a])).attr("x2", (r) => x(r[b])).attr("stroke", SOFT).attr("stroke-width", 2);
  if (whisker) g.append("line").attr("x1", (r) => x(r.lo)).attr("x2", (r) => x(r.hi)).attr("stroke", colB).attr("stroke-width", 4).attr("opacity", 0.35);
  g.append("circle").attr("cx", (r) => x(r[a])).attr("r", 5.5).attr("fill", colA).attr("stroke", "#fff").attr("stroke-width", 1.5);
  g.append("circle").attr("cx", (r) => x(r[b])).attr("r", 6.5).attr("fill", colB).attr("stroke", "#fff").attr("stroke-width", 1.5);
  g.append("text").attr("x", (r) => x(Math.max(r[a], r[b], whisker ? r.hi : 0)) + 10).attr("dy", "0.35em").style("font-weight", 700).text(label);
}
function drawRole() {
  const d = J.roles[state.role];
  const rows = state.view === "distinct"
    ? d.skills.filter((s) => s.distinct).sort((p, q) => q.ratio - p.ratio).slice(0, 12)
    : d.skills.slice(0, 12);
  document.querySelectorAll("#roles button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.r === state.role));
  document.querySelectorAll("#views button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === state.view));
  document.getElementById("role-line").textContent =
    `${whole(d.posts)} posts mention this role. ${pct(d.junior_share)} of them also mention a junior, intern or new-graduate opening.`;
  dumbbell("#skills", rows, { a: "share_other", b: "share", colA: SOFT, colB: RED, whisker: true,
    label: (r) => (state.view === "distinct" ? `×${r.ratio.toFixed(1)}` : pct(r.share)) });
}
const roleBox = document.getElementById("roles");
ROLES.forEach((r) => { const b = document.createElement("button"); b.type = "button"; b.textContent = r; b.dataset.r = r; b.addEventListener("click", () => { state.role = r; drawRole(); }); roleBox.append(b); });
document.querySelectorAll("#views button").forEach((b) => b.addEventListener("click", () => { state.view = b.dataset.v; drawRole(); }));
drawRole();

// ------------------------------------------------------------ first year against last year
(function () {
  const sig = J.trends.filter((t) => t.sig);
  const rows = [...sig.slice(0, 8), ...sig.slice(-5)].filter((t, i, a) => a.indexOf(t) === i);
  const pp = (v) => (v > 0 ? "+" : "−") + Math.abs(v * 100).toFixed(1);
  dumbbell("#trend", rows, { a: "first", b: "last", colA: SOFT, colB: INK, label: (r) => pp(r.diff), left: 150, W: 480, rowH: 27 });
})();

// ------------------------------------------------------------ month by month
(function () {
  const W = 480, H = 300, m = { t: 12, r: 14, b: 34, l: 46 }, n = J.months.length;
  const svg = d3.select("#months").attr("viewBox", `0 0 ${W} ${H}`);
  const series = [["LLMs", TEAL], ["AI agents", RED]].map(([k, c]) => ({ c, v: J.skill_per_month[k].map((x, i) => x / J.posts_per_month[i]) }));
  const x = d3.scaleLinear().domain([0, n - 1]).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(series, (s) => d3.max(s.v))]).nice().range([H - m.b, m.t]);
  const jan = J.months.map((mm, i) => [mm, i]).filter(([mm]) => mm.endsWith("-01"));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(jan.map((d) => d[1])).tickFormat((i) => J.months[i].slice(0, 4)).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".0%")).tickSizeOuter(0));
  const line = d3.line().x((_, i) => x(i)).y((v) => y(v));
  series.forEach((s) => {
    svg.append("path").attr("d", line(s.v)).attr("fill", "none").attr("stroke", s.c).attr("stroke-width", 2.2);
    svg.append("g").selectAll("circle").data(s.v).join("circle").attr("cx", (_, i) => x(i)).attr("cy", (v) => y(v)).attr("r", 2.6).attr("fill", s.c)
      .append("title").text((v, i) => `${J.months[i]}: ${pct(v, 1)}`);
  });
  document.getElementById("avg-posts").textContent = whole(d3.mean(J.posts_per_month));
})();

// ------------------------------------------------------------ check your own skills
(function () {
  const groups = d3.group(J.roles["Any data role"].skills.concat(
    ROLES.flatMap((r) => J.roles[r].skills)).filter((s, i, a) => a.findIndex((t) => t.skill === s.skill) === i), (s) => s.group);
  const box = document.getElementById("groups"), have = new Set(["Python", "SQL", "Statistics"]);
  for (const [name, skills] of groups) {
    const fs = document.createElement("fieldset"); fs.innerHTML = `<legend>${name}</legend>`;
    skills.sort((a, b) => a.skill.localeCompare(b.skill)).forEach((s) => {
      const l = document.createElement("label"); const c = document.createElement("input"); c.type = "checkbox"; c.checked = have.has(s.skill);
      c.addEventListener("change", () => { c.checked ? have.add(s.skill) : have.delete(s.skill); draw(); });
      l.append(c, document.createTextNode(s.skill)); fs.append(l);
    });
    box.append(fs);
  }
  function draw() {
    document.getElementById("fit").innerHTML = ROLES.map((r) => {
      const typical = J.roles[r].skills.filter((s) => s.distinct), got = typical.filter((s) => have.has(s.skill));
      const missing = typical.filter((s) => !have.has(s.skill)).sort((a, b) => b.share - a.share).slice(0, 4);
      return `<div><h3>${r}</h3><span class="score">${got.length} of ${typical.length}</span>
        <div class="meter"><span style="width:${typical.length ? (100 * got.length / typical.length) : 0}%"></span></div>
        <p>${missing.length ? "Most common ones you are missing: " + missing.map((s) => `${s.skill} (${pct(s.share)})`).join(", ") + "." : "You cover every typical skill."}</p></div>`;
    }).join("");
  }
  draw();
})();
