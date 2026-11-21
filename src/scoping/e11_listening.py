"""E11: does the E8 headroom survive sleep/idle energy? (robustness of H3; named as missing in PAPER5_SCOPING Sec 12)

Adds to the v2 model:
  - baseline drain per node per round: platform sleep current (MCU + radio, timer running) x 3 V x reporting interval Tr;
  - TDMA guard time: every reception (member -> CH, relay, control frame) listens GUARD seconds longer at RX current.
Sleep currents (approximate platform values, stated as assumptions): CC2420 on TelosB 5.1 uA; nRF52840 System ON with
RTC 3.0 uA; CC1101 with a low-power MCU 2.0 uA. FO has no sleep term in the literature; for FO the baseline uses the
CC2420 value so the comparison is like for like.
Everything else (layouts, protocols, column generation with exact pricing) is v2 unchanged.
Usage: python -I src/scoping/e11_listening.py <model> <sink> <seed> <Tr seconds> [--iters 800]
Prints: L11 <model> <sink> seed <s> Tr <Tr>: base_mJ= DIRECT= LEACH= KMRE= PSOC= LP=[lb,ub]
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e8_model_v2 as v2  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
SLEEP_UA = {"CC2420": 5.1, "nRF52840v3": 3.0, "CC1101-868": 2.0, "FO": 5.1}
GUARD = 0.002  # s of extra listening per reception
V = 3.0


class ModelL(v2.Model):
    def __init__(self, name, tr):
        super().__init__(name)
        self.base = SLEEP_UA[name] * 1e-6 * V * tr
        if name != "FO":
            irx_w = self.erx / self.t  # RX power (W)
            self.erx += irx_w * GUARD
            self.erx_ctrl += irx_w * GUARD


_charges, _price = v2.charges, v2.price_v2


def charges(m, pos, sink, alive, chs, U):
    e = _charges(m, pos, sink, alive, chs, U)
    e = e.copy()
    e[np.flatnonzero(alive)] += m.base
    return e


def price(y, m, pos, sink, U):
    val, e = _price(y, m, pos, sink, U)
    return val + m.base * float(np.sum(y)), e + m.base


v2.charges, v2.price_v2 = charges, price


def main():
    a = sys.argv[1:]
    name, sname, seed, tr = a[0], a[1], int(a[2]), float(a[3])
    its = int(a[a.index("--iters") + 1]) if "--iters" in a else 800
    m = ModelL(name, tr)
    rng = np.random.default_rng(100 + seed)
    pos = rng.uniform(0, 100, (100, 2))
    sink = np.array(v2.SINKS[sname])
    out = {}
    for s in ("DIRECT", "LEACH", "KMRE", "PSOC"):
        out[s] = v2.simulate(s, m, pos, sink, 5, np.random.default_rng(11 + seed))
    t0 = time.time()
    lb, ub = v2.lp_bound(m, pos, sink, iters=its, seed=seed)
    out["LP"] = f"[{lb:.1f},{ub:.1f}] ({time.time()-t0:.0f}s)" if lb else "unreachable"
    print(f"L11 {name} {sname} seed {seed} Tr {tr:g}: base_mJ={m.base*1e3:.3f} "
          + " ".join(f"{k}={v}" for k, v in out.items()), flush=True)


if __name__ == "__main__":
    main()
