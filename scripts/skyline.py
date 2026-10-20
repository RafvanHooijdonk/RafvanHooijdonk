"""Own isometric contribution skyline, replacing the 3D contrib action.

Writes assets/skyline-light.svg and assets/skyline-dark.svg. Bars rise week by week, the
busiest days spring a little, the busiest day gets a flag, the longest streak draws itself
as a line over the bars, and a stat block counts up. Plain SMIL, plays inside an <img>.
"""
import base64, datetime, json, math, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("GH_TOKEN", "")
TEST_DENSITY = os.environ.get("SKYLINE_TEST_DENSITY")
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
THEMES = {
    "light": dict(levels=["#e2e8f0", "#bae6fd", "#38bdf8", "#0ea5e9", "#8b5cf6"], fg="#0f172a", sub="#475569",
                  mute="#64748b", panel="#ffffff", line="#e2e8f0", flag="#0f172a", flag_text="#ffffff", wave="0.55"),
    "dark": dict(levels=["#1e293b", "#0c4a6e", "#0369a1", "#0ea5e9", "#8b5cf6"], fg="#f8fafc", sub="#94a3b8",
                 mute="#64748b", panel="#0b0b12", line="#1e293b", flag="#f8fafc", flag_text="#020204", wave="0.3"),
}
SKY, VIO = "#0ea5e9", "#8b5cf6"
STREAK_COL, TOP_COL = "#22c55e", "#f59e0b"   # longest streak and busiest day, also in the stat block

# ---------------- data ----------------
QUERY = """{ viewer { contributionsCollection { totalCommitContributions restrictedContributionsCount
  totalPullRequestContributions totalPullRequestReviewContributions totalIssueContributions
  contributionCalendar { totalContributions weeks { contributionDays { contributionCount contributionLevel weekday date } } } } } }"""
if TEST_DENSITY is None:
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY}).encode(),
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cc = json.load(r)["data"]["viewer"]["contributionsCollection"]
else:
    import random
    random.seed(1)
    first = datetime.date(2025, 10, 19)
    days = []
    for w in range(53):
        week = []
        for d in range(7):
            n = random.randint(1, 40) if random.random() < float(TEST_DENSITY) else 0
            lv = 0 if not n else min(4, 1 + n // 10)
            week.append({"contributionCount": n, "contributionLevel": list(LEVEL)[lv], "weekday": d,
                         "date": str(first + datetime.timedelta(days=7 * w + d))})
        days.append({"contributionDays": week})
    cc = {"totalCommitContributions": 0, "restrictedContributionsCount": 0, "totalPullRequestContributions": 0,
          "totalPullRequestReviewContributions": 0, "totalIssueContributions": 0,
          "contributionCalendar": {"totalContributions": sum(d["contributionCount"] for w in days for d in w["contributionDays"]),
                                   "weeks": days}}
weeks = cc["contributionCalendar"]["weeks"]
TOTAL = cc["contributionCalendar"]["totalContributions"]
cells = []  # (week, weekday, count, level, date)
for x, w in enumerate(weeks):
    for d in w["contributionDays"]:
        cells.append((x, d["weekday"], d["contributionCount"], LEVEL[d["contributionLevel"]], d["date"]))
MAXC = max([c[2] for c in cells] + [1])
STATS = [("contributions", TOTAL),
         ("commits incl. private", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
         ("pull requests", cc["totalPullRequestContributions"]),
         ("reviews", cc["totalPullRequestReviewContributions"])]

# longest streak of consecutive days with contributions
ordered = sorted(cells, key=lambda c: c[4])
best, cur = [], []
for c in ordered:
    if c[2] > 0:
        cur.append(c)
        if len(cur) > len(best):
            best = list(cur)
    else:
        cur = []
STREAK = best
TOP = max(cells, key=lambda c: c[2]) if cells and MAXC > 0 else None
STATS += [("longest streak in days", len(STREAK)), ("most in one day", TOP[2] if TOP else 0)]

# ---------------- geometry ----------------
WX, WY = 14.0, 6.2      # one week to the right and down
DX, DY = -10.0, 5.0     # one weekday to the left and down
OX, OY = 130.0, 175.0   # top corner of the first week
MAXH = 120.0

def proj(x, y, h=0.0):
    return OX + x * WX + y * DX, OY + x * WY + y * DY - h

def height(n):
    return 0.0 if n == 0 else 4 + (MAXH - 4) * math.sqrt(n / MAXC)

def shade(hexc, f):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(v * f):02x}" for v in (r, g, b))

def pts(*ps):
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in ps)

def b64(p):
    return base64.b64encode(open(os.path.join(ROOT, p), "rb").read()).decode()

FONTS = ("<style>" + "".join(
    f"@font-face{{font-family:'{n}';src:url(data:font/woff2;base64,{b64('assets/fonts/' + f)}) format('woff2');}}"
    for n, f in [("In", "Inter-400.woff2"), ("InS", "Inter-600.woff2"), ("Mono", "JBM-500.woff2")])
    + ".i{font-family:'In',Helvetica,Arial,sans-serif}.s{font-family:'InS',Helvetica,Arial,sans-serif;font-weight:600}"
    + ".m{font-family:'Mono',Menlo,Consolas,monospace}</style>")

def outline(c):
    """Silhouette of a bar on screen: top face plus the two visible sides."""
    x, y, n = c[0], c[1], c[2]
    h = height(n)
    return [proj(x, y, h), proj(x + 1, y, h), proj(x + 1, y), proj(x + 1, y + 1), proj(x, y + 1), proj(x, y + 1, h)]

def inside_poly(pt, poly):
    px, py = pt
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit

def in_view(c):
    """Is the top of this bar, and the flag pole above it, free of bars standing in front?"""
    fx, fy = proj(c[0] + 0.5, c[1] + 0.5, height(c[2]))
    probes = [(fx, fy), (fx - 4, fy + 2), (fx + 4, fy + 2), (fx, fy - 15), (fx, fy - 30)]
    for d in cells:
        if d[2] > 0 and (d[0] + d[1], d[0]) > (c[0] + c[1], c[0]):
            poly = outline(d)
            if any(inside_poly(p, poly) for p in probes):
                return False
    return True

def svg(th):
    W, H = 1000, 575
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS,
         f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
         f'<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
         f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    # bars, back to front so nearer ones cover the ones behind
    streak_days = {c[4] for c in STREAK} if len(STREAK) >= 2 else set()
    end_bars = 0.25 + len(weeks) * 0.035 + 0.7
    for x, y, n, lv, date in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):
        h = height(n)
        top = th["levels"][lv]
        side = top
        if TOP and date == TOP[4]:
            top = TOP_COL
        elif date in streak_days:
            top = STREAK_COL
        p0, p1, p2, p3 = proj(x, y), proj(x + 1, y), proj(x + 1, y + 1), proj(x, y + 1)
        if h == 0:
            o.append(f'<polygon points="{pts(p0, p1, p2, p3)}" fill="{top}" stroke="{th["panel"]}" stroke-width="0.6"/>')
            continue
        t0, t1, t2, t3 = (proj(a, b, h) for a, b in ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)))
        ox, oy = p2  # grow from the front corner of the base
        delay = 0.25 + x * 0.035
        grow = (f'<animateTransform attributeName="transform" type="scale" values="1 0;1 1.14;1 1" keyTimes="0;0.7;1" '
                if lv == 4 else '<animateTransform attributeName="transform" type="scale" values="1 0;1 1" keyTimes="0;1" ')
        grow += (f'calcMode="spline" keySplines="{"0.2 0.7 0.3 1;0.4 0 0.6 1" if lv == 4 else "0.2 0.7 0.3 1"}" '
                 f'begin="{delay:.3f}s" dur="0.7s" fill="freeze"/>')
        o.append(f'<g transform="translate({ox:.1f} {oy:.1f})"><g transform="scale(1 0)">{grow}'
                 f'<g transform="translate({-ox:.1f} {-oy:.1f})">'
                 f'<polygon points="{pts(p3, p2, t2, t3)}" fill="{shade(side, 0.78)}"/>'
                 f'<polygon points="{pts(p1, p2, t2, t1)}" fill="{shade(side, 0.9)}"/>'
                 f'<polygon points="{pts(t0, t1, t2, t3)}" fill="{top}"/>'
                 # light wave: every few seconds a soft highlight glides over all tops, left to right
                 + (lambda a: f'<polygon points="{pts(t0, t1, t2, t3)}" fill="#ffffff" opacity="0">'
                    f'<animate attributeName="opacity" values="0;0;{th["wave"]};0;0" keyTimes="0;{a:.3f};{a + 0.04:.3f};{a + 0.1:.3f};1" '
                    f'begin="{end_bars:.2f}s" dur="6s" repeatCount="indefinite"/></polygon>')(x / len(weeks) * 0.85)
                 + '</g></g></g>')
    # month labels along the front edge
    last = -10
    for x, w in enumerate(weeks):
        d0 = datetime.date.fromisoformat(w["contributionDays"][0]["date"])
        prev = datetime.date.fromisoformat(weeks[x - 1]["contributionDays"][0]["date"]).month if x else None
        if (x == 0 or d0.month != prev) and x - last >= 3:
            lx, ly = proj(x + 0.2, 9.0)
            o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="m" font-size="11" fill="{th["mute"]}">{d0.strftime("%b")}</text>')
            last = x
    # flag: jumps between the days, every day with contributions gets it once per round.
    # The pole grows where bars in front would hide the label, so every label stays readable.
    # random order, every day still once per round; reshuffled with each daily build
    tops = [c for c in sorted(cells, key=lambda c: c[4]) if c[2] > 0]
    import random
    random.Random(datetime.date.today().toordinal()).shuffle(tops)
    if tops:
        k, slot, fade = len(tops), 1.5, 0.4   # seconds per day, seconds to fade in and out
        loop = k * slot
        start = end_bars + 0.4
        stat_box = (620, 0, 1000, 265)
        front = lambda c: [outline(d) for d in cells if d[2] > 0 and (d[0] + d[1], d[0]) > (c[0] + c[1], c[0])]
        for i, c in enumerate(tops):
            fx, fy = proj(c[0] + 0.5, c[1] + 0.5, height(c[2]))
            label = f'{c[2]} on {datetime.date.fromisoformat(c[4]).strftime("%-d %b")}'
            bw = len(label) * 7.2 + 18
            polys = front(c)
            pole = 30
            while pole < 240:
                for side in (0, 1):
                    bx = fx if side == 0 else fx - bw
                    by = fy - pole - 20
                    corners = [(bx, by), (bx + bw, by), (bx, by + 21), (bx + bw, by + 21), (bx + bw / 2, by + 10)]
                    in_stats = bx + bw > stat_box[0] and by < stat_box[3]
                    if bx < 5 or bx + bw > 995 or by < 4 or in_stats:
                        continue
                    if not any(inside_poly(p, poly) for p in corners for poly in polys):
                        break
                else:
                    pole += 10
                    continue
                break
            by = max(4, fy - pole - 20)
            a0, b0, e = i / k, (i + 1) / k, fade / loop
            if k == 1:
                vis = 'values="1;1" keyTimes="0;1"'
            elif i == 0:
                vis = f'values="1;1;0;0;1" keyTimes="0;{b0 - e:.5f};{b0:.5f};{1 - e:.5f};1"'
            else:
                vis = f'values="0;0;1;1;0;0" keyTimes="0;{a0:.5f};{a0 + e:.5f};{b0 - e:.5f};{b0:.5f};1"'
            o.append(f'<g opacity="0"><animate attributeName="opacity" {vis} begin="{start:.2f}s" dur="{loop:.2f}s" repeatCount="indefinite"/>'
                     f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="9" fill="{SKY}" opacity="0.35">'
                     f'<animate attributeName="r" values="4;11;4" dur="1s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="0.45;0;0.45" dur="1s" repeatCount="indefinite"/></circle>'
                     f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{fx:.1f}" y2="{by + 21:.1f}" stroke="{th["flag"]}" stroke-width="1.4"/>'
                     f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="2.6" fill="{th["flag"]}"/>'
                     f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="21" rx="5" fill="{th["flag"]}"/>'
                     f'<text x="{bx + 9:.1f}" y="{by + 14.5:.1f}" class="m" font-size="11.5" fill="{th["flag_text"]}">{label}</text></g>')
    # stat block, top right, numbers counting up
    px, py = 640, 40
    o.append(f'<text x="{px}" y="{py}" class="m" font-size="11" fill="{SKY}" letter-spacing="1.8">LAST 12 MONTHS</text>')
    for i, (label, value) in enumerate(STATS):
        cx, cy = px + (i % 2) * 165, py + 46 + (i // 2) * 70
        steps = 14
        for k in range(steps + 1):
            v = round(value * (1 - (1 - k / steps) ** 3))
            start = 0.4 + k * 0.08
            last_frame = k == steps
            anims = (f'<set attributeName="opacity" to="1" begin="{start:.2f}s"/>' if k else '')
            if not last_frame:
                anims += f'<set attributeName="opacity" to="0" begin="{start + 0.08:.2f}s"/>'
            col = STREAK_COL if label.startswith("longest streak") else TOP_COL if label == "most in one day" else th["fg"]
            o.append(f'<text x="{cx}" y="{cy}" class="s" font-size="30" fill="{col}" opacity="{1 if k == 0 else 0}">{v:,}{anims}</text>')
        o.append(f'<text x="{cx}" y="{cy + 21}" class="i" font-size="12.5" fill="{th["sub"]}">{label}</text>')
    # legend, bottom left
    lx, ly = 40, 500
    o.append(f'<text x="{lx}" y="{ly}" class="i" font-size="13" fill="{th["fg"]}">Contributions per day</text>')
    o.append(f'<text x="{lx}" y="{ly + 26}" class="m" font-size="11" fill="{th["mute"]}">Less</text>')
    for k in range(5):
        o.append(f'<rect x="{lx + 38 + k * 20}" y="{ly + 14}" width="15" height="15" rx="4" fill="{th["levels"][k]}"/>')
    o.append(f'<text x="{lx + 38 + 5 * 20 + 4}" y="{ly + 26}" class="m" font-size="11" fill="{th["mute"]}">More</text>')
    o.append(f'<rect x="{lx}" y="{ly + 38}" width="15" height="15" rx="4" fill="{STREAK_COL}"/>'
             f'<text x="{lx + 22}" y="{ly + 50}" class="m" font-size="11" fill="{th["mute"]}">Longest streak</text>'
             f'<rect x="{lx + 140}" y="{ly + 38}" width="15" height="15" rx="4" fill="{TOP_COL}"/>'
             f'<text x="{lx + 162}" y="{ly + 50}" class="m" font-size="11" fill="{th["mute"]}">Most in one day</text>')
    o.append('</svg>')
    return "\n".join(o)

for name, th in THEMES.items():
    out = svg(th)
    assert out.endswith("</svg>")
    if TEST_DENSITY is None:
        with open(os.path.join(ROOT, "assets", f"skyline-{name}.svg"), "w") as f:
            f.write(out)
print(f"skyline: {len(cells)} days, max {MAXC}, streak {len(STREAK)}, flagged days: {sum(1 for c in cells if c[2] > 0)}")
