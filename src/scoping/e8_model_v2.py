"""E8: energy model v2 and lifetime comparison under it.

Changes from E2/E7 (v1):
  - Relaying: a packet to the sink follows the minimum-energy multi-hop path over alive nodes (links <= radio range);
    each relay pays RX + its own TX (v1 charged all relay energy to the sender).
  - Control traffic: in a clustered round every alive node receives one control frame (CTRL_BITS) and every CH sends one
    at maximum power; direct rounds have none.
  - Members join a CH only within single-hop range; otherwise they send directly (multi-hop).
  - First-order (FO) model keeps its unlimited range, as in the literature, so it has no relays.
Strategies: DIRECT, LEACH, KMRE, PSOC as in E2. LP bound v2: column generation with exact pricing including relay loads
and the control term (see price_v2).
Usage: python -I src/scoping/e8_model_v2.py <model> <sink far|edge|centre> <seed> [--lp] [--no-sim]
"""
import heapq
import math
import os
import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_radio_model_gate as e1  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
SINKS = {"far": (50.0, 175.0), "edge": (50.0, 100.0), "centre": (50.0, 50.0)}
CTRL_BITS = 200  # 25-byte control frame
ADV_MODE = "one"  # "one": each alive node receives one control frame per clustered round (paper default);
# "perch": each node receives the advertisement of every CH within range (revision sensitivity, E13)
PRICE_CALLS = [0, 0]  # [calls, calls not solved to proven optimality] (revision instrumentation)
PRICE_TIME_LIMIT = 300  # s per pricing MILP; the UB uses the proven dual bound, so it stays valid if the limit binds
# nRF52840 per the v3.0 product brief (0 dBm 6.40 mA, +8 dBm 16.40 mA, RX 6.26 mA, DC/DC 3 V); intermediate steps are the
# v2.0 values scaled by 6.40/4.80 (approximate, to be replaced by the product specification table).
EXTRA_RADIOS = [
    ("nRF52840v3", 250e3, 3.0, 6.26, [(-20, 3.6), (-8, 4.4), (-4, 5.6), (0, 6.4), (4, 9.3), (8, 16.4)], -100, 40.0),
]


class Model:
    def __init__(self, name):
        self.name = name
        if name == "FO":
            self.rmax = math.inf
            self.erx = e1.K_BITS * e1.E_ELEC
            self.agg = e1.K_BITS * e1.E_DA
            self.erx_ctrl = CTRL_BITS * e1.E_ELEC
            self.etx_ctrl = CTRL_BITS * (e1.E_ELEC + e1.E_MP * 100.0**4)  # advert to ~100 m
        else:
            r = [x for x in e1.RADIOS + EXTRA_RADIOS if x[0] == name][0]
            _, rate, v, irx, levels, sens, pl0 = r
            self.t = e1.K_BITS / rate
            self.v = v
            self.p = np.array([lv[0] for lv in levels], float)
            self.i = np.array([lv[1] for lv in levels], float)
            self.sens, self.pl0 = sens, pl0
            self.erx = irx * 1e-3 * v * self.t
            self.agg = 0.0
            self.rmax = 10 ** ((self.p[-1] - sens - e1.MARGIN - pl0) / (10 * e1.PL_N))
            tc = CTRL_BITS / rate
            self.erx_ctrl = irx * 1e-3 * v * tc
            self.etx_ctrl = self.i[-1] * 1e-3 * v * tc

    def tx(self, d):
        """single-hop TX energy for distance d (array); inf beyond range."""
        d = np.maximum(np.asarray(d, float), 1.0)
        if self.name == "FO":
            return e1.K_BITS * (e1.E_ELEC + np.where(d < e1.D0, e1.E_FS * d**2, e1.E_MP * d**4))
        need = self.pl0 + 10 * e1.PL_N * np.log10(d)
        idx = np.searchsorted(self.p - self.sens - e1.MARGIN, need)
        out = self.i[np.minimum(idx, len(self.p) - 1)] * 1e-3 * self.v * self.t
        return np.where(idx >= len(self.p), np.inf, out)


def uplinks(m, pos, sink, alive):
    """For each alive node, the energy vector of sending one packet to the sink along the min-energy path.
    Returns U (n x n): U[j] = energy charged to each node when j originates one packet. Unreachable -> inf row."""
    n = len(pos)
    al = np.flatnonzero(alive)
    U = np.full((n, n), 0.0)
    if m.name == "FO":
        for j in al:
            U[j, j] = float(m.tx(np.linalg.norm(pos[j] - sink)))
        return U
    # Dijkstra from sink over reverse edges: cost(j -> k) = tx(d_jk) + erx (k relay) ; j -> sink = tx(d_js)
    P = np.vstack([pos[al], sink])
    S = len(al)
    D = np.linalg.norm(P[:, None] - P[None], axis=2)
    W = m.tx(D)
    dist = np.full(S + 1, np.inf)
    nxt = np.full(S + 1, -1)
    dist[S] = 0.0
    h = [(0.0, S)]
    while h:
        c, k = heapq.heappop(h)
        if c > dist[k]:
            continue
        for j in range(S):
            if j == k or not np.isfinite(W[j, k]):
                continue
            nc = c + W[j, k] + (m.erx if k != S else 0.0)
            if nc < dist[j]:
                dist[j], nxt[j] = nc, k
                heapq.heappush(h, (nc, j))
    for a, j in enumerate(al):
        if not np.isfinite(dist[a]):
            U[j, :] = np.inf
            continue
        cur = a
        U[j, j] += W[a, nxt[a]]
        cur = nxt[a]
        while cur != S:
            U[al[cur], al[cur]] += 0  # placeholder for clarity
            U[j, al[cur]] += m.erx + W[cur, nxt[cur]]
            cur = nxt[cur]
    return U


def charges(m, pos, sink, alive, chs, U):
    n = len(pos)
    e = np.zeros(n)
    al = np.flatnonzero(alive)
    if len(chs) == 0:
        return U[al].sum(0)
    chs = np.asarray(chs)
    d = np.linalg.norm(pos[al, None] - pos[None, chs], axis=2)
    a = d.argmin(1)
    dmin = d[np.arange(len(al)), a]
    for idx, j in enumerate(al):
        c = chs[a[idx]]
        if j == c:
            continue
        if dmin[idx] <= m.rmax:
            e[j] += float(m.tx(dmin[idx]))
            e[c] += m.erx + m.agg
        else:
            e += U[j]
    for c in chs:
        e[c] += m.agg
        e += U[c]
        e[c] += m.etx_ctrl
        if ADV_MODE == "perch":
            hear = al[(np.linalg.norm(pos[al] - pos[c], axis=1) <= m.rmax) & (al != c)]
            e[hear] += m.erx_ctrl
    if ADV_MODE != "perch":
        e[al] += m.erx_ctrl
    return e


def simulate(strategy, m, pos, sink, k, rng, E0=0.5, max_rounds=20000):
    import e2_lifetime_gate as e2
    n = len(pos)
    E = np.full(n, E0)
    alive = np.ones(n, bool)
    last_ch = np.full(n, -10**9)
    U = uplinks(m, pos, sink, alive)
    cent = pos[rng.choice(n, k, replace=False)]
    for _ in range(50):
        lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
        cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
    p = 0.05
    for r in range(max_rounds):
        if strategy == "DIRECT":
            chs = []
        elif strategy == "LEACH":
            epoch = int(round(1 / p))
            thr = p / (1 - p * (r % epoch))
            chs = list(np.flatnonzero(alive & (r - last_ch >= epoch) & (rng.random(n) < thr)))
        elif strategy == "KMRE":
            chs = [int(np.flatnonzero(alive & (lab == j))[E[alive & (lab == j)].argmax()]) for j in np.unique(lab[alive])]
        else:  # PSOC
            al = np.flatnonzero(alive)

            def fit(ch):
                d = np.linalg.norm(pos[al, None] - pos[None, ch], axis=2)
                a = d.argmin(1)
                md = max(d[a == j, j].mean() for j in range(len(ch)) if (a == j).any())
                return 0.5 * md + 0.5 * (E[al].sum() / E[ch].sum())
            chs = e2.pso(pos, sink, alive, E, k, fit, rng)
        chs = [c for c in chs if alive[c]]
        last_ch[chs] = r
        c = charges(m, pos, sink, alive, chs, U)
        if not np.isfinite(c).all():
            return r  # a node lost its path to the sink: network partition counts as end of FND window
        E -= c
        if (E[alive] <= 0).any():
            return r + 1
    return max_rounds


def price_v2(y, m, pos, sink, U):
    """Exact weighted pricing for v2: vars o_i (open CH), a_ij (member j -> CH i, i != j, single-hop), s_j (direct), z (clustered)."""
    n = len(pos)
    up = U @ y  # weighted cost of node j originating one uplink packet (relays included)
    d = np.linalg.norm(pos[:, None] - pos[None], axis=2)
    tmem = m.tx(d)
    okm = np.isfinite(tmem) & ~np.eye(n, dtype=bool)
    pairs = np.argwhere(okm.T)  # (i, j) with j able to reach CH i ... argwhere on okm.T gives [i, j] where okm[j, i]
    na = len(pairs)
    nv = n + na + n + 1
    c = np.zeros(nv)
    c[:n] = y * m.agg + up + y * m.etx_ctrl  # open CH i: aggregates own data, sends one uplink, sends advert
    ii, jj = pairs[:, 0], pairs[:, 1]
    c[n:n + na] = y[jj] * tmem[jj, ii] + y[ii] * (m.erx + m.agg)
    c[n + na:n + na + n] = up
    c[-1] = m.erx_ctrl * y.sum()
    if ADV_MODE == "perch":  # opening CH i charges one reception to every other node within range of i
        hearm = (d <= m.rmax) & ~np.eye(n, dtype=bool)
        c[:n] += m.erx_ctrl * (hearm @ y)
        c[-1] = 0.0
    rows, cols, vals = [], [], []
    r = 0
    # each j: o_j + sum_i a_ij + s_j = 1  (a node that is CH is not a member and not direct)
    for j in range(n):
        idx = np.flatnonzero(jj == j)
        rows += [r] * (len(idx) + 2)
        cols += [j] + list(n + idx) + [n + na + j]
        vals += [1.0] * (len(idx) + 2)
        r += 1
    eq = r
    for t in range(na):  # a_ij <= o_i
        rows += [r, r]
        cols += [n + t, int(ii[t])]
        vals += [1.0, -1.0]
        r += 1
    for i in range(n):  # o_i <= z
        rows += [r, r]
        cols += [i, nv - 1]
        vals += [1.0, -1.0]
        r += 1
    M = coo_matrix((vals, (rows, cols)), shape=(r, nv)).tocsr()
    lo = np.r_[np.ones(eq), np.full(r - eq, -np.inf)]
    hi = np.r_[np.ones(eq), np.zeros(r - eq)]
    res = milp(c, constraints=LinearConstraint(M, lo, hi), integrality=np.ones(nv), bounds=Bounds(0, 1),
               options={"mip_rel_gap": 1e-6, "time_limit": PRICE_TIME_LIMIT})
    PRICE_CALLS[0] += 1
    if res.status != 0:
        PRICE_CALLS[1] += 1
    if res.x is None:  # time limit without an incumbent: fall back to the all-direct column, keep the proven bound
        res_x = np.r_[np.zeros(n + na), np.ones(n), 0.0]
    else:
        res_x = res.x
    x = np.round(res_x).astype(int)
    e = np.zeros(n)
    o = x[:n]
    for t in np.flatnonzero(x[n:n + na]):
        i, j = int(ii[t]), int(jj[t])
        e[j] += tmem[j, i]
        e[i] += m.erx + m.agg
    for i in np.flatnonzero(o):
        e += U[i]
        e[i] += m.agg + m.etx_ctrl
        if ADV_MODE == "perch":
            e[hearm[i]] += m.erx_ctrl
    for j in np.flatnonzero(x[n + na:n + na + n]):
        e += U[j]
    if x[-1] and ADV_MODE != "perch":
        e += m.erx_ctrl
    # Return the solver's proven lower bound on the pricing minimum (equals res.fun when solved to optimality), so that
    # the Farley upper bound E0*sum(y)/value stays valid even if the time limit stops the MILP early.
    db = getattr(res, "mip_dual_bound", None)
    val = float(db) if db is not None and np.isfinite(db) else float(res.fun)
    return min(val, float(res.fun)) if res.fun is not None else val, e


def lp_bound(m, pos, sink, iters=300, tol=0.02, warm=300, seed=0):
    n, E0 = len(pos), 0.5
    U = uplinks(m, pos, sink, np.ones(n, bool))
    if not np.isfinite(U).all():
        return None, None
    cols = [charges(m, pos, sink, np.ones(n, bool), [], U)]  # DIRECT column (= U.sum(0) in v2; E11 adds its baseline)
    wr = np.random.default_rng(seed)
    for k in (2, 3, 5, 8, 12, 20):
        cent = pos[wr.choice(n, k, replace=False)]
        for _ in range(30):
            lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
            cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
        for _ in range(warm // 6):
            chs = [int(wr.choice(np.flatnonzero(lab == j))) for j in range(k) if (lab == j).any()]
            cols.append(charges(m, pos, sink, np.ones(n, bool), chs, U))
    pm1, _ = price_v2(np.ones(n), m, pos, sink, U)
    ub = n * E0 / pm1
    yb, alpha = None, 0.7
    lb = 0.0
    for it in range(iters):
        A = np.array(cols).T
        res = linprog(-np.ones(A.shape[1]), A_ub=A, b_ub=np.full(n, E0), bounds=(0, None), method="highs")
        lb = -res.fun
        ylp = -res.ineqlin.marginals
        y = ylp if yb is None else alpha * yb + (1 - alpha) * ylp
        pm, col = price_v2(y, m, pos, sink, U)
        if E0 * y.sum() / pm < ub:
            ub, yb = E0 * y.sum() / pm, y.copy()
        elif yb is None:
            yb = y.copy()
        if ylp @ col >= 1 - 1e-9:
            pm2, col = price_v2(ylp, m, pos, sink, U)
            if E0 * ylp.sum() / pm2 < ub:
                ub, yb = E0 * ylp.sum() / pm2, ylp.copy()
        if ub / lb - 1 < tol:
            break
        cols.append(col)
    return lb, ub


def main():
    a = sys.argv[1:]
    name, sname, seed = a[0], a[1], int(a[2])
    m = Model(name)
    rng = np.random.default_rng(100 + seed)
    pos = rng.uniform(0, 100, (100, 2))
    sink = np.array(SINKS[sname])
    out = {}
    if "--no-sim" not in a:
        for s in ("DIRECT", "LEACH", "KMRE", "PSOC"):
            k = 5
            out[s] = simulate(s, m, pos, sink, k, np.random.default_rng(11 + seed))
    lb = ub = None
    if "--lp" in a:
        t0 = time.time()
        its = int(a[a.index("--iters") + 1]) if "--iters" in a else 300
        lb, ub = lp_bound(m, pos, sink, iters=its, seed=seed)
        out["LP"] = f"[{lb:.1f},{ub:.1f}] ({time.time()-t0:.0f}s)" if lb else "unreachable"
    print(f"V2 {name} {sname} seed {seed} rmax {m.rmax:.0f}: " + " ".join(f"{k}={v}" for k, v in out.items()), flush=True)


if __name__ == "__main__":
    main()
