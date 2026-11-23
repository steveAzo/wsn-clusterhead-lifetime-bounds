"""E14 + E14b runner in native Python (replaces run_e14.sh / run_e14b.sh, whose Git-Bash shells were killed by a
console Ctrl+C, exit 0xC000013A). Serial (3.7 GB RAM), resumable: runs whose result line exists are skipped.
Each solver starts in its own process group, detached from any console, so console Ctrl+C events cannot reach it.
Usage (from Paper5/, normally via the scheduled task Paper5_E14): python -I src/scoping/run_e14.py
"""
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
os.chdir(ROOT)
PY = sys.executable
FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
LOG = "results/runner_run_e14.log"


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def has(path, key):
    return os.path.exists(path) and any(key in l for l in open(path, encoding="utf-8"))


def run(args, out, key, last, prefix, wall=True):
    if has(out, key):
        return
    log("start " + " ".join(args))
    t0 = time.time()
    with open(last, "w", encoding="utf-8") as f:
        rc = subprocess.call([PY, "-I"] + args, stdout=f, stderr=subprocess.STDOUT, creationflags=FLAGS)
    lines = [l.rstrip("\n") for l in open(last, encoding="utf-8") if l.startswith(prefix)]
    with open(out, "a", encoding="utf-8") as f:
        if lines:
            for l in lines:
                f.write(l + (f" wall={time.time() - t0:.0f}s" if wall else "") + "\n")
        else:
            f.write(f"FAIL rc={rc} {' '.join(args)}\n")
            f.writelines(open(last, encoding="utf-8").readlines()[-3:])
    log(f"end rc={rc} {time.time() - t0:.0f}s")


def e14():
    out, last, sch = "results/e14_replan.txt", "results/e14_last.log", "src/scoping/e10_lp_protocol.py"
    real = ["--report-cost", "--delay", "--miss", "0.2"]

    def one(m, s, R, realistic):
        nz = "0.1" if realistic else "0.0"
        key = f"LPSCHED {m} {s} seed 0 replan {R} noise {nz}" + (" report-cost delay miss 0.2:" if realistic else ":")
        run([sch, m, s, "0", "--replan", str(R), "--noise", nz, "--iters", "600", "--reiters", "20"] + (real if realistic else []),
            out, key, last, "LPSCHED")

    for m, s in (("FO", "centre"), ("CC2420", "edge")):
        for R in (10, 25, 100, 200):
            one(m, s, R, False)
    run([sch, "CC2420", "edge", "0", "--replan", "50", "--noise", "0.0", "--iters", "600", "--reiters", "20", "--report-cost"],
        out, "LPSCHED CC2420 edge seed 0 replan 50 noise 0.0 report-cost:", last, "LPSCHED")
    one("CC2420", "edge", 50, True)
    for m, s in (("FO", "centre"), ("CC2420", "edge")):
        for R in (10, 25, 100, 200):
            one(m, s, R, True)
    if not has(out, "E14 DONE"):
        open(out, "a", encoding="utf-8").write(f"E14 DONE {time.ctime()}\n")


def e14b():
    out, last = "results/e14b_nrf_v2.txt", "results/e14b_last.log"
    for s in ("far", "edge", "centre"):
        for seed in (0, 1, 2):
            run(["src/scoping/e13_revision.py", "nRF52840", s, str(seed), "--iters", "800"], out,
                f"R13 nRF52840 {s} seed {seed} ", last, "R13", wall=False)
    if not has(out, "E14B DONE"):
        open(out, "a", encoding="utf-8").write(f"E14B DONE {time.ctime()}\n")


if __name__ == "__main__":
    log("runner start")
    e14()
    e14b()
    log("runner done")
