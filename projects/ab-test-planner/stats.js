// Small statistics library for the A/B test planner.
// Every function here is checked against SciPy in analysis/check_formulas.py.
const AB = (() => {
  // Standard normal CDF (Abramowitz & Stegun 26.2.17, error below 7.5e-8)
  function normCdf(x) {
    const t = 1 / (1 + 0.2316419 * Math.abs(x));
    const d = 0.3989422804014327 * Math.exp(-x * x / 2);
    const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x >= 0 ? 1 - p : p;
  }
  // Inverse of the standard normal CDF (Acklam's algorithm, relative error about 1e-9)
  function normInv(p) {
    const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.383577518672690e2, -3.066479806614716e1, 2.506628277459239];
    const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
    const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
    const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
    const lo = 0.02425;
    if (p < lo) { const q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    if (p > 1 - lo) return -normInv(1 - p);
    const q = p - 0.5, r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  // Visitors needed in EACH group to detect p1 -> p2 (two-sided test of two proportions)
  function sampleSize(p1, p2, alpha = 0.05, power = 0.8) {
    const za = normInv(1 - alpha / 2), zb = normInv(power), pbar = (p1 + p2) / 2;
    const top = za * Math.sqrt(2 * pbar * (1 - pbar)) + zb * Math.sqrt(p1 * (1 - p1) + p2 * (1 - p2));
    return Math.ceil(top * top / ((p2 - p1) * (p2 - p1)));
  }
  // Chance of detecting p1 -> p2 with n visitors in each group
  function power(p1, p2, n, alpha = 0.05) {
    const za = normInv(1 - alpha / 2), pbar = (p1 + p2) / 2;
    const se0 = Math.sqrt(2 * pbar * (1 - pbar) / n), se1 = Math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n);
    const d = Math.abs(p2 - p1);
    return normCdf((d - za * se0) / se1) + normCdf((-d - za * se0) / se1);
  }
  // Smallest relative lift that n visitors per group can detect (found by bisection)
  function detectableLift(p1, n, alpha = 0.05, pw = 0.8) {
    let lo = 0, hi = (1 - p1) / p1;
    if (power(p1, p1 * (1 + hi), n, alpha) < pw) return null;
    for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (power(p1, p1 * (1 + mid), n, alpha) < pw) lo = mid; else hi = mid; }
    return hi;
  }
  // Analyse a finished test: difference, 95% interval, two-sided p-value
  function analyse(nA, xA, nB, xB, alpha = 0.05) {
    const pA = xA / nA, pB = xB / nB, diff = pB - pA, pool = (xA + xB) / (nA + nB);
    const se0 = Math.sqrt(pool * (1 - pool) * (1 / nA + 1 / nB));
    const se1 = Math.sqrt(pA * (1 - pA) / nA + pB * (1 - pB) / nB);
    const z = se0 > 0 ? diff / se0 : 0, zc = normInv(1 - alpha / 2);
    return { pA, pB, diff, z, p: 2 * (1 - normCdf(Math.abs(z))), lo: diff - zc * se1, hi: diff + zc * se1, lift: pA > 0 ? diff / pA : null };
  }
  return { normCdf, normInv, sampleSize, power, detectableLift, analyse };
})();
if (typeof module !== "undefined") module.exports = AB;
