import base64, datetime, zoneinfo, json, math, os, re, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS_OF = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).date() - datetime.timedelta(days=1)
AS_OF_TEXT = f"as of {AS_OF:%d/%m/%Y} 23:59"
_ams = zoneinfo.ZoneInfo("Europe/Amsterdam")
RANGE_TO = datetime.datetime.combine(AS_OF, datetime.time(23, 59, 59), _ams).isoformat()
RANGE_FROM = datetime.datetime.combine(AS_OF - datetime.timedelta(days=364), datetime.time(0, 0), _ams).isoformat()
TOKEN = os.environ["GH_TOKEN"]
IGNORED = {"Jupyter Notebook", "ShaderLab", "HLSL", "Dockerfile", "Procfile", "Batchfile", "PowerShell", "Shell"}
TOP = 6
EXTRA_ORGS = ["Alpha-Stock"]
DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{0}/{0}-{1}.svg"
LOGOS = {
    "TypeScript": ("typescript", "original"), "JavaScript": ("javascript", "original"),
    "Python": ("python", "original"), "C#": ("csharp", "original"), "Java": ("java", "original"),
    "HTML": ("html5", "original"), "CSS": ("css3", "original"), "SCSS": ("sass", "original"),
    "PHP": ("php", "original"), "Go": ("go", "original-wordmark"), "Rust": ("rust", "original"),
    "C++": ("cplusplus", "original"), "C": ("c", "original"), "Kotlin": ("kotlin", "original"),
    "Swift": ("swift", "original"), "Dart": ("dart", "original"), "Vue": ("vuejs", "original"),
    "TSQL": ("microsoftsqlserver", "plain"), "PLpgSQL": ("postgresql", "original"),
    "Pug": ("pug", "original"), "Shell": ("bash", "original"), "PowerShell": ("powershell", "original"),
}

def logo(name):
    if name not in LOGOS:
        return None
    try:
        with urllib.request.urlopen(DEVICON.format(*LOGOS[name]), timeout=10) as r:
            return "data:image/svg+xml;base64," + base64.b64encode(r.read()).decode()
    except OSError:
        return None

QUERY = """
query($after: String, $from: DateTime, $to: DateTime) {
  viewer {
    login
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name owner { login } defaultBranchRef { name } languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
    contributionsCollection(from: $from, to: $to) {
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
        data=json.dumps({"query": query, "variables": {"after": after, **({"from": RANGE_FROM, "to": RANGE_TO} if query is QUERY else {}), **extra}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["viewer"] if query is QUERY else body["data"]["organization"]

langs, colors, repo_count, repo_refs, ignored_seen = {}, {}, 0, [], {}

def take(repos):
    global repo_count, ignored_seen
    repo_count += len(repos["nodes"])
    for n in repos["nodes"]:
        if n["defaultBranchRef"]:
            repo_refs.append((n["owner"]["login"], n["name"], n["defaultBranchRef"]["name"]))
        for e in n["languages"]["edges"]:
            name = e["node"]["name"]
            if name in IGNORED:
                ignored_seen[name] = ignored_seen.get(name, 0) + e["size"]
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
named = [kv for kv in ranked if kv[1] / total >= 0.01][:7]
top = named
rest = sum(s for n, s in ranked if (n, s) not in named)
parts = [(n, s / total, colors[n]) for n, s in top]
if rest / total >= 0.0005:
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
    "dark": dict(panel="#0b0b12", line="#1e293b", fg="#f8fafc", sub="#94a3b8", mute="#64748b", track="#0f172a", tile="#f1f5f9", btile="#111827", plate="#e2e8f0", wave="0.45"),
    "light": dict(panel="#ffffff", line="#e2e8f0", fg="#0f172a", sub="#475569", mute="#64748b", track="#f1f5f9", tile="#f8fafc", btile="#f8fafc", plate=None, wave="0.85"),
}
SKY, VIO = "#0ea5e9", "#8b5cf6"
DONUT = ["#0ea5e9", "#38bdf8", "#7dd3fc", "#6366f1", "#8b5cf6", "#c4b5fd", "#94a3b8"]

def card(t):
    W, H = 1000, 250
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LANGUAGES</text>']
    cx, cy, r, sw = 112, 146, 64, 22
    circ = 2 * math.pi * r
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["track"]}" stroke-width="{sw}"/>')
    shown = [(i, n, f) for i, (n, f, c) in enumerate(parts) if n != "Other"]
    slot, fade, centre_start = 2.5, 0.4, 1.4
    loop = max(1, len(shown)) * slot
    def turn(k, lo, hi):
        a0, b0, e = k / len(shown), (k + 1) / len(shown), fade / loop
        if len(shown) == 1:
            return f'values="{hi};{hi}" keyTimes="0;1"'
        if k == 0:
            return f'values="{hi};{hi};{lo};{lo};{hi}" keyTimes="0;{b0 - e:.5f};{b0:.5f};{1 - e:.5f};1"'
        return f'values="{lo};{lo};{hi};{hi};{lo};{lo}" keyTimes="0;{a0:.5f};{a0 + e:.5f};{b0 - e:.5f};{b0:.5f};1"'
    turn_of = {i: k for k, (i, n, f) in enumerate(shown)}
    start = 0.0
    for i, (n, f, c) in enumerate(parts):
        seg = max(circ * f - 2, 0.6)
        col = DONUT[i] if n != "Other" else "#94a3b8"
        swell = (f'<animate attributeName="stroke-width" {turn(turn_of[i], sw, sw + 7)} begin="{centre_start}s" '
                 f'dur="{loop}s" repeatCount="indefinite"/>' if i in turn_of else '')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" '
                 f'stroke-dasharray="{seg:.2f} {circ:.2f}" stroke-dashoffset="{-start:.2f}" transform="rotate(-90 {cx} {cy})">'
                 f'<animate attributeName="stroke-dasharray" values="0 {circ:.2f};0 {circ:.2f};{seg:.2f} {circ:.2f}" '
                 f'keyTimes="0;{min(0.85, 0.12*i):.2f};1" dur="{0.7+0.12*i:.2f}s"/>{swell}</circle>')
        start += circ * f
    for k, (i, n, f) in enumerate(shown):
        lg = logos.get(n)
        o.append(f'<g opacity="0"><animate attributeName="opacity" {turn(k, 0, 1)} begin="{centre_start}s" dur="{loop}s" repeatCount="indefinite"/>'
                 + (f'<image href="{lg}" x="{cx - 12}" y="{cy - 30}" width="24" height="24"/>' if lg else '')
                 + f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" class="s" font-size="12" fill="{t["fg"]}">{n}</text>'
                 f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" class="m" font-size="11" fill="{t["sub"]}">{f * 100:.1f}%</text></g>')
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
    o.append(f'<text x="672" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LAST 12 MONTHS</text>'
             f'<text x="{W - 32}" y="44" class="m" font-size="10.5" fill="{t["mute"]}" text-anchor="end">{AS_OF_TEXT}</text>')
    for i, (num, label) in enumerate(numbers):
        col, row = i % 2, i // 2
        nx, ny = 672 + col * 160, 104 + row * 82
        o.append(f'<text x="{nx}" y="{ny}" class="s" font-size="30" fill="{t["fg"]}">{num}</text>'
                 f'<text x="{nx}" y="{ny+22}" class="i" font-size="12.5" fill="{t["sub"]}">{label}</text>')
    o.append('</svg>')
    return "\n".join(o)

with urllib.request.urlopen("https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/devicon.json", timeout=30) as r:
    CATALOG = {e["name"]: e for e in json.load(r)}
SKIP_TAGS = {"language", "editor", "ide", "os", "browser"}
SKIP = {"npm", "yarn", "pnpm", "git", "github", "json", "markdown", "yaml", "babel", "html5", "css3", "bash"}

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

CANON = {"vite": "vitejs"}

SPECIAL = {"xunit": ("xUnit", "Testing"), "nunit": ("NUnit", "Testing"), "mstest": ("MSTest", "Testing"),
           "efcore": ("EF Core", "Data & AI"), "siege": ("Siege", "Testing"), "k6load": ("k6", "Testing"),
           "jmeter": ("JMeter", "Testing"), "locust": ("Locust", "Testing")}
TEXT_LOGO = {"siege": "#b91c1c", "jmeter": "#d22128", "locust": "#2d6a4f"}
NUGET_SPECIAL = {"xunit": "xunit", "nunit": "nunit", "mstest.testframework": "mstest", "microsoft.entityframeworkcore": "efcore"}
with open(os.path.join(ROOT, "scripts", "tool-names.json")) as f:
    PRETTY = json.load(f)
GROUP_FIX = {"nodejs": "Frameworks", "vitejs": "Frameworks", "eslint": "DevOps", "githubactions": "DevOps", "jupyter": "Data & AI",
             "pandas": "Data & AI", "numpy": "Data & AI", "supabase": "Data & AI", "prisma": "Data & AI",
             "typeorm": "Data & AI", "sqlalchemy": "Data & AI", "nodemon": "DevOps", "unity": "Frameworks",
             "opencv": "Data & AI", "swagger": "DevOps", "nginx": "DevOps"}
DATA_TAGS = {"database", "sql", "nosql", "machine-learning", "data", "ai", "data-science", "orm"}
DEVOPS_TAGS = {"container", "deploy", "deployment", "cloud", "hosting", "ci", "cd", "devops", "kubernetes",
               "server", "monitoring", "security", "platform", "build", "package", "manager", "tool", "auth"}

def info(key):
    if key in SPECIAL:
        name, group = SPECIAL[key]
        if key in TEXT_LOGO:
            return name, group, "text:" + name, TEXT_LOGO[key]
        if key == "k6load":
            return name, group, "k6", "original"
        return name, group, "dot-net", "original"
    e = CATALOG[key]
    tags = set(e.get("tags", []))
    group = GROUP_FIX.get(key) or ("Testing" if "testing" in tags else "Data & AI" if tags & DATA_TAGS
                                   else "DevOps" if tags & DEVOPS_TAGS else "Frameworks")
    svgs = e["versions"]["svg"]
    variant = "original" if "original" in svgs else "plain" if "plain" in svgs else svgs[0]
    return PRETTY.get(key, key.capitalize()), group, key, variant

PATH_RULES = [
    (lambda p: p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")), "githubactions"),
    (lambda p: p.rsplit("/", 1)[-1] == "package.json", "nodejs"),
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
PATH_RULES += [  # load testing, found by name since these have no manifest
    (lambda p: any(part.startswith("siege") for part in p.split("/")) or p.endswith(".siegerc"), "siege"),
    (lambda p: p.endswith(".jmx"), "jmeter"),
    (lambda p: p.endswith("locustfile.py"), "locust"),
    (lambda p: "/k6/" in "/" + p or p.rsplit("/", 1)[-1].startswith("k6"), "k6load"),
]
PATH_RULES = [(t, k) for t, k in PATH_RULES if k in CATALOG or k in SPECIAL]

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
REPOS = {}

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

extra_path = os.path.join(ROOT, "scripts", "extra-repos.json")
EXTRA_REPOS = json.load(open(extra_path)) if os.path.exists(extra_path) else []
for extra in EXTRA_REPOS:
    for h in extra["tools"]:
        if h in CATALOG or h in SPECIAL:
            found[h] = found.get(h, 0) + 1
    test_files += extra.get("test_files", 0)

GROUPS = ["Testing", "DevOps", "Frameworks", "Data & AI"]
INFO = {k: info(k) for k in found}
tool_logo_cache = {}
def tool_logo(folder, variant):
    key = (folder, variant)
    if folder.startswith("text:"):
        return text_logo(folder[5:], variant)
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
    rows = [(g, items) for g, items in rows if items] + [("Tools", [("daily", d) for d in DAILY_TOOLS])]
    W, rh = 1000, 64
    H = 70 + len(rows) * rh + 14
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         f'<rect x="32" y="0.5" width="48" height="2" fill="url(#ac)"/>',
         f'<text x="32" y="44" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">TOOLING &amp; TESTING USED IN MY REPOSITORIES</text>',
         f'<text x="{W-32}" y="44" class="m" font-size="10.5" fill="{t["mute"]}" text-anchor="end">{AS_OF_TEXT}</text>']
    for r, (g, items) in enumerate(rows):
        y = 70 + r * rh
        if r:
            o.append(f'<line x1="32" y1="{y}" x2="{W-32}" y2="{y}" stroke="{t["line"]}"/>')
        o.append(f'<text x="32" y="{y+31}" class="s" font-size="13" fill="{t["sub"]}">{g.replace("&", "&amp;")}</text>')
        if g == "Testing" and test_files:
            o.append(f'<text x="32" y="{y+48}" class="m" font-size="10.5" fill="{SKY}">{test_files:,} test files</text>')
        for k, key in enumerate(items):
            if isinstance(key, tuple):
                label, folder, variant = key[1]
                sub = "used daily"
            else:
                label, _, folder, variant = INFO[key]
                sub = f'{found[key]} repo{"s" if found[key] != 1 else ""}'
            x = 176 + k * 158
            lg = tool_logo(folder, variant)
            o.append(f'<rect x="{x-4}" y="{y+14}" width="34" height="34" rx="8" fill="{t["tile"]}" stroke="{t["line"]}"/>')
            o.append(f'<image href="{lg}" x="{x+2}" y="{y+20}" width="22" height="22"/>' if lg
                     else f'<circle cx="{x+13}" cy="{y+31}" r="6" fill="{SKY}"/>')
            o.append(f'<text x="{x+36}" y="{y+29}" class="i" font-size="13.5" fill="{t["fg"]}">{label}</text>'
                     f'<text x="{x+36}" y="{y+46}" class="m" font-size="10.5" fill="{t["mute"]}">{sub}</text>')
    o.append('</svg>')
    return "\n".join(o)

STACK_MIN_REPOS = 2
STACK_EXTRA = [("Supabase", "supabase", "original", "Data & AI"), ("Azure", "azure", "original", "DevOps")]
DAILY_TOOLS = [("Git", "git", "original"), ("GitHub", "github", "original"), ("VS Code", "vscode", "original"),
               ("Windows", "windows11", "original"), ("macOS", "apple", "original")]
STACK_GROUPS = ["Languages", "Frameworks", "Data & AI", "Testing", "DevOps", "Tools"]
STACK_SKIP = {"nodemon", "postcss", "babel", "eslint", "githubactions", "swagger", "jupyter", "prettier"}

def brand(folder, fallback=SKY):
    e = CATALOG.get(folder)
    c = (e or {}).get("color") or fallback
    return c if c.startswith("#") and len(c) in (4, 7) else fallback

def text_logo(name, color):
    short = name if len(name) <= 4 else name[:3]
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='{color}'/>"
           f"<text x='16' y='21' text-anchor='middle' font-family='Arial,Helvetica,sans-serif' font-weight='700' "
           f"font-size='{12 if len(short) > 3 else 13}' fill='#ffffff'>{short}</text></svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

def stack_items():
    groups = {g: [] for g in STACK_GROUPS}
    seen = set()
    top_share = max([f for n, f, c in parts if n != "Other"] + [1e-9])
    for n, size in ranked:
        f = size / total
        if f < 0.01:
            continue
        lg = logos.get(n) or logo(n) or text_logo(n, colors.get(n) or "#64748b")
        if lg:
            groups["Languages"].append((n, lg, f"{f * 100:.0f}%", f / top_share, colors.get(n, SKY)))
            seen.add(n)
    for n in ("Shell", "PowerShell"):
        if ignored_seen.get(n, 0) > 0 and logo(n):
            groups["Languages"].append((n, logo(n), "scripts", 0, "#4eaa25" if n == "Shell" else "#5391fe"))
            seen.add(n)
    tools = sorted([k for k in found if found[k] >= (1 if INFO[k][1] == "Testing" else STACK_MIN_REPOS)],
                   key=lambda k: (-found[k], INFO[k][0].lower()))
    most = max([found[k] for k in tools] + [1])
    for k in tools:
        if k in STACK_SKIP:
            continue
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
    items = [it for g in STACK_GROUPS for it in groups.get(g, [])]
    per_row, cell, TILE = 12, 78, 52
    rows = (len(items) + per_row - 1) // per_row
    W, H = 1000, rows * 88 + 14
    x0 = (W - per_row * cell) / 2 + (cell - TILE) / 2
    intro_end = 0.3 + len(items) * 0.035 + 0.5
    flippers = []
    SLOT, TURN, HOLD = 2.6, 0.22, 1.6
    loop = max(1, len(flippers)) * SLOT
    WAVE, wave_peak = 6.0, t.get("wave", "0.5")
    diag_max = (per_row - 1) + (rows - 1) * 2
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
         '<linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="-60" y1="0" x2="0" y2="0">'
         '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.9"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
         '<animateTransform attributeName="gradientTransform" type="translate" values="0 0;0 0;320 0;320 0" keyTimes="0;0.02;0.3;1" begin="1s" dur="6s" repeatCount="indefinite"/></linearGradient>'
         '<linearGradient id="glare" x1="0" y1="0" x2="1" y2="1"><stop offset="0.25" stop-color="#ffffff" stop-opacity="0"/>'
         '<stop offset="0.5" stop-color="#ffffff" stop-opacity="1"/><stop offset="0.75" stop-color="#ffffff" stop-opacity="0"/></linearGradient></defs>']
    esc = lambda s: s.replace("&", "&amp;")
    kt = lambda sec: f"{sec / loop:.5f}"
    for i, (label, lg, metric, use, col) in enumerate(items):
        r, c = divmod(i, per_row)
        x, y = x0 + c * cell, 8 + r * 88
        cx, cy = x + TILE / 2, y + TILE / 2
        pop = 0.3 + i * 0.035
        front = (f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="{t["tile"]}" stroke="{t["line"]}"/>'
                 f'<image href="{lg}" x="{x + 11}" y="{y + 11}" width="30" height="30"/>')
        flip = back = ""
        if i in flippers:
            s0 = flippers.index(i) * SLOT + 0.3
            times = [0, s0, s0 + TURN, s0 + 2 * TURN, s0 + 2 * TURN + HOLD, s0 + 3 * TURN + HOLD, s0 + 4 * TURN + HOLD, loop]
            keys = ";".join(kt(v) for v in times)
            flip = (f'<animateTransform attributeName="transform" type="scale" values="1 1;1 1;0 1;1 1;1 1;0 1;1 1;1 1" '
                    f'keyTimes="{keys}" begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/>')
            swap_in, swap_out = kt(s0 + TURN), kt(s0 + 3 * TURN + HOLD)
            show_front = f'<animate attributeName="opacity" calcMode="discrete" values="1;0;1" keyTimes="0;{swap_in};{swap_out}" begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/>'
            show_back = f'<animate attributeName="opacity" calcMode="discrete" values="0;1;0" keyTimes="0;{swap_in};{swap_out}" begin="{intro_end:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/>'
            num, unit = (metric.split(" ", 1) + [""])[:2] if " " in metric else (metric, "")
            back = (f'<g opacity="0">{show_back}'
                    f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="{col}" fill-opacity="0.16" stroke="{col}" stroke-width="1.6"/>'
                    f'<text x="{cx:.1f}" y="{y + (27 if unit else 32)}" text-anchor="middle" class="s" font-size="17" fill="{t["fg"]}">{esc(num)}</text>'
                    + (f'<text x="{cx:.1f}" y="{y + 41}" text-anchor="middle" class="m" font-size="9" fill="{t["sub"]}">{esc(unit)}</text>' if unit else "")
                    + '</g>')
            front = f'<g>{show_front}{front}</g>'
        wa = (c + r * 2) / max(1, diag_max) * 0.7
        glare = (f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="url(#glare)" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;{wave_peak};0;0" keyTimes="0;{wa:.3f};{wa + 0.06:.3f};{wa + 0.14:.3f};1" '
                 f'begin="{intro_end:.2f}s" dur="{WAVE}s" repeatCount="indefinite"/></rect>')
        o.append(f'<g transform="translate({cx:.1f} {cy:.1f})"><g transform="scale(0)">'
                 f'<animateTransform attributeName="transform" type="scale" values="0;1.12;1" keyTimes="0;0.65;1" begin="{pop:.3f}s" dur="0.45s" fill="freeze"/>'
                 f'<g>{flip}<g transform="translate({-cx:.1f} {-cy:.1f})">{front}{back}{glare}</g></g>'
                 f'<text x="0" y="{y + 70 - cy:.1f}" text-anchor="middle" class="m" font-size="10" fill="{t["sub"]}">{esc(label)}</text>'
                 '</g></g>')
    o.append('</svg>')
    return "\n".join(o)

STACK = stack_items()

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

def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


PER_ROW = 7


def card_layout(pr):
    tag = wrap(pr["tagline"], 25)
    points = [wrap(p, 31) for p in pr["points"]]
    return tag, points


def project_card(t, pr, items, rows, head_h):
    W = 240
    tag, points = card_layout(pr)
    top = head_h
    H = top + 40 + rows * 28 + 12
    ic = base64.b64encode(open(os.path.join(ROOT, pr["icon"]), "rb").read()).decode()
    esc = lambda x: x.replace("&", "&amp;").replace("<", "&lt;")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         '<defs><clipPath id="ir"><rect x="20" y="52" width="44" height="44" rx="10"/></clipPath>'
         f'<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
         '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         '<clipPath id="tb"><rect x="20" y="0.5" width="44" height="3" rx="1.5"/></clipPath>'
         '<linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="-60" y1="0" x2="0" y2="0">'
         '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.9"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
         '<animateTransform attributeName="gradientTransform" type="translate" values="0 0;0 0;240 0;240 0" keyTimes="0;0.02;0.3;1" begin="1s" dur="6s" repeatCount="indefinite"/></linearGradient>'
         '<linearGradient id="glare" x1="0" y1="0" x2="1" y2="1"><stop offset="0.25" stop-color="#ffffff" stop-opacity="0"/>'
         '<stop offset="0.5" stop-color="#ffffff" stop-opacity="1"/><stop offset="0.75" stop-color="#ffffff" stop-opacity="0"/></linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>',
         '<rect x="20" y="0.5" width="44" height="3" rx="1.5" fill="url(#ac)"/>'
         '<rect x="10" y="0.5" width="16" height="3" fill="url(#shine)" opacity="0.8" clip-path="url(#tb)">'
         '<animate attributeName="x" values="10;64;64" keyTimes="0;0.5;1" dur="5s" repeatCount="indefinite"/></rect>',
         f'<text x="20" y="31" class="m" font-size="9.5" fill="{SKY}" letter-spacing="1.4">{pr["num"]} // PROJECT</text>']
    st = pr["status"]
    scol = "#22c55e" if st == "LIVE" else "#f59e0b"
    sw = len(st) * 6 + 24
    o.append(f'<g transform="translate({W-20-sw:.0f},17)"><rect width="{sw:.0f}" height="19" rx="9.5" fill="{scol}" fill-opacity="0.1" stroke="{scol}" stroke-opacity="0.4"/>'
             f'<circle cx="10" cy="9.5" r="3" fill="{scol}"/><text x="18" y="13.2" class="m" font-size="9" fill="{scol}" letter-spacing="0.6">{esc(st)}</text></g>')
    if pr.get("icon_tile"):
        o.append(f'<rect x="20" y="52" width="44" height="44" rx="10" fill="{pr["icon_tile"]}" stroke="{t["line"]}"/>'
                 f'<image href="data:image/png;base64,{ic}" xlink:href="data:image/png;base64,{ic}" x="25" y="57" width="34" height="34"/>')
    else:
        o.append(f'<image href="data:image/png;base64,{ic}" xlink:href="data:image/png;base64,{ic}" x="20" y="52" width="44" height="44" clip-path="url(#ir)"/>')
    o.append(f'<rect x="20" y="52" width="44" height="44" rx="10" fill="url(#glare)" opacity="0">'
             f'<animate attributeName="opacity" values="0;0;{t["wave"]};0;0" keyTimes="0;0.02;0.08;0.16;1" begin="1s" dur="6s" repeatCount="indefinite"/></rect>')
    o.append(f'<text x="76" y="71" class="s" font-size="16" fill="{t["fg"]}">{esc(pr["name"])}</text>'
             f'<text x="76" y="71" class="s" font-size="16" fill="url(#sweep)">{esc(pr["name"])}</text>')
    for k, line in enumerate(tag):
        o.append(f'<text x="76" y="{88 + k * 14}" class="i" font-size="11" fill="{t["sub"]}">{esc(line)}</text>')
    y = 128
    for lines in points:
        o.append(f'<rect x="20" y="{y-7}" width="4.5" height="4.5" rx="1" fill="url(#ac)"/>')
        for k, line in enumerate(lines):
            o.append(f'<text x="32" y="{y + k * 15}" class="i" font-size="11.5" fill="{t["sub"]}">{esc(line)}</text>')
        y += 15 * len(lines) + 7
    o.append(f'<line x1="20" y1="{top}" x2="{W-20}" y2="{top}" stroke="{t["line"]}"/>'
             f'<text x="20" y="{top + 24}" class="m" font-size="9" fill="{t["mute"]}" letter-spacing="1.4">BUILT WITH</text>')
    for i, (label, lg) in enumerate(items):
        r, c = divmod(i, PER_ROW)
        x, yy = 20 + c * 29, top + 34 + r * 28
        wa = 0.45 + (c + r * 2) / 12 * 0.4
        o.append(f'<rect x="{x:.1f}" y="{yy}" width="25" height="25" rx="6" fill="{t["tile"]}" stroke="{t["line"]}"/>'
                 f'<image href="{lg}" x="{x+4:.1f}" y="{yy+4}" width="17" height="17"/>'
                 f'<rect x="{x:.1f}" y="{yy}" width="25" height="25" rx="6" fill="url(#glare)" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;{t["wave"]};0;0" keyTimes="0;{wa:.3f};{wa + 0.06:.3f};{wa + 0.14:.3f};1" '
                 f'begin="1s" dur="6s" repeatCount="indefinite"/></rect>')
    o.append('</svg>')
    return "\n".join(o)


with open(os.path.join(ROOT, "scripts", "projects.json")) as f:
    PROJECTS = json.load(f)
for i, pr in enumerate(PROJECTS, 1):
    pr["num"] = f"{i:02d}"
    pr["items"] = project_logos(pr)
CARD_ROWS = max((len(pr["items"]) + PER_ROW - 1) // PER_ROW for pr in PROJECTS)
CARD_HEAD = max(128 + sum(15 * len(l) + 7 for l in card_layout(pr)[1]) + 2 for pr in PROJECTS)
for name, t in THEMES.items():
    with open(os.path.join(ROOT, "assets", f"stats-{name}.svg"), "w") as f:
        f.write(card(t))
    with open(os.path.join(ROOT, "assets", f"tools-{name}.svg"), "w") as f:
        f.write(tools_card(t))
    with open(os.path.join(ROOT, "assets", f"stack-{name}.svg"), "w") as f:
        f.write(stack_card(t, STACK))
    for pr in PROJECTS:
        with open(os.path.join(ROOT, "assets", f"card-{pr['slug']}-{name}.svg"), "w") as f:
            f.write(project_card(t, pr, pr["items"], CARD_ROWS, CARD_HEAD))
import datetime
md = ["# Languages and tooling", "",
      f"Updated {datetime.date.today():%d %B %Y}. Counted over my own repositories, {', '.join(EXTRA_ORGS)}"
      + (f" and {', '.join(e['name'] for e in EXTRA_REPOS)} (tools only)" if EXTRA_REPOS else "") + ", forks excluded.", "",
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
