"""Builds assets/stats-{dark,light}.svg: language mix and yearly numbers, in the README style.

Runs in the 'Stats card' workflow with GH_TOKEN (a personal token, so private repos count).
"""
import base64, json, math, os, re, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ["GH_TOKEN"]
# Notebooks are huge because of stored output, and shader/markup files say little about the code written.
IGNORED = {"Jupyter Notebook", "ShaderLab", "HLSL", "Dockerfile", "Procfile", "Batchfile", "PowerShell", "Shell"}
TOP = 6
# Organisations whose repositories are my own work too (my own startup), counted like personal repos.
EXTRA_ORGS = ["Alpha-Stock"]
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

ORG_QUERY = """
query($org: String!, $after: String) {
  organization(login: $org) {
    repositories(first: 100, after: $after, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name owner { login } defaultBranchRef { name } languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
  }
}"""

def gql(after=None, query=QUERY, **extra):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"after": after, **extra}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["viewer"] if query is QUERY else body["data"]["organization"]

langs, colors, repo_count, repo_refs = {}, {}, 0, []

def take(repos):
    global repo_count
    repo_count += len(repos["nodes"])
    for n in repos["nodes"]:
        if n["defaultBranchRef"]:
            repo_refs.append((n["owner"]["login"], n["name"], n["defaultBranchRef"]["name"]))
        for e in n["languages"]["edges"]:
            name = e["node"]["name"]
            if name in IGNORED:
                continue
            langs[name] = langs.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or "#64748b"

after = None
while True:
    v = gql(after)
    take(v["repositories"])
    if not v["repositories"]["pageInfo"]["hasNextPage"]:
        break
    after = v["repositories"]["pageInfo"]["endCursor"]
cc = v["contributionsCollection"]
for org in EXTRA_ORGS:
    after = None
    while True:
        repos = gql(after, ORG_QUERY, org=org)["repositories"]
        take(repos)
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]

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
    (f'{repo_count:,}', "repositories"),
]

def b64(p): return base64.b64encode(open(os.path.join(ROOT, p), "rb").read()).decode()
FONTS = ("<style>" + "".join(
    f"@font-face{{font-family:'{n}';src:url(data:font/woff2;base64,{b64('assets/fonts/'+f)}) format('woff2');}}"
    for n, f in [("In", "Inter-400.woff2"), ("InS", "Inter-600.woff2"), ("Mono", "JBM-500.woff2"), ("Sync", "Syncopate-Bold.woff2")])
    + ".i{font-family:'In',Helvetica,Arial,sans-serif}.s{font-family:'InS',Helvetica,Arial,sans-serif;font-weight:600}"
    + ".m{font-family:'Mono',Menlo,Consolas,monospace}.d{font-family:'Sync',Arial Black,sans-serif;font-weight:700}</style>")
THEMES = {
    "dark": dict(panel="#0b0b12", line="#1e293b", fg="#f8fafc", sub="#94a3b8", mute="#64748b", track="#0f172a", tile="#f1f5f9", btile="#111827", plate="#e2e8f0"),
    "light": dict(panel="#ffffff", line="#e2e8f0", fg="#0f172a", sub="#475569", mute="#64748b", track="#f1f5f9", tile="#f8fafc", btile="#f8fafc", plate=None),
}
SKY, VIO = "#0ea5e9", "#8b5cf6"
# Donut colours by rank, from sky to violet, so the card stays in the README palette
DONUT = ["#0ea5e9", "#38bdf8", "#7dd3fc", "#6366f1", "#8b5cf6", "#c4b5fd", "#94a3b8"]

def card(t):
    W, H = 1000, 250
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LANGUAGES</text>']
    # donut: one circle per language, drawn with a dash on a shared ring
    cx, cy, r, sw = 112, 146, 64, 22
    circ = 2 * math.pi * r
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["track"]}" stroke-width="{sw}"/>')
    start = 0.0
    for i, (n, f, c) in enumerate(parts):
        seg = max(circ * f - 2, 0.6)  # small gap between segments
        col = DONUT[i] if n != "Other" else "#94a3b8"
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" '
                 f'stroke-dasharray="{seg:.2f} {circ:.2f}" stroke-dashoffset="{-start:.2f}" transform="rotate(-90 {cx} {cy})">'
                 f'<animate attributeName="stroke-dasharray" values="0 {circ:.2f};0 {circ:.2f};{seg:.2f} {circ:.2f}" '
                 f'keyTimes="0;{min(0.85, 0.12*i):.2f};1" dur="{0.7+0.12*i:.2f}s"/></circle>')
        start += circ * f
    for i, (n, f, c) in enumerate(parts):
        col, row = i // 4, i % 4
        lx, ly = 228 + col * 200, 92 + row * 34
        swatch = DONUT[i] if n != "Other" else "#94a3b8"
        mark = (f'<image href="{logos[n]}" x="{lx+12}" y="{ly-15}" width="20" height="20"/>' if logos[n]
                else f'<circle cx="{lx+22}" cy="{ly-5}" r="5" fill="{swatch}"/>')
        o.append(f'<rect x="{lx}" y="{ly-15}" width="4" height="20" rx="2" fill="{swatch}"/>' + mark
                 + f'<text x="{lx+42}" y="{ly}" class="i" font-size="14" fill="{t["fg"]}">{n}</text>'
                 f'<text x="{lx+178}" y="{ly}" class="m" font-size="12.5" fill="{t["sub"]}" text-anchor="end">{f*100:.1f}%</text>')
    o.append(f'<line x1="640" y1="32" x2="640" y2="{H-32}" stroke="{t["line"]}"/>')
    o.append(f'<text x="672" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LAST 12 MONTHS</text>')
    for i, (num, label) in enumerate(numbers):
        col, row = i % 2, i // 2
        nx, ny = 672 + col * 160, 104 + row * 82
        o.append(f'<text x="{nx}" y="{ny}" class="s" font-size="30" fill="{t["fg"]}">{num}</text>'
                 f'<text x="{nx}" y="{ny+22}" class="i" font-size="12.5" fill="{t["sub"]}">{label}</text>')
    o.append('</svg>')
    return "\n".join(o)

# ---------- tooling and testing, detected automatically ----------
# Every dependency and config file is matched against the devicon catalogue (about 470 tools
# with tags), so a tool I start using shows up by itself, with its logo and a group taken
# from its tags. Only display names, a few aliases and group corrections are set by hand.
with urllib.request.urlopen("https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/devicon.json", timeout=30) as r:
    CATALOG = {e["name"]: e for e in json.load(r)}
SKIP_TAGS = {"language", "editor", "ide", "os", "browser"}  # languages sit in the donut already
SKIP = {"nodejs", "npm", "yarn", "pnpm", "git", "github", "json", "markdown", "yaml", "babel", "html5", "css3", "bash"}

def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
LOOKUP = {}
for e in CATALOG.values():
    if e["name"] in SKIP or SKIP_TAGS & set(e.get("tags", [])):
        continue
    for k in [e["name"], *e.get("altnames", [])]:
        LOOKUP.setdefault(norm(k), e["name"])
ALIASES = {"torch": "pytorch", "pg": "postgresql", "psycopg2": "postgresql", "psycopg2binary": "postgresql",
           "mysql2": "mysql", "mysqlconnector": "mysql", "playwrighttest": "playwright", "next": "nextjs",
           "tensorflowcpu": "tensorflow", "npgsql": "postgresql", "pomeloentityframeworkcoremysql": "mysql",
           "mysqldata": "mysql", "sqlalchemy": "sqlalchemy", "socketio": "socketio"}

def match(token):
    n = norm(token)
    for cand in (ALIASES.get(n, n), n.removesuffix("js"), n.removesuffix("python"), n.removeprefix("python"), n.removesuffix("binary")):
        if cand in LOOKUP:
            return LOOKUP[cand]
        if cand in CATALOG and cand in ALIASES.values():
            return cand
    return None

# The catalogue has a few tools twice under different names, count them as one
CANON = {"vite": "vitejs"}

# Tools without their own devicon (shown with the .NET logo), keyed like catalogue names
SPECIAL = {"xunit": ("xUnit", "Testing"), "nunit": ("NUnit", "Testing"), "mstest": ("MSTest", "Testing"),
           "efcore": ("EF Core", "Data & AI")}
NUGET_SPECIAL = {"xunit": "xunit", "nunit": "nunit", "mstest.testframework": "mstest", "microsoft.entityframeworkcore": "efcore"}
# Display names for every tool in the catalogue, so a newly detected tool is spelled right at once.
# A tool the catalogue adds later falls back to its catalogue name; add it to tool-names.json then.
with open(os.path.join(ROOT, "scripts", "tool-names.json")) as f:
    PRETTY = json.load(f)
GROUP_FIX = {"vitejs": "Frameworks", "eslint": "DevOps", "githubactions": "DevOps", "jupyter": "Data & AI",
             "pandas": "Data & AI", "numpy": "Data & AI", "supabase": "Data & AI", "prisma": "Data & AI",
             "typeorm": "Data & AI", "sqlalchemy": "Data & AI", "nodemon": "DevOps", "unity": "Frameworks",
             "opencv": "Data & AI", "swagger": "DevOps", "nginx": "DevOps"}
DATA_TAGS = {"database", "sql", "nosql", "machine-learning", "data", "ai", "data-science", "orm"}
DEVOPS_TAGS = {"container", "deploy", "deployment", "cloud", "hosting", "ci", "cd", "devops", "kubernetes",
               "server", "monitoring", "security", "platform", "build", "package", "manager", "tool", "auth"}

def info(key):
    """(display name, group, logo folder, logo variant) for a detected tool."""
    if key in SPECIAL:
        name, group = SPECIAL[key]
        return name, group, "dot-net", "original"
    e = CATALOG[key]
    tags = set(e.get("tags", []))
    group = GROUP_FIX.get(key) or ("Testing" if "testing" in tags else "Data & AI" if tags & DATA_TAGS
                                   else "DevOps" if tags & DEVOPS_TAGS else "Frameworks")
    svgs = e["versions"]["svg"]
    variant = "original" if "original" in svgs else "plain" if "plain" in svgs else svgs[0]
    return PRETTY.get(key, key.capitalize()), group, key, variant

PATH_RULES = [  # (test on a lower-case path, catalogue name)
    (lambda p: p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")), "githubactions"),
    (lambda p: p.rsplit("/", 1)[-1] in ("dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"), "docker"),
    (lambda p: "/jest.config." in "/" + p, "jest"), (lambda p: "/vitest.config." in "/" + p, "vitest"),
    (lambda p: "/playwright.config." in "/" + p, "playwright"), (lambda p: "/cypress.config." in "/" + p, "cypressio"),
    (lambda p: p.endswith(("pytest.ini", "conftest.py")), "pytest"),
    (lambda p: "/.eslintrc" in "/" + p or "/eslint.config." in "/" + p, "eslint"),
    (lambda p: p.endswith(".csproj"), "dotnetcore"), (lambda p: p.endswith(".ipynb"), "jupyter"),
    (lambda p: p.endswith("projectsettings/projectversion.txt"), "unity"),
    (lambda p: "/vite.config." in "/" + p, "vitejs"), (lambda p: "/tailwind.config." in "/" + p, "tailwindcss"),
    (lambda p: p.endswith("nest-cli.json"), "nestjs"), (lambda p: "/next.config." in "/" + p, "nextjs"),
    (lambda p: p.startswith("supabase/") or "/supabase/migrations/" in p, "supabase"),
    (lambda p: p.endswith("schema.prisma"), "prisma"), (lambda p: p.endswith("chart.yaml"), "helm"),
    (lambda p: p.endswith(".tf"), "terraform"), (lambda p: p.startswith(("k8s/", "kubernetes/")) or "/k8s/" in p, "kubernetes"),
    (lambda p: p.endswith(".gitlab-ci.yml"), "gitlab"), (lambda p: p.endswith("jenkinsfile"), "jenkins"),
    (lambda p: p.endswith("firebase.json"), "firebase"), (lambda p: p.endswith("vercel.json"), "vercel"),
    (lambda p: p.endswith("netlify.toml"), "netlify"), (lambda p: p.endswith("azure-pipelines.yml"), "azuredevops"),
    (lambda p: p.endswith("nginx.conf") or "/nginx/" in "/" + p, "nginx"),
]
PATH_RULES = [(t, k) for t, k in PATH_RULES if k in CATALOG]

def rest(path, raw=False):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": f"bearer {TOKEN}",
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace") if raw else json.load(r)

def npm_tokens(dep):
    if dep.startswith("@types/"):
        return []
    if dep.startswith("@") and "/" in dep:
        scope, pkg = dep[1:].split("/", 1)
        return [scope, pkg]
    return [dep]

TEST_FILE = re.compile(r"(\.(test|spec)\.[cm]?[jt]sx?$)|(^|/)test_[^/]+\.py$|(^|/)[^/]+_test\.py$|tests?\.cs$|(^|/)cypress/e2e/")
REPOS = {}  # (owner, name) -> (paths, {manifest path: text}), read once and reused for the project cards

def read_repo(owner, name, branch):
    try:
        tree = rest(f"/repos/{owner}/{name}/git/trees/{urllib.parse.quote(branch)}?recursive=1")["tree"]
    except (urllib.error.HTTPError, KeyError):
        return None
    paths = [e["path"] for e in tree if e["type"] == "blob" and "node_modules/" not in e["path"]]
    manifests = [p for p in paths if p.rsplit("/", 1)[-1].lower() in ("package.json", "requirements.txt", "pyproject.toml") or p.lower().endswith(".csproj")]
    texts = {}
    for p in manifests[:50]:
        try:
            texts[p] = rest(f"/repos/{owner}/{name}/contents/{urllib.parse.quote(p)}?ref={urllib.parse.quote(branch)}", raw=True)
        except urllib.error.HTTPError:
            pass
    return paths, texts

def detect(paths, texts):
    """Catalogue names of the tools that these files show."""
    hits = set()
    for p in paths:
        lp = p.lower()
        hits |= {k for test, k in PATH_RULES if test(lp)}
    for p, text in texts.items():
        low = p.lower()
        tokens = []
        if low.endswith("package.json"):
            try:
                pkg = json.loads(text)
            except ValueError:
                continue
            for dep in {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}:
                tokens += npm_tokens(dep)
        elif low.endswith((".txt", ".toml")):
            for l in text.splitlines():
                l = l.strip().strip('",')
                if l and not l.startswith(("#", "[")) and "=" not in l.split(">")[0].split("<")[0][:1]:
                    tokens.append(re.split(r"[=<>~!\[;\s]", l, 1)[0])
        else:
            for pid in re.findall(r'include="([^"]+)"', text, re.I):
                pl = pid.lower()
                hits |= {k for prefix, k in NUGET_SPECIAL.items() if pl.startswith(prefix)}
                first = pl.split(".")[0]
                if first not in ("microsoft", "system"):
                    tokens.append(first)
        hits |= {m for m in map(match, tokens) if m}
    return {CANON.get(h, h) for h in hits}

found = {}
test_files = 0
for owner, name, branch in repo_refs:
    data = read_repo(owner, name, branch)
    if not data:
        continue
    REPOS[(owner, name)] = data
    paths, texts = data
    test_files += sum(1 for p in paths if TEST_FILE.search(p.lower()))
    for h in detect(paths, texts):
        found[h] = found.get(h, 0) + 1

GROUPS = ["Testing", "DevOps", "Frameworks", "Data & AI"]
INFO = {k: info(k) for k in found}
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

def in_group(g):
    return sorted([k for k in found if INFO[k][1] == g], key=lambda k: (-found[k], INFO[k][0].lower()))

def tools_card(t):
    rows = [(g, in_group(g)[:5]) for g in GROUPS]
    rows = [(g, items) for g, items in rows if items]
    W, rh = 1000, 64
    H = 70 + len(rows) * rh + 14
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">TOOLING &amp; TESTING</text>',
         f'<text x="{W-32}" y="44" class="m" font-size="11" fill="{t["mute"]}" text-anchor="end">used in my repositories</text>']
    for r, (g, items) in enumerate(rows):
        y = 70 + r * rh
        if r:
            o.append(f'<line x1="32" y1="{y}" x2="{W-32}" y2="{y}" stroke="{t["line"]}"/>')
        o.append(f'<text x="32" y="{y+31}" class="s" font-size="13" fill="{t["sub"]}">{g.replace("&", "&amp;")}</text>')
        if g == "Testing" and test_files:
            o.append(f'<text x="32" y="{y+48}" class="m" font-size="10.5" fill="{SKY}">{test_files:,} test files</text>')
        for k, key in enumerate(items):
            label, _, folder, variant = INFO[key]
            x = 176 + k * 158
            lg = tool_logo(folder, variant)
            o.append(f'<rect x="{x-4}" y="{y+14}" width="34" height="34" rx="8" fill="{t["tile"]}" stroke="{t["line"]}"/>')
            o.append(f'<image href="{lg}" x="{x+2}" y="{y+20}" width="22" height="22"/>' if lg
                     else f'<circle cx="{x+13}" cy="{y+31}" r="6" fill="{SKY}"/>')
            o.append(f'<text x="{x+36}" y="{y+29}" class="i" font-size="13.5" fill="{t["fg"]}">{label}</text>'
                     f'<text x="{x+36}" y="{y+46}" class="m" font-size="10.5" fill="{t["mute"]}">{found[key]} repo{"s" if found[key] != 1 else ""}</text>')
    o.append('</svg>')
    return "\n".join(o)

# ---------- stack: a bento per category, filled automatically ----------
# Languages by share, then every tool found in at least two repositories, grouped like the
# tooling card, plus a few things that never show up in code. The most used item of each
# group gets a wide tile; a thin bar shows how much it is used; one tile at a time lights
# up in the colour of its own logo.
STACK_MIN_REPOS = 2
STACK_EXTRA = [("Git", "git", "original", "DevOps"), ("GitHub", "github", "original", "DevOps"),
               ("Supabase", "supabase", "original", "Data & AI"), ("Azure", "azure", "original", "DevOps"),
               ("VS Code", "vscode", "original", "Tools"), ("Windows", "windows11", "original", "Tools"),
               ("macOS", "apple", "original", "Tools")]
STACK_GROUPS = ["Languages", "Frameworks", "Data & AI", "Testing", "DevOps", "Tools"]

def brand(folder, fallback=SKY):
    e = CATALOG.get(folder)
    c = (e or {}).get("color") or fallback
    return c if c.startswith("#") and len(c) in (4, 7) else fallback

def stack_items():
    """{group: [(label, logo, metric text, usage 0..1, brand colour)]}"""
    groups = {g: [] for g in STACK_GROUPS}
    seen = set()
    top_share = max([f for n, f, c in parts if n != "Other"] + [1e-9])
    for n, f, c in parts:
        if n != "Other" and logos.get(n):
            groups["Languages"].append((n, logos[n], f"{f * 100:.0f}%", f / top_share, c))
            seen.add(n)
    tools = sorted([k for k in found if found[k] >= STACK_MIN_REPOS], key=lambda k: (-found[k], INFO[k][0].lower()))
    most = max([found[k] for k in tools] + [1])
    for k in tools:
        label, group, folder, variant = INFO[k]
        lg = tool_logo(folder, variant)
        if lg and label not in seen:
            groups[group].append((label, lg, f"{found[k]} repos", found[k] / most, brand(folder)))
            seen.add(label)
    for label, folder, variant, group in STACK_EXTRA:
        lg = tool_logo(folder, variant)
        if lg and label not in seen:
            groups[group].append((label, lg, "", 0, brand(folder)))
            seen.add(label)
    return {g: items for g, items in groups.items() if items}

def stack_card(t, groups):
    """One grid of equal tiles, as before: tiles pop in one by one, then one tile at a time
    lifts and glows in the colour of its own logo."""
    items = [it for g in STACK_GROUPS for it in groups.get(g, [])]
    per_row, cell, TILE = 12, 78, 52
    rows = (len(items) + per_row - 1) // per_row
    W, H = 1000, rows * 88 + 14
    x0 = (W - per_row * cell) / 2 + (cell - TILE) / 2
    loop = len(items) * 1.2
    intro_end = 0.3 + len(items) * 0.035 + 0.5
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         '<defs><filter id="gl" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="6"/></filter></defs>']
    esc = lambda s: s.replace("&", "&amp;")
    for i, (label, lg, metric, use, col) in enumerate(items):
        r, c = divmod(i, per_row)
        x, y = x0 + c * cell, 8 + r * 88
        cx, cy = x + TILE / 2, y + TILE / 2
        a0, b0, e = i / len(items), (i + 1) / len(items), 0.3 / loop
        vis = (f'keyTimes="0;{a0:.5f};{a0 + e:.5f};{b0 - e:.5f};{b0:.5f};1"' if i else
               f'keyTimes="0;{e:.5f};{b0 - e:.5f};{b0:.5f};{1 - e:.5f};1"')
        on, off = ("0;0;1;1;0;0", "0;0;-4;-4;0;0") if i else ("0;1;1;0;0;0", "0;-4;-4;0;0;0")
        pop = 0.3 + i * 0.035
        o.append(f'<g transform="translate({cx:.1f} {cy:.1f})"><g transform="scale(0)">'
                 f'<animateTransform attributeName="transform" type="scale" values="0;1.12;1" keyTimes="0;0.65;1" begin="{pop:.3f}s" dur="0.45s" fill="freeze"/>'
                 f'<g transform="translate({-cx:.1f} {-cy:.1f})">'
                 # the lift and glow while this tile is in the spotlight
                 f'<g><animateTransform attributeName="transform" type="translate" values="{";".join("0 " + v for v in off.split(";"))}" {vis} '
                 f'begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/>'
                 f'<rect x="{x - 2}" y="{y - 2}" width="{TILE + 4}" height="{TILE + 4}" rx="14" fill="{col}" opacity="0" filter="url(#gl)">'
                 f'<animate attributeName="opacity" values="{on.replace("1", "0.55")}" {vis} begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/></rect>'
                 f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="{t["tile"]}" stroke="{t["line"]}"/>'
                 f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="none" stroke="{col}" stroke-width="1.6" opacity="0">'
                 f'<animate attributeName="opacity" values="{on}" {vis} begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/></rect>'
                 f'<image href="{lg}" x="{x + 11}" y="{y + 11}" width="30" height="30"/></g>'
                 f'<text x="{cx:.1f}" y="{y + 70}" text-anchor="middle" class="m" font-size="10" fill="{t["sub"]}">{esc(label)}</text>'
                 '</g></g></g>')
    o.append('</svg>')
    return "\n".join(o)

STACK = stack_items()

# ---------- project cards: everything a project uses, as logos ----------
EXT_LANG = {".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
            ".py": "Python", ".cs": "C#", ".java": "Java", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
            ".go": "Go", ".rs": "Rust", ".php": "PHP", ".kt": "Kotlin", ".swift": "Swift", ".dart": "Dart", ".vue": "Vue"}
_lang_logo = {}
def lang_logo(n):
    if n not in _lang_logo:
        _lang_logo[n] = logo(n)
    return _lang_logo[n]

def project_logos(project):
    langs, hits = set(), set()
    for src in project["sources"]:
        if "org" in src:
            keys = [k for k in REPOS if k[0] == src["org"]]
            prefixes = None
        else:
            keys = [tuple(src["repo"].split("/", 1))]
            prefixes = tuple(src["paths"])
        for key in keys:
            if key not in REPOS:
                continue
            paths, texts = REPOS[key]
            if prefixes:
                paths = [p for p in paths if p.startswith(prefixes)]
                texts = {p: t for p, t in texts.items() if p.startswith(prefixes)}
            hits |= detect(paths, texts)
            for p in paths:
                ext = os.path.splitext(p)[1].lower()
                if ext in EXT_LANG and "/public/" not in "/" + p:
                    langs.add(EXT_LANG[ext])
    out = []
    for n in sorted(langs, key=lambda n: [x for x, _, _ in parts].index(n) if n in [x for x, _, _ in parts] else 99):
        if lang_logo(n):
            out.append((n, lang_logo(n)))
    order = {g: i for i, g in enumerate(["Frameworks", "Data & AI", "Testing", "DevOps"])}
    for k in sorted(hits, key=lambda k: (order[info(k)[1]], -found.get(k, 0), info(k)[0].lower())):
        label, _, folder, variant = info(k)
        lg = tool_logo(folder, variant)
        if lg:
            out.append((label, lg))
    return out

def project_card(t, pr, items, rows):
    W = 320
    H = 244 + rows * 30 + 14
    ic = base64.b64encode(open(os.path.join(ROOT, pr["icon"]), "rb").read()).decode()
    esc = lambda x: x.replace("&", "&amp;").replace("<", "&lt;")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         '<defs><clipPath id="ir"><rect x="24" y="58" width="48" height="48" rx="11"/></clipPath>'
         f'<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
         '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         '<clipPath id="tb"><rect x="24" y="0.5" width="48" height="3" rx="1.5"/></clipPath></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         '<rect x="24" y="0.5" width="48" height="3" rx="1.5" fill="url(#ac)"/>'
         '<rect x="24" y="0.5" width="18" height="3" fill="url(#shine)" opacity="0.8" clip-path="url(#tb)">'
         '<animate attributeName="x" values="12;72;12" dur="5s" repeatCount="indefinite"/></rect>',
         f'<text x="24" y="34" class="m" font-size="10" fill="{SKY}" letter-spacing="1.6">{pr["num"]} // PROJECT</text>']
    st = pr["status"]
    scol = "#22c55e" if st == "LIVE" else "#f59e0b"
    sw = len(st) * 6.4 + 26
    o.append(f'<g transform="translate({W-24-sw:.0f},20)"><rect width="{sw:.0f}" height="20" rx="10" fill="{scol}" fill-opacity="0.1" stroke="{scol}" stroke-opacity="0.4"/>'
             f'<circle cx="11" cy="10" r="3.2" fill="{scol}"/><text x="20" y="13.8" class="m" font-size="9.5" fill="{scol}" letter-spacing="0.7">{esc(st)}</text></g>')
    if pr.get("icon_tile"):
        o.append(f'<rect x="24" y="58" width="48" height="48" rx="11" fill="{pr["icon_tile"]}" stroke="{t["line"]}"/>'
                 f'<image href="data:image/png;base64,{ic}" xlink:href="data:image/png;base64,{ic}" x="30" y="64" width="36" height="36"/>')
    else:
        o.append(f'<image href="data:image/png;base64,{ic}" xlink:href="data:image/png;base64,{ic}" x="24" y="58" width="48" height="48" clip-path="url(#ir)"/>')
    o.append(f'<text x="86" y="79" class="s" font-size="18" fill="{t["fg"]}">{esc(pr["name"])}</text>'
             f'<text x="86" y="98" class="i" font-size="12" fill="{t["sub"]}">{esc(pr["tagline"])}</text>')
    y = 140
    for ln in pr["points"]:
        o.append(f'<rect x="24" y="{y-7}" width="5" height="5" rx="1" fill="url(#ac)"/><text x="37" y="{y}" class="i" font-size="12.5" fill="{t["sub"]}">{esc(ln)}</text>')
        y += 24
    o.append(f'<line x1="24" y1="208" x2="{W-24}" y2="208" stroke="{t["line"]}"/>'
             f'<text x="24" y="233" class="m" font-size="9.5" fill="{t["mute"]}" letter-spacing="1.6">BUILT WITH</text>')
    for i, (label, lg) in enumerate(items):
        r, c = divmod(i, 9)
        x, yy = 24 + c * 30.5, 244 + r * 30
        o.append(f'<rect x="{x:.1f}" y="{yy}" width="26" height="26" rx="6" fill="{t["tile"]}" stroke="{t["line"]}"/>'
                 f'<image href="{lg}" x="{x+4:.1f}" y="{yy+4}" width="18" height="18"/>')
    o.append('</svg>')
    return "\n".join(o)

with open(os.path.join(ROOT, "scripts", "projects.json")) as f:
    PROJECTS = json.load(f)
for i, pr in enumerate(PROJECTS, 1):
    pr["num"] = f"{i:02d}"
    pr["items"] = project_logos(pr)
CARD_ROWS = max((len(pr["items"]) + 8) // 9 for pr in PROJECTS)
for name, t in THEMES.items():
    with open(os.path.join(ROOT, "assets", f"stats-{name}.svg"), "w") as f:
        f.write(card(t))
    with open(os.path.join(ROOT, "assets", f"tools-{name}.svg"), "w") as f:
        f.write(tools_card(t))
    with open(os.path.join(ROOT, "assets", f"stack-{name}.svg"), "w") as f:
        f.write(stack_card(t, STACK))
    for pr in PROJECTS:
        with open(os.path.join(ROOT, "assets", f"card-{pr['slug']}-{name}.svg"), "w") as f:
            f.write(project_card(t, pr, pr["items"], CARD_ROWS))
# Details page behind the cards: full lists, since an image in a README cannot show tooltips.
import datetime
md = ["# Languages and tooling", "",
      f"Updated {datetime.date.today():%d %B %Y}. Counted over my own repositories and {', '.join(EXTRA_ORGS)}, forks excluded.", "",
      "## Languages", "", "| Language | Share |", "| --- | --- |"]
md += [f"| {n} | {s / total * 100:.1f}% |" for n, s in ranked]
md += ["", f"Not counted: {', '.join(sorted(IGNORED))}.", "", "## Tooling and testing", "",
       f"{test_files:,} test files found.", ""]
for g in GROUPS:
    items = in_group(g)
    if items:
        md += [f"### {g}", "", "| Tool | Repositories |", "| --- | --- |"] + [f"| {INFO[k][0]} | {found[k]} |" for k in items] + [""]
md += ["[Back to profile](./README.md)", ""]
with open(os.path.join(ROOT, "STATS.md"), "w") as f:
    f.write("\n".join(md))
for pr in PROJECTS:
    print(f"{pr['name']}:", ", ".join(l for l, _ in pr["items"]))
print("stack:", "; ".join(f"{g}: {len(v)}" for g, v in STACK.items()))
print("test files:", test_files)
for g in GROUPS:
    print(f"{g}:", ", ".join(f"{INFO[k][0]} {found[k]}" for k in in_group(g)))
print("languages:", ", ".join(f"{n} {f*100:.1f}%" for n, f, _ in parts))
