"""Run mapwright's evals with headless Claude Code. Standard library only.

    python evals/run.py                       # every case, its own run count
    python evals/run.py --ids trigger-find-place --runs 3
    python evals/run.py --decoys --runs 1

Each run gets a fresh temp folder holding copies of scripts/ and
tests/fixtures/, then `claude -p --plugin-dir <repo>` (sonnet, stream-json).
A trigger case passes when a Skill tool_use names mapwright (decoys: when
none does). An action case also runs its evidence command in the run folder.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def claude_exe():
    if os.name == "nt":  # bare `claude` is FileNotFound from Python on Windows
        found = shutil.which("claude.cmd") or shutil.which("claude.CMD")
        if found:
            return found
    return shutil.which("claude") or "claude"


def skills_fired(stream):
    names = []
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") if isinstance(ev, dict) else None
        for part in (msg or {}).get("content", []) if isinstance(msg, dict) else []:
            if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Skill":
                names.append(str(part.get("input", {}).get("skill", "")))
    return names


def run_case(case, model, timeout):
    work = tempfile.mkdtemp(prefix="mpw-eval-")
    shutil.copytree(os.path.join(ROOT, "scripts"), os.path.join(work, "scripts"))
    shutil.copytree(os.path.join(ROOT, "tests", "fixtures"), os.path.join(work, "tests", "fixtures"))
    cmd = [claude_exe(), "-p", case["prompt"], "--plugin-dir", ROOT, "--model", model,
           "--output-format", "stream-json", "--verbose"]
    if case.get("kind") == "action":
        cmd += ["--max-turns", str(case.get("max_turns", 30)),
                "--allowedTools", ",".join(case.get("tools", []))]
    else:
        cmd += ["--max-turns", "3"]
    try:
        out = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    fired = skills_fired(out)
    hit = any("mapwright" in n for n in fired)
    ok = (not hit) if case.get("decoy") else hit
    note = ""
    ev = case.get("evidence")
    if ok and ev and ev.get("type") == "command":
        code = subprocess.call(ev["run"], cwd=work, shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok = code == 0
        note = "evidence exit %d" % code
    return {"id": case["id"], "ok": ok, "skills": fired, "note": note, "dir": work}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--decoys", action="store_true", help="only decoy cases")
    ap.add_argument("--runs", type=int, help="override each case's run count")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    cases = json.load(open(os.path.join(ROOT, "evals", "evals.json"), encoding="utf-8"))["evals"]
    if a.ids:
        cases = [c for c in cases if c["id"] in a.ids]
    if a.decoys:
        cases = [c for c in cases if c.get("decoy")]
    results = []
    for c in cases:
        for i in range(a.runs or c.get("runs", 1)):
            r = run_case(c, a.model, a.timeout)
            results.append(r)
            print("%-22s run %d  %s  skills=%s %s" % (c["id"], i + 1, "PASS" if r["ok"] else "FAIL",
                                                     ",".join(r["skills"]) or "-", r["note"]), flush=True)
    passed = sum(r["ok"] for r in results)
    print("%d/%d runs passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
