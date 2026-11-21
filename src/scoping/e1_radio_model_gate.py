"""E1 gate (idea 3 reframe): does the first-order radio model create the gain that cluster-head optimisation claims?

Per-round network energy (one k-bit report per node, perfect aggregation at cluster heads, the LEACH setting)
under two energy models:
  FO   : first-order radio model (Heinzelman 2002 constants), cost grows as d^2 / d^4 without a range limit.
  REAL : datasheet transceiver; transmit current at the lowest power step that closes the link under a
         log-distance path loss with fade margin; links beyond max range are relayed in equal hops (relays pay RX+TX).
Strategies: DIRECT (every node to sink), LEACH-like random CHs (mean over draws), OPT (CH set optimised by
multi-start local search on the same energy model = what a perfect swarm optimiser could reach).
Usage: python -I src/scoping/e1_radio_model_gate.py
"""
import math
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
K_BITS = 4000
E_ELEC, E_FS, E_MP, E_DA = 50e-9, 10e-12, 0.0013e-12, 5e-9
D0 = math.sqrt(E_FS / E_MP)

# Datasheet radios: (name, bitrate bps, supply V, RX mA, [(dBm, TX mA)], sensitivity dBm, PL(1 m) dB)
RADIOS = [
    ("CC2420", 250e3, 3.0, 18.8, [(-25, 8.5), (-15, 9.9), (-10, 11.2), (-7, 12.5), (-5, 13.9), (-3, 15.2), (-1, 16.5), (0, 17.4)], -95, 40.0),
    ("nRF52840", 250e3, 3.0, 4.6, [(-20, 2.7), (-8, 3.3), (-4, 4.2), (0, 4.8), (4, 7.0), (8, 14.8)], -100, 40.0),
    ("CC1101-868", 38.4e3, 3.0, 15.7, [(-30, 12.3), (-20, 14.4), (-10, 15.5), (0, 16.8), (5, 20.0), (10, 30.0)], -104, 31.2),
]
PL_N, MARGIN = 2.7, 10.0


def fo_tx(d):
    return K_BITS * (E_ELEC + (E_FS * d**2 if d < D0 else E_MP * d**4))


def make_real(radio):
    name, rate, v, irx, levels, sens, pl0 = radio
    t_pkt = K_BITS / rate
    erx = irx * 1e-3 * v * t_pkt
    budget = lambda p: p - sens - MARGIN - pl0  # noqa: E731
    rmax = 10 ** (budget(levels[-1][0]) / (10 * PL_N))

    def hop_tx(d):
        for p, i in levels:
            if pl0 + 10 * PL_N * math.log10(max(d, 1.0)) <= p - sens - MARGIN:
                return i * 1e-3 * v * t_pkt
        return None

    def tx(d):  # cost of delivering one packet over distance d, relayed if needed, excluding final RX
        h = max(1, math.ceil(d / rmax))
        return h * hop_tx(d / h) + (h - 1) * erx

    return tx, erx, rmax


def round_energy(pos, sink, chs, tx, erx, agg):
    if len(chs) == 0:
        return sum(tx(np.linalg.norm(p - sink)) for p in pos)
    c = pos[chs]
    dist = np.linalg.norm(pos[:, None, :] - c[None, :, :], axis=2)
    assign = dist.argmin(1)
    e = 0.0
    for i, p in enumerate(pos):
        if i in chs:
            continue
        e += tx(dist[i, assign[i]]) + erx
    for j, ch in enumerate(chs):
        members = int((assign == j).sum())  # includes the CH itself
        e += agg * members
        e += tx(np.linalg.norm(pos[ch] - sink))
    return e


def optimise(pos, sink, k, tx, erx, agg, rng, starts=6, iters=400):
    best, best_e = None, math.inf
    n = len(pos)
    for _ in range(starts):
        chs = list(rng.choice(n, k, replace=False))
        e = round_energy(pos, sink, chs, tx, erx, agg)
        for _ in range(iters):
            j = rng.integers(k)
            cand = chs.copy()
            new = rng.integers(n)
            if new in cand:
                continue
            cand[j] = new
            ce = round_energy(pos, sink, cand, tx, erx, agg)
            if ce < e:
                chs, e = cand, ce
        if e < best_e:
            best, best_e = chs, e
    return best, best_e


def kmeans_chs(pos, sink, k, rng, tx, erx, agg, restarts=5):
    """Simple deterministic-style heuristic: k-means on positions, CH = node nearest each centroid;
    k chosen from 1..10 by the same energy model (a planner could do this once, offline)."""
    best, best_e = None, math.inf
    for kk in range(1, 11):
        for _ in range(restarts):
            cent = pos[rng.choice(len(pos), kk, replace=False)]
            for _ in range(30):
                lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
                cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(kk)])
            chs = sorted({int(np.linalg.norm(pos - c, axis=1).argmin()) for c in cent})
            e = round_energy(pos, sink, chs, tx, erx, agg)
            if e < best_e:
                best, best_e = chs, e
    return best, best_e


def main():
    if "--kmeans" in sys.argv:
        return main_kmeans()
    _main()


def main_kmeans():
    rng = np.random.default_rng(2)
    scenarios = [("100x100, sink (50,175)", 100, np.array([50.0, 175.0])),
                 ("100x100, sink centre", 100, np.array([50.0, 50.0])),
                 ("200x200, sink (100,100)", 200, np.array([100.0, 100.0]))]
    print("E1b: OPT (free k 1..10, local search) vs KMEANS heuristic (k chosen by model) vs DIRECT")
    for sname, side, sink in scenarios:
        pos = rng.uniform(0, side, (100, 2))
        print(f"\n=== {sname}")
        models = [("FO (Heinzelman)", fo_tx, K_BITS * E_ELEC, K_BITS * E_DA)]
        for r in RADIOS:
            tx, erx, _ = make_real(r)
            models.append((r[0], tx, erx, 0.0))
        for mname, tx, erx, agg in models:
            ed = round_energy(pos, sink, [], tx, erx, agg)
            km, ek = kmeans_chs(pos, sink, 5, rng, tx, erx, agg)
            eo, ko = math.inf, None
            for kk in (1, 2, 3, 5, 8):
                _, e = optimise(pos, sink, kk, tx, erx, agg, rng, starts=3, iters=300)
                if e < eo:
                    eo, ko = e, kk
            best_simple = min(ed, ek)
            print(f"{mname:16s} DIRECT {ed*1e3:8.2f}  KMEANS(k={len(km)}) {ek*1e3:8.2f}  OPT(k={ko}) {eo*1e3:8.2f}"
                  f"  | OPT vs best simple: {100*(1-eo/best_simple):5.1f}% saving")


def _main():
    rng = np.random.default_rng(1)
    scenarios = [("100x100, sink (50,175)", 100, np.array([50.0, 175.0])),
                 ("100x100, sink centre", 100, np.array([50.0, 50.0])),
                 ("200x200, sink (100,100)", 200, np.array([100.0, 100.0]))]
    k = 5
    print(f"k={k}, N=100, {K_BITS} bit, PL exponent {PL_N}, margin {MARGIN} dB; d0(FO)={D0:.1f} m")
    for sname, side, sink in scenarios:
        pos = rng.uniform(0, side, (100, 2))
        print(f"\n=== {sname}")
        models = [("FO (Heinzelman)", fo_tx, K_BITS * E_ELEC, K_BITS * E_DA, None)]
        for r in RADIOS:
            tx, erx, rmax = make_real(r)
            models.append((f"{r[0]} (range {rmax:.0f} m)", tx, erx, 0.0, rmax))
        print(f"{'model':28s} {'DIRECT':>9s} {'LEACH':>9s} {'OPT':>9s} | OPT/LEACH  OPT/DIRECT  LEACH/DIRECT  RX share(OPT)")
        for mname, tx, erx, agg, _ in models:
            ed = round_energy(pos, sink, [], tx, erx, agg)
            el = np.mean([round_energy(pos, sink, list(rng.choice(100, k, replace=False)), tx, erx, agg) for _ in range(200)])
            chs, eo = optimise(pos, sink, k, tx, erx, agg, rng)
            rx_share = (100 - k) * erx / eo
            print(f"{mname:28s} {ed*1e3:9.3f} {el*1e3:9.3f} {eo*1e3:9.3f} | {eo/el:9.3f}  {eo/ed:10.3f}  {el/ed:12.3f}  {rx_share:8.2f}")


if __name__ == "__main__":
    main()
