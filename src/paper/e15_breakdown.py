"""Energy breakdown, DIRECT against PSO-C (second review, point 8.4), nRF52840 at the edge sink.

Runs v2.simulate unchanged, but wraps v2.charges so that every charge is also booked to a component:
own report sent to the sink (direct or out-of-range member), member report sent to a CH, CH reception of member
reports, CH aggregated packet to the sink, relaying of other nodes' packets (RX + TX), and control frames.
The wrapper returns exactly what v2.charges returns, so FND is unchanged. Also reports the transmit power steps
used for own reports. Usage (from Paper5/): python -I src/paper/e15_breakdown.py [model] [sink] [layouts]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scoping"))
import e8_model_v2 as v2  # noqa: E402

COMP = ["own report to sink", "member report to CH", "CH reception", "CH packet to sink", "relaying", "control"]
_orig = v2.charges
BOOK = {}


def booked(m, pos, sink, alive, chs, U):
    e = _orig(m, pos, sink, alive, chs, U)
    n = len(pos)
    b = {c: np.zeros(n) for c in COMP}
    al = np.flatnonzero(alive)

    def uplink(j, own_key):
        b[own_key][j] += U[j, j]
        r = U[j].copy()
        r[j] = 0
        b["relaying"] += r

    if len(chs) == 0:
        for j in al:
            uplink(j, "own report to sink")
    else:
        chs = np.asarray(chs)
        d = np.linalg.norm(pos[al, None] - pos[None, chs], axis=2)
        a = d.argmin(1)
        for idx, j in enumerate(al):
            c = chs[a[idx]]
            if j == c:
                continue
            if d[idx, a[idx]] <= m.rmax:
                b["member report to CH"][j] += float(m.tx(d[idx, a[idx]]))
                b["CH reception"][c] += m.erx + m.agg
            else:
                uplink(j, "own report to sink")
        for c in chs:
            b["CH reception"][c] += m.agg
            uplink(c, "CH packet to sink")
            b["control"][c] += m.etx_ctrl
        b["control"][al] += m.erx_ctrl
    tot = sum(b.values())
    assert np.allclose(tot, e), "breakdown does not add up"
    for c in COMP:
        BOOK[c] += b[c]
    return e


def main():
    a = sys.argv[1:]
    name = a[0] if a else "nRF52840v3"
    sname = a[1] if len(a) > 1 else "edge"
    layouts = range(int(a[2]) if len(a) > 2 else 3)
    v2.charges = booked
    m = v2.Model(name)
    sink = np.array(v2.SINKS[sname])
    for seed in layouts:
        pos = np.random.default_rng(100 + seed).uniform(0, 100, (100, 2))
        ds = np.linalg.norm(pos - sink, axis=1)
        if name != "FO":
            idx = np.searchsorted(m.p - m.sens - v2.e1.MARGIN, m.pl0 + 10 * v2.e1.PL_N * np.log10(np.maximum(ds, 1)))
            steps = {f"{m.p[i]:+.0f} dBm ({m.i[i]:.1f} mA)": int((idx == i).sum()) for i in range(len(m.p))}
            print(f"layout {seed}: direct-to-sink power step needed by each node: {steps}; farthest {ds.max():.0f} m")
        for s in ("DIRECT", "PSOC"):
            for c in COMP:
                BOOK[c] = np.zeros(len(pos))
            F = v2.simulate(s, m, pos, sink, 5, np.random.default_rng(11 + seed))
            tot = sum(BOOK.values())
            first = int(np.argmax(tot))  # the node that spent the most is the one that died first (equal E0)
            print(f"  {s:6s} FND {F}: network energy per round {1e3 * tot.sum() / F:.1f} mJ; "
                  f"first-dead node {first} at {ds[first]:.0f} m from sink")
            for c in COMP:
                print(f"    {c:22s} network {1e3 * BOOK[c].sum() / F:7.2f} mJ/round "
                      f"({100 * BOOK[c].sum() / tot.sum():4.1f}%)  first-dead node {1e3 * BOOK[c][first] / F:6.3f} mJ/round "
                      f"({100 * BOOK[c][first] / tot[first]:4.1f}%)")


if __name__ == "__main__":
    main()
