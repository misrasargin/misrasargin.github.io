// Every number in the text is read from the analysis output, so the words can
// never drift away from the results. Usage: <span data-k="meta.votes"></span>
function fillNumbers(data) {
  document.querySelectorAll("[data-k]").forEach((el) => {
    let v = el.dataset.k.split(".").reduce((o, k) => (o == null ? o : o[k]), data);
    if (v == null) { el.textContent = "?"; return; }
    const f = el.dataset.f;
    if (f === "pct") v = Math.round(v * 100) + "%";
    else if (f === "signed") v = signed(v);
    else if (f === "raw") v = String(v);
    else if (f === "2dp") v = v.toFixed(2);
    else if (typeof v === "number") v = v.toLocaleString("en-GB");
    el.textContent = v;
  });
}

// "+4.2", "-0.1", and plain "0.0" when the value rounds to zero
function signed(v) {
  const t = v.toFixed(1);
  return t === "-0.0" || t === "0.0" ? "0.0" : (v > 0 ? "+" : "") + t;
}
