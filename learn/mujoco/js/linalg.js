// Small dense linear algebra and quaternion helpers for the labs. Matrices are
// arrays of rows; sizes here are at most about 10, so clarity beats speed.
// Quaternions are [w, x, y, z], MuJoCo's order.

/** Eigen-decomposition of a symmetric matrix by cyclic Jacobi rotations.
 *  Returns {values, vectors} with vectors[k] the eigenvector for values[k]. */
export function symEig(A0) {
  const n = A0.length;
  const A = A0.map((r) => r.slice());
  const V = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < 60; sweep++) {
    let off = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += A[i][j] * A[i][j];
    if (off < 1e-30) break;
    for (let p = 0; p < n; p++) {
      for (let q = p + 1; q < n; q++) {
        if (Math.abs(A[p][q]) < 1e-300) continue;
        const theta = (A[q][q] - A[p][p]) / (2 * A[p][q]);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1), s = t * c;
        for (let k = 0; k < n; k++) {            // A <- A G, V <- V G (columns p, q)
          const akp = A[k][p], akq = A[k][q];
          A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq;
          const vkp = V[k][p], vkq = V[k][q];
          V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq;
        }
        for (let k = 0; k < n; k++) {            // A <- G^T A (rows p, q)
          const apk = A[p][k], aqk = A[q][k];
          A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk;
        }
      }
    }
  }
  return { values: A.map((r, i) => r[i]), vectors: Array.from({ length: n }, (_, k) => V.map((row) => row[k])) };
}

/** Solve A x = b by Gaussian elimination with partial pivoting. */
export function solve(A0, b0) {
  const n = A0.length;
  const A = A0.map((r, i) => [...r, b0[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
    [A[c], A[p]] = [A[p], A[c]];
    for (let r = c + 1; r < n; r++) {
      const f = A[r][c] / A[c][c];
      for (let k = c; k <= n; k++) A[r][k] -= f * A[c][k];
    }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) {
    let s = A[r][n];
    for (let k = r + 1; k < n; k++) s -= A[r][k] * x[k];
    x[r] = s / A[r][r];
  }
  return x;
}

export const transpose = (M) => M[0].map((_, j) => M.map((r) => r[j]));
export const matMul = (A, B) => A.map((r) => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));
export const matVec = (A, x) => A.map((r) => r.reduce((s, v, k) => s + v * x[k], 0));
export const norm = (v) => Math.hypot(...v);

/** Rotation matrix (row-major, 9 numbers, as MuJoCo's xmat) to a unit quaternion. */
export function quatFromMat(m) {
  const [r00, r01, r02, r10, r11, r12, r20, r21, r22] = m;
  const tr = r00 + r11 + r22;
  let q;
  if (tr > 0) { const s = 2 * Math.sqrt(tr + 1); q = [0.25 * s, (r21 - r12) / s, (r02 - r20) / s, (r10 - r01) / s]; }
  else if (r00 > r11 && r00 > r22) { const s = 2 * Math.sqrt(1 + r00 - r11 - r22); q = [(r21 - r12) / s, 0.25 * s, (r01 + r10) / s, (r02 + r20) / s]; }
  else if (r11 > r22) { const s = 2 * Math.sqrt(1 + r11 - r00 - r22); q = [(r02 - r20) / s, (r01 + r10) / s, 0.25 * s, (r12 + r21) / s]; }
  else { const s = 2 * Math.sqrt(1 + r22 - r00 - r11); q = [(r10 - r01) / s, (r02 + r20) / s, (r12 + r21) / s, 0.25 * s]; }
  const n = norm(q);
  return q.map((v) => v / n);
}
export const quatMul = (a, b) => [
  a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
  a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
  a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
  a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
export const quatConj = (q) => [q[0], -q[1], -q[2], -q[3]];
/** Rotation vector (axis times angle, angle in [0, pi]) of a unit quaternion. */
export function quatToRotvec(q0) {
  const q = q0[0] < 0 ? q0.map((v) => -v) : q0;     // the shorter way round
  const s = norm(q.slice(1));
  if (s < 1e-12) return [2 * q[1], 2 * q[2], 2 * q[3]];
  const angle = 2 * Math.atan2(s, q[0]);
  return q.slice(1).map((v) => (v / s) * angle);
}
