"""Builds assets/stats-{dark,light}.svg: language mix and yearly numbers, in the README style.

Runs in the 'Stats card' workflow with GH_TOKEN (a personal token, so private repos count).
"""
import base64, json, os, re, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ["GH_TOKEN"]
# Notebooks are huge because of stored output, and shader/markup files say little about the code written.
IGNORED = {"Jupyter Notebook", "ShaderLab", "HLSL", "Dockerfile", "Procfile", "Batchfile", "PowerShell", "Shell"}
TOP = 6
DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{0}/{0}-{1}.svg"
LOGOS = {  # GitHub language name -> devicon folder and variant
    "TypeScript": ("typescript", "original"), "JavaScript": ("javascript", "original"),
    "Python": ("python", "original"), "C#": ("csharp", "original"), "Java": ("java", "original"),
    "HTML": ("html5", "original"), "CSS": ("css3", "original"), "SCSS": ("sass", "original"),
    "PHP": ("php", "original"), "Go": ("go", "original-wordmark"), "Rust": ("rust", "original"),
    "C++": ("cplusplus", "original"), "C": ("c", "original"), "Kotlin": ("kotlin", "original"),
    "Swift": ("swift", "original"), "Dart": ("dart", "original"), "Vue": ("vuejs", "original"),
    "TSQL": ("microsoftsqlserver", "plain"), "PLpgSQL": ("postgresql", "original"),
}

def logo(name):
    """Logo as a data URI, or None so the card falls back to a coloured dot."""
    if name not in LOGOS:
        return None
    try:
        with urllib.request.urlopen(DEVICON.format(*LOGOS[name]), timeout=10) as r:
            return "data:image/svg+xml;base64," + base64.b64encode(r.read()).decode()
    except OSError:
        return None

QUERY = """
query($after: String) {
  viewer {
    login
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name owner { login } defaultBranchRef { name } languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
    contributionsCollection {
      contributionCalendar { totalContributions }
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
    }
  }
}"""

def gql(after=None):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"after": after}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["viewer"]

langs, colors, after, repo_count, repo_refs = {}, {}, None, 0, []
while True:
    v = gql(after)
    repos = v["repositories"]
    repo_count = repos["totalCount"]
    for n in repos["nodes"]:
        if n["defaultBranchRef"]:
            repo_refs.append((n["owner"]["login"], n["name"], n["defaultBranchRef"]["name"]))
        for e in n["languages"]["edges"]:
            name = e["node"]["name"]
            if name in IGNORED:
                continue
            langs[name] = langs.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or "#64748b"
    if not repos["pageInfo"]["hasNextPage"]:
        break
    after = repos["pageInfo"]["endCursor"]
cc = v["contributionsCollection"]

total = sum(langs.values()) or 1
ranked = sorted(langs.items(), key=lambda kv: -kv[1])
top = ranked[:TOP]
rest = sum(s for _, s in ranked[TOP:])
parts = [(n, s / total, colors[n]) for n, s in top]
if rest:
    parts.append(("Other", rest / total, "#64748b"))
logos = {n: logo(n) for n, _, _ in parts}

numbers = [
    (f'{cc["contributionCalendar"]["totalContributions"]:,}', "contributions"),
    (f'{cc["totalCommitContributions"] + cc["restrictedContributionsCount"]:,}', "commits incl. private"),
    (f'{cc["totalPullRequestContributions"]:,}', "pull requests"),
    (f'{repo_count:,}', "own repositories"),
]

def b64(p): return base64.b64encode(open(os.path.join(ROOT, p), "rb").read()).decode()
FONTS = ("<style>" + "".join(
    f"@font-face{{font-family:'{n}';src:url(data:font/woff2;base64,{b64('assets/fonts/'+f)}) format('woff2');}}"
    for n, f in [("In", "Inter-400.woff2"), ("InS", "Inter-600.woff2"), ("Mono", "JBM-500.woff2"), ("Sync", "Syncopate-Bold.woff2")])
    + ".i{font-family:'In',Helvetica,Arial,sans-serif}.s{font-family:'InS',Helvetica,Arial,sans-serif;font-weight:600}"
    + ".m{font-family:'Mono',Menlo,Consolas,monospace}.d{font-family:'Sync',Arial Black,sans-serif;font-weight:700}</style>")
THEMES = {
    "dark": dict(panel="#0b0b12", line="#1e293b", fg="#f8fafc", sub="#94a3b8", mute="#64748b", track="#0f172a", tile="#f1f5f9"),
    "light": dict(panel="#ffffff", line="#e2e8f0", fg="#0f172a", sub="#475569", mute="#64748b", track="#f1f5f9", tile="#f8fafc"),
}
SKY, VIO = "#0ea5e9", "#8b5cf6"

def card(t):
    W, H = 1000, 250
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
         f'<clipPath id="bar"><rect x="32" y="74" width="560" height="10" rx="5"/></clipPath></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LANGUAGES</text>',
         f'<rect x="32" y="74" width="560" height="10" rx="5" fill="{t["track"]}"/>', '<g clip-path="url(#bar)">']
    x = 32.0
    for i, (n, f, c) in enumerate(parts):
        w = 560 * f
        o.append(f'<rect x="{x:.2f}" y="74" width="{w:.2f}" height="10" fill="{c}">'
                 f'<animate attributeName="width" values="0;0;{w:.2f}" keyTimes="0;{min(0.9, 0.15*i):.2f};1" dur="{0.6+0.15*i:.2f}s"/></rect>')
        x += w
    o.append('</g>')
    for i, (n, f, c) in enumerate(parts):
        col, row = i % 2, i // 2
        lx, ly = 32 + col * 290, 122 + row * 32
        mark = (f'<image href="{logos[n]}" x="{lx}" y="{ly-15}" width="20" height="20"/>' if logos[n]
                else f'<circle cx="{lx+10}" cy="{ly-5}" r="5" fill="{c}"/>')
        o.append(mark + f'<text x="{lx+30}" y="{ly}" class="i" font-size="14" fill="{t["fg"]}">{n}</text>'
                 f'<text x="{lx+262}" y="{ly}" class="m" font-size="12.5" fill="{t["sub"]}" text-anchor="end">{f*100:.1f}%</text>')
    o.append(f'<line x1="640" y1="32" x2="640" y2="{H-32}" stroke="{t["line"]}"/>')
    o.append(f'<text x="672" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LAST 12 MONTHS</text>')
    for i, (num, label) in enumerate(numbers):
        col, row = i % 2, i // 2
        nx, ny = 672 + col * 160, 104 + row * 82
        o.append(f'<text x="{nx}" y="{ny}" class="s" font-size="30" fill="{t["fg"]}">{num}</text>'
                 f'<text x="{nx}" y="{ny+22}" class="i" font-size="12.5" fill="{t["sub"]}">{label}</text>')
    o.append('</svg>')
    return "\n".join(o)

# ---------- tooling and testing, detected from files in the repos ----------
TOOLS = {  # name: (group, devicon folder, variant)
    "Jest": ("Testing", "jest", "plain"), "Vitest": ("Testing", "vitest", "original"),
    "Playwright": ("Testing", "playwright", "original"), "Cypress": ("Testing", "cypressio", "original"),
    "Pytest": ("Testing", "pytest", "original"), "xUnit": ("Testing", "dot-net", "original"),
    "NUnit": ("Testing", "dot-net", "original"), "MSTest": ("Testing", "dot-net", "original"),
    "GitHub Actions": ("DevOps", "githubactions", "original"), "Docker": ("DevOps", "docker", "original"),
    "ESLint": ("DevOps", "eslint", "original"), "Azure": ("DevOps", "azure", "original"),
    "React": ("Frameworks", "react", "original"), "NestJS": ("Frameworks", "nestjs", "original"),
    "Next.js": ("Frameworks", "nextjs", "original"), "Express": ("Frameworks", "express", "original"),
    ".NET": ("Frameworks", "dotnetcore", "original"), "Vite": ("Frameworks", "vitejs", "original"),
    "Tailwind": ("Frameworks", "tailwindcss", "original"), "Unity": ("Frameworks", "unity", "original"),
    "FastAPI": ("Frameworks", "fastapi", "original"), "Flask": ("Frameworks", "flask", "original"),
    "Supabase": ("Data & AI", "supabase", "original"), "MySQL": ("Data & AI", "mysql", "original"),
    "PostgreSQL": ("Data & AI", "postgresql", "original"), "Prisma": ("Data & AI", "prisma", "original"),
    "Pandas": ("Data & AI", "pandas", "original"), "NumPy": ("Data & AI", "numpy", "original"),
    "scikit-learn": ("Data & AI", "scikitlearn", "original"), "TensorFlow": ("Data & AI", "tensorflow", "original"),
    "PyTorch": ("Data & AI", "pytorch", "original"), "OpenCV": ("Data & AI", "opencv", "original"),
    "Jupyter": ("Data & AI", "jupyter", "original"), "EF Core": ("Data & AI", "dot-net", "original"),
}
PATH_RULES = [  # (substring or suffix test on a lower-case path, tool)
    (lambda p: p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")), "GitHub Actions"),
    (lambda p: p.rsplit("/", 1)[-1] in ("dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"), "Docker"),
    (lambda p: "/jest.config." in "/" + p, "Jest"), (lambda p: "/vitest.config." in "/" + p, "Vitest"),
    (lambda p: "/playwright.config." in "/" + p, "Playwright"), (lambda p: "/cypress.config." in "/" + p, "Cypress"),
    (lambda p: p.endswith(("pytest.ini", "conftest.py")), "Pytest"),
    (lambda p: "/.eslintrc" in "/" + p or "/eslint.config." in "/" + p, "ESLint"),
    (lambda p: p.endswith(".csproj"), ".NET"), (lambda p: p.endswith(".ipynb"), "Jupyter"),
    (lambda p: p.endswith("projectsettings/projectversion.txt"), "Unity"),
    (lambda p: "/vite.config." in "/" + p, "Vite"), (lambda p: "/tailwind.config." in "/" + p, "Tailwind"),
    (lambda p: p.endswith("nest-cli.json"), "NestJS"), (lambda p: "/next.config." in "/" + p, "Next.js"),
    (lambda p: p.startswith("supabase/") or "/supabase/migrations/" in p, "Supabase"),
    (lambda p: p.endswith("schema.prisma"), "Prisma"),
]
NPM = {"jest": "Jest", "vitest": "Vitest", "@playwright/test": "Playwright", "cypress": "Cypress",
       "react": "React", "@nestjs/core": "NestJS", "next": "Next.js", "express": "Express", "vite": "Vite",
       "tailwindcss": "Tailwind", "@supabase/supabase-js": "Supabase", "mysql2": "MySQL", "mysql": "MySQL",
       "pg": "PostgreSQL", "prisma": "Prisma", "@prisma/client": "Prisma", "eslint": "ESLint"}
PIP = {"pytest": "Pytest", "pandas": "Pandas", "numpy": "NumPy", "scikit-learn": "scikit-learn",
       "tensorflow": "TensorFlow", "torch": "PyTorch", "opencv-python": "OpenCV", "fastapi": "FastAPI",
       "flask": "Flask", "psycopg2": "PostgreSQL", "psycopg2-binary": "PostgreSQL", "mysql-connector-python": "MySQL"}
NUGET = {"xunit": "xUnit", "nunit": "NUnit", "mstest.testframework": "MSTest",
         "microsoft.entityframeworkcore": "EF Core", "npgsql": "PostgreSQL", "mysql.data": "MySQL",
         "pomelo.entityframeworkcore.mysql": "MySQL", "azure.": "Azure"}

def rest(path, raw=False):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": f"bearer {TOKEN}",
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace") if raw else json.load(r)

found = {}
test_files = 0
TEST_FILE = re.compile(r"(\.(test|spec)\.[cm]?[jt]sx?$)|(^|/)test_[^/]+\.py$|(^|/)[^/]+_test\.py$|tests?\.cs$|(^|/)cypress/e2e/")
for owner, name, branch in repo_refs:
    hits = set()
    try:
        tree = rest(f"/repos/{owner}/{name}/git/trees/{urllib.parse.quote(branch)}?recursive=1")["tree"]
    except (urllib.error.HTTPError, KeyError):
        continue
    paths = [e["path"] for e in tree if e["type"] == "blob" and "node_modules/" not in e["path"]]
    test_files += sum(1 for p in paths if TEST_FILE.search(p.lower()))
    for p in paths:
        lp = p.lower()
        for test, tool in PATH_RULES:
            if test(lp):
                hits.add(tool)
    manifests = [p for p in paths if p.rsplit("/", 1)[-1].lower() in ("package.json", "requirements.txt") or p.lower().endswith(".csproj")]
    for p in manifests[:15]:
        try:
            text = rest(f"/repos/{owner}/{name}/contents/{urllib.parse.quote(p)}?ref={urllib.parse.quote(branch)}", raw=True)
        except urllib.error.HTTPError:
            continue
        low = p.lower()
        if low.endswith("package.json"):
            try:
                pkg = json.loads(text)
            except ValueError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            hits |= {tool for dep, tool in NPM.items() if dep in deps}
        elif low.endswith("requirements.txt"):
            names = {l.split("==")[0].split(">=")[0].split("[")[0].strip().lower() for l in text.splitlines() if l.strip() and not l.startswith("#")}
            hits |= {tool for dep, tool in PIP.items() if dep in names}
        else:
            t = text.lower()
            hits |= {tool for dep, tool in NUGET.items() if f'include="{dep}' in t}
    for h in hits:
        found[h] = found.get(h, 0) + 1

GROUPS = ["Testing", "DevOps", "Frameworks", "Data & AI"]
tool_logo_cache = {}
def tool_logo(folder, variant):
    key = (folder, variant)
    if key not in tool_logo_cache:
        try:
            with urllib.request.urlopen(DEVICON.format(folder, variant), timeout=10) as r:
                tool_logo_cache[key] = "data:image/svg+xml;base64," + base64.b64encode(r.read()).decode()
        except OSError:
            tool_logo_cache[key] = None
    return tool_logo_cache[key]

def tools_card(t):
    rows = [(g, sorted([n for n in found if TOOLS[n][0] == g], key=lambda n: (-found[n], n))[:6]) for g in GROUPS]
    rows = [(g, items) for g, items in rows if items]
    W, rh = 1000, 64
    H = 70 + len(rows) * rh + 14
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">TOOLING &amp; TESTING</text>',
         f'<text x="{W-32}" y="44" class="m" font-size="11" fill="{t["mute"]}" text-anchor="end">detected in my repositories</text>']
    for r, (g, items) in enumerate(rows):
        y = 70 + r * rh
        if r:
            o.append(f'<line x1="32" y1="{y}" x2="{W-32}" y2="{y}" stroke="{t["line"]}"/>')
        o.append(f'<text x="32" y="{y+31}" class="s" font-size="13" fill="{t["sub"]}">{g.replace("&", "&amp;")}</text>')
        if g == "Testing" and test_files:
            o.append(f'<text x="32" y="{y+48}" class="m" font-size="10.5" fill="{SKY}">{test_files:,} test files</text>')
        for k, n in enumerate(items):
            x = 176 + k * 136
            lg = tool_logo(*TOOLS[n][1:])
            o.append(f'<rect x="{x-4}" y="{y+14}" width="34" height="34" rx="8" fill="{t["tile"]}" stroke="{t["line"]}"/>')
            o.append(f'<image href="{lg}" x="{x+2}" y="{y+20}" width="22" height="22"/>' if lg
                     else f'<circle cx="{x+13}" cy="{y+31}" r="6" fill="{SKY}"/>')
            o.append(f'<text x="{x+36}" y="{y+29}" class="i" font-size="13.5" fill="{t["fg"]}">{n}</text>'
                     f'<text x="{x+36}" y="{y+46}" class="m" font-size="10.5" fill="{t["mute"]}">{found[n]} repo{"s" if found[n] != 1 else ""}</text>')
    o.append('</svg>')
    return "\n".join(o)

for name, t in THEMES.items():
    with open(os.path.join(ROOT, "assets", f"stats-{name}.svg"), "w") as f:
        f.write(card(t))
    with open(os.path.join(ROOT, "assets", f"tools-{name}.svg"), "w") as f:
        f.write(tools_card(t))
print("test files:", test_files)
print("tools:", ", ".join(f"{n} {c}" for n, c in sorted(found.items(), key=lambda kv: -kv[1])))
print("languages:", ", ".join(f"{n} {f*100:.1f}%" for n, f, _ in parts))
