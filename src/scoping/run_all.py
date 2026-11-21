"""Unattended, resumable orchestrator for the Paper 5 runs (replaces the run_*.sh chain).

Usage (from anywhere):  pythonw -I src/scoping/run_all.py heavy|light
  heavy: E10 (LP schedule as protocol) -> missing E8 case -> E11 (sleep/guard) -> E8 bound re-verification
  light: E12 (tuned GWO/PSO-C and model-aware greedy); no MILP, safe to run beside the heavy lane

Every job is skipped when its result line is already in its results file, so a restart never repeats
finished work. One instance per lane (lock file with PID). Progress: results/orch_<lane>.status;
per-job logs: results/logs/. Started by Windows Task Scheduler (tasks Paper5Runs_heavy/_light) at logon
and every 15 minutes; a second start exits at once while the first is alive.
"""
import os, re, subprocess, sys, time, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
PY = os.path.join(os.path.dirname(sys.executable), "python.exe")
RES = "results"
LOGS = os.path.join(RES, "logs")
os.makedirs(LOGS, exist_ok=True)
NOWIN = 0x08000000  # CREATE_NO_WINDOW


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def has(path, pattern):
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        return any(re.search(pattern, line) for line in f)


def append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")


def pid_alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                         creationflags=NOWIN).stdout
    return str(pid) in out and "python" in out.lower()


def jobs_heavy():
    J = []
    out = f"{RES}/e10_lp_protocol.txt"
    for s in ["centre", "edge", "far"]:
        for m in ["CC2420", "nRF52840v3", "FO"]:
            for seed in [0, 1, 2]:
                for nz in ["0.0", "0.1"]:
                    if s == "far" and m == "CC2420":
                        continue
                    J.append((f"e10_{m}_{s}_{seed}_{nz}", out,
                              re.escape(f"LPSCHED {m} {s} seed {seed} replan 50 noise {nz}:"),
                              ["src/scoping/e10_lp_protocol.py", m, s, str(seed), "--replan", "50", "--noise", nz,
                               "--iters", "600", "--reiters", "20"], "^LPSCHED"))
    J.append(("e8_FO_far_1", f"{RES}/e8_v2.txt", r"^V2 FO far seed 1 ",
              ["src/scoping/e8_model_v2.py", "FO", "far", "1", "--lp", "--iters", "800"], "^V2"))
    J.append(("MARK", out, "E10 DONE", None, None))
    out = f"{RES}/e8_v2_verify.txt"
    for s in ["centre", "edge", "far"]:
        for m in ["CC2420", "nRF52840v3", "FO", "CC1101-868"]:
            for seed in [0, 1, 2]:
                if s == "far" and m == "CC2420":
                    continue
                J.append((f"verify_{m}_{s}_{seed}", out, re.escape(f"V2 {m} {s} seed {seed} "),
                          ["src/scoping/e8_model_v2.py", m, s, str(seed), "--lp", "--no-sim", "--iters", "800"], "^V2"))
    J.append(("MARK", out, "VERIFY DONE", None, None))
    return J + jobs_e13_main()


SETTINGS13 = [("FO", "centre"), ("CC2420", "centre"), ("nRF52840v3", "edge"), ("nRF52840v3", "centre"), ("FO", "edge"),
              ("CC2420", "edge"), ("nRF52840v3", "far"), ("FO", "far"), ("CC1101-868", "centre"),
              ("CC1101-868", "edge"), ("CC1101-868", "far")]


def jobs_e13_main():
    """Revision (2026-11-21): 20 layouts with integer lower bound, ordered by layout so partial results are usable."""
    J = []
    out = f"{RES}/e13_main.txt"
    for seed in range(20):
        for m, s in SETTINGS13:
            J.append((f"e13_{m}_{s}_{seed}", out, re.escape(f"R13 {m} {s} seed {seed} n 100 adv one:"),
                      ["src/scoping/e13_revision.py", m, s, str(seed), "--iters", "800"], "^R13"))
    return J


def jobs_rev_light():
    J = []
    out = f"{RES}/e12_baselines.txt"
    for c in ["FO centre", "CC2420 centre", "nRF52840v3 edge", "FO edge", "CC2420 edge", "nRF52840v3 far",
              "FO far", "nRF52840v3 centre"]:
        m, s = c.split()
        J.append((f"e12_{m}_{s}_2", out, re.escape(f"M12 {m} {s} seed 2:"),
                  ["src/scoping/e12_modern_baselines.py", m, s, "2"], "^M12"))
    out = f"{RES}/e13_lpsched.txt"
    for m, s in [("CC2420", "centre"), ("FO", "centre"), ("nRF52840v3", "edge"), ("nRF52840v3", "centre")]:
        J.append((f"e13b_{m}_{s}_0_rc", out, re.escape(f"LPSCHED {m} {s} seed 0 replan 50 noise 0.0 report-cost:"),
                  ["src/scoping/e10_lp_protocol.py", m, s, "0", "--iters", "600", "--reiters", "20", "--report-cost"],
                  "^LPSCHED"))
        J.append((f"e13b_{m}_{s}_0_real", out,
                  re.escape(f"LPSCHED {m} {s} seed 0 replan 50 noise 0.1 report-cost delay miss 0.2:"),
                  ["src/scoping/e10_lp_protocol.py", m, s, "0", "--iters", "600", "--reiters", "20", "--report-cost",
                   "--delay", "--miss", "0.2", "--noise", "0.1"], "^LPSCHED"))
    out = f"{RES}/e13_adv.txt"
    for seed in range(3):
        for m, s in SETTINGS13[:9]:
            J.append((f"e13adv_{m}_{s}_{seed}", out, re.escape(f"R13 {m} {s} seed {seed} n 100 adv perch:"),
                      ["src/scoping/e13_revision.py", m, s, str(seed), "--adv", "perch"], "^R13"))
    out = f"{RES}/e13_density.txt"
    for nn in (50, 200):
        for seed in range(2):
            for m, s in [("FO", "centre"), ("CC2420", "centre"), ("nRF52840v3", "edge")]:
                J.append((f"e13n_{m}_{s}_{seed}_{nn}", out, re.escape(f"R13 {m} {s} seed {seed} n {nn} adv one:"),
                          ["src/scoping/e13_revision.py", m, s, str(seed), "--n", str(nn)], "^R13"))
    # then help the heavy lane with the main grid from the last layout backwards
    return J + jobs_e13_main()[::-1]


def jobs_e11():
    # moved to the light lane on 2026-11-20 23:45 so it runs beside E10 (memory guard in main)
    J = []
    out = f"{RES}/e11_listening.txt"
    for tr in ["60", "300", "10"]:
        seeds = [0, 1, 2] if tr == "60" else [0]
        for s in ["centre", "edge"]:
            for m in ["CC2420", "nRF52840v3", "FO"]:
                for seed in seeds:
                    J.append((f"e11_{m}_{s}_{seed}_{tr}", out, re.escape(f"L11 {m} {s} seed {seed} Tr {tr}:"),
                              ["src/scoping/e11_listening.py", m, s, str(seed), tr, "--iters", "800"], "^L11"))
        for m in ["nRF52840v3", "FO"]:
            J.append((f"e11_{m}_far_0_{tr}", out, re.escape(f"L11 {m} far seed 0 Tr {tr}:"),
                      ["src/scoping/e11_listening.py", m, "far", "0", tr, "--iters", "800"], "^L11"))
    J.append(("MARK", out, "E11 DONE", None, None))
    return J


def jobs_light():
    J = []
    out = f"{RES}/e12_baselines.txt"
    for seed in [0, 1]:
        for c in ["FO centre", "CC2420 centre", "nRF52840v3 edge", "FO edge", "CC2420 edge", "nRF52840v3 far",
                  "FO far", "nRF52840v3 centre"]:
            m, s = c.split()
            J.append((f"e12_{m}_{s}_{seed}", out, re.escape(f"M12 {m} {s} seed {seed}:"),
                      ["src/scoping/e12_modern_baselines.py", m, s, str(seed)], "^M12"))
    J.append(("MARK", out, "E12 DONE", None, None))
    # verify also runs here (since 2026-11-21 08:45) so it can start before E10 ends; finished jobs are skipped in both lanes
    V = [j for j in jobs_heavy() if j[1].endswith("e8_v2_verify.txt")]
    # after verify, take E10 far-sink jobs from the end of the list (the heavy lane works from the start), 2026-11-21 10:45
    F = [j for j in jobs_heavy() if j[0].startswith("e10_") and "_far_" in j[0]][::-1]
    return J + jobs_e11() + V + F + jobs_rev_light()


def avail_mb():
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2**20


def main():
    lane = sys.argv[1]
    lock = f"{RES}/orch_{lane}.lock"
    status = f"{RES}/orch_{lane}.status"
    if os.path.exists(lock):
        try:
            old = int(open(lock).read().strip())
            if old != os.getpid() and pid_alive(old):
                return
        except Exception:
            pass
    open(lock, "w").write(str(os.getpid()))
    append(f"{RES}/orch_history.log", f"{now()} {lane} start pid {os.getpid()}")
    jobs = jobs_heavy() if lane == "heavy" else jobs_light()
    for name, out, pat, args, keep in jobs:
        if args is None:
            if not has(out, pat):
                append(out, f"{pat} {now()}")
            continue
        if has(out, pat):
            continue
        if lane == "light" and name.startswith(("e11_", "verify_", "e10_", "e13", "e12_")):
            # memory guard: start an E11 job beside the heavy lane only when at least 250 MB is free (idle apps can page out)
            while avail_mb() < 250:
                open(status, "w").write(f"{now()} waiting for memory before {name} ({avail_mb():.0f} MB free)\n")
                time.sleep(60)
        claim = os.path.join(RES, "claims", name)  # revision: the two lanes never run the same job twice
        os.makedirs(os.path.dirname(claim), exist_ok=True)
        if name.startswith("e13"):
            if os.path.exists(claim):
                try:
                    other = int(open(claim).read().strip())
                    if other != os.getpid() and pid_alive(other):
                        continue
                except Exception:
                    pass
            open(claim, "w").write(str(os.getpid()))
        log = os.path.join(LOGS, name + ".log")
        open(status, "w").write(f"{now()} running {name} (log {log})\n")
        t0 = time.time()
        with open(log, "w", encoding="utf-8") as lf:
            rc = subprocess.run([PY, "-I"] + args, stdout=lf, stderr=subprocess.STDOUT, creationflags=NOWIN).returncode
        lines = [l for l in open(log, encoding="utf-8", errors="replace") if re.search(keep, l)]
        if lines:
            append(out, "".join(lines))
        else:
            append(f"{RES}/orch_failures.log", f"{now()} FAIL {name} rc {rc}; see {log}")
        append(f"{RES}/orch_history.log", f"{now()} {lane} {name} rc {rc} {time.time() - t0:.0f}s")
    open(status, "w").write(f"{now()} lane {lane} finished\n")
    append(f"{RES}/orch_history.log", f"{now()} {lane} finished")


if __name__ == "__main__":
    main()
