"""Reads the tools of a repository on this machine that the workflow cannot reach (a work repo
under another GitHub account) and stores only their names in scripts/extra-repos.json.

    python3 scripts/local_repo_tools.py ~/Documents/GitHub/fleetbuddy FleetBuddy

No code and no manifest files leave the machine: just tool names and a count of test files.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo, name = os.path.expanduser(sys.argv[1]), sys.argv[2]

# reuse the exact detection of the stats script, so both count the same way
src = open(os.path.join(ROOT, "scripts", "stats_card.py")).read()
start = src.index("# ---------- tooling and testing, detected automatically ----------")
end = src.index("found = {}\ntest_files = 0")
ns = {"__name__": "detector", "ROOT": ROOT, "TOKEN": "",
      "DEVICON": "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{0}/{0}-{1}.svg"}
exec("import base64, json, os, re, urllib.request, urllib.parse, urllib.error\n" + src[start:end], ns)

paths = [p for p in subprocess.check_output(["git", "-C", repo, "ls-files"], text=True).splitlines()
         if "node_modules/" not in p]
manifest = ("package.json", "requirements.txt", "pyproject.toml")
texts = {p: open(os.path.join(repo, p), errors="replace").read() for p in paths
         if p.rsplit("/", 1)[-1].lower() in manifest or p.lower().endswith(".csproj")}
entry = {"name": name, "tools": sorted(ns["detect"](paths, texts)),
         "test_files": sum(1 for p in paths if ns["TEST_FILE"].search(p.lower()))}

out = os.path.join(ROOT, "scripts", "extra-repos.json")
data = json.load(open(out)) if os.path.exists(out) else []
data = [d for d in data if d["name"] != name] + [entry]
json.dump(data, open(out, "w"), indent=2)
print(f"{name}: {len(entry['tools'])} tools, {entry['test_files']} test files -> scripts/extra-repos.json")
