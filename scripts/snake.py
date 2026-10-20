"""Own contribution snake: eats every day with contributions and grows with each bite.

Writes dist/github-snake.svg and dist/github-snake-dark.svg for the output branch.
Plain SMIL animation, so it plays inside an <img> on GitHub.

- The route never crosses the body: each step knows where the body will still be.
- Head with eyes and a flicking tongue, bites shrink the day, the busiest days spark.
- Eats the lightest days first and the violet ones last. Month and weekday labels, a live counter, and at the end the snake coils up and
  shows the year's total before the round starts over.
"""
import base64, datetime, json, os, sys, urllib.request
from collections import deque

TOKEN = os.environ.get("GH_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELL, DOT, RADIUS = 16, 12, 4
START_LEN = 1  # starts as just the head, grows one segment with every day eaten, no cap
STEP = 0.07            # seconds per grid step
HOLD = 2.6             # seconds the coiled snake and the total stay on screen
FADE = 0.6             # seconds to fade out before the round restarts
THEMES = {
    "github-snake.svg": dict(dots=["#e2e8f0", "#bae6fd", "#38bdf8", "#0ea5e9", "#8b5cf6"], border="#0f172a14",
                             head="#16a34a", tail="#86efac", bar="#e2e8f0", bar_done="#38bdf8",
                             label="#64748b", text="#0f172a", accent="#0ea5e9", pupil="#0f172a"),
    "github-snake-dark.svg": dict(dots=["#1e293b", "#0c4a6e", "#0369a1", "#0ea5e9", "#8b5cf6"], border="#ffffff14",
                                  head="#22c55e", tail="#14532d", bar="#1e293b", bar_done="#0ea5e9",
                                  label="#94a3b8", text="#f8fafc", accent="#38bdf8", pupil="#020204"),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

# ---------------- data ----------------
# SNAKE_TEST_DENSITY=0.0..1.0 runs on a random year instead of real data (stress test, no files written)
TEST_DENSITY = os.environ.get("SNAKE_TEST_DENSITY")
QUERY = """{ viewer { contributionsCollection { contributionCalendar { totalContributions weeks {
  contributionDays { contributionLevel weekday date } } } } } }"""
if TEST_DENSITY is None:
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY}).encode(),
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]
else:
    import random
    random.seed(os.environ.get("SNAKE_TEST_SEED", "1"))
    first = datetime.date(2025, 10, 19)
    cal = {"totalContributions": 0, "weeks": [{"contributionDays": [
        {"contributionLevel": random.choice(list(LEVEL)[1:]) if random.random() < float(TEST_DENSITY) else "NONE",
         "weekday": d, "date": str(first + datetime.timedelta(days=7 * w + d))} for d in range(7)]} for w in range(53)]}
weeks, TOTAL = cal["weeks"], cal["totalContributions"]
grid = {}
for x, w in enumerate(weeks):
    for d in w["contributionDays"]:
        grid[(x, d["weekday"])] = LEVEL[d["contributionLevel"]]
W, H = len(weeks), 7

# ---------------- route ----------------
# The snake moves on the grid plus one lane around it, with one extra column on the right so a
# closed tour exists. A fixed Hamiltonian cycle visits every cell exactly once; following it the
# snake can never hit itself and always reaches every day. While that is safe it takes shortcuts
# ahead on the cycle, but never past its own tail (the well known safe-shortcut strategy), so it
# stays fast when short and stays correct even with every day of the year filled.
X0, X1, Y0, Y1 = -1, W + 1, -1, H          # columns X0..X1 (even count), rows Y0..Y1

def inside(c):
    return X0 <= c[0] <= X1 and Y0 <= c[1] <= Y1

def neighbours(c):
    x, y = c
    return [n for n in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)) if inside(n)]

def build_cycle():
    cols, rows = X1 - X0 + 1, Y1 - Y0 + 1
    assert cols % 2 == 0
    order = [(0, r) for r in range(rows)]                       # first column down
    for c in range(1, cols):                                    # snake through rows 1..end
        rng = range(rows - 1, 0, -1) if c % 2 else range(1, rows)
        order += [(c, r) for r in rng]
    order += [(c, 0) for c in range(cols - 1, 0, -1)]           # back along the top row
    return [(X0 + c, Y0 + r) for c, r in order]

CYCLE = build_cycle()
AREA = len(CYCLE)
IDX = {c: i for i, c in enumerate(CYCLE)}
assert len(IDX) == AREA == (X1 - X0 + 1) * (Y1 - Y0 + 1)
for i, c in enumerate(CYCLE):  # every step of the cycle is one grid step
    n = CYCLE[(i + 1) % AREA]
    assert abs(c[0] - n[0]) + abs(c[1] - n[1]) == 1

def ahead(a, b):
    return (IDX[b] - IDX[a]) % AREA

ALL_DAYS = {c for c, lv in grid.items() if lv > 0}
MAX_LEN = START_LEN + len(ALL_DAYS)

def reset():
    global route, bites, eaten_at, targets, out_of_order
    route, bites, eaten_at, targets, out_of_order = [CYCLE[0]], [], {}, set(ALL_DAYS), 0

def length_at(t):
    return min(MAX_LEN, START_LEN + sum(1 for b in bites if b <= t))

def body(t, k_from=0):
    return [route[max(0, t - i)] for i in range(k_from, length_at(t))]

def blocked(t, c, d):
    """Is cell c still under the body when the head gets there d steps after time t?"""
    L = length_at(t) + 1
    for k in range(0, L):
        if route[max(0, t - k)] == c and d < L - k:
            return True
    return False

def step_to(c):
    """Move the head one cell; a day is eaten the moment the head reaches it."""
    global out_of_order
    route.append(c)
    if c in targets:
        if grid[c] != min(grid[x] for x in targets):
            out_of_order += 1
        targets.discard(c)
        eaten_at[c] = len(route) - 1
        bites.append(len(route) - 1)

def verify():
    """The two hard rules: never on an uneaten day, never two segments in one cell."""
    for f, c in enumerate(route):
        if c in eaten_at and eaten_at[c] > f:
            return False
    for f in range(len(route)):
        visible = [route[f - i] for i in range(length_at(f)) if f - i >= 0]
        if len(set(visible)) != len(visible):
            return False
    return not targets

# --- planner 1: free routes around every uneaten day, safe as long as the tail stays reachable ---
def paths_to(goals, limit=12):
    t, start = len(route) - 1, route[-1]
    prev, q, found = {start: None}, deque([(start, 0)]), []
    while q and len(found) < limit:
        c, d = q.popleft()
        for n in neighbours(c):
            if n in prev or blocked(t, n, d + 1):
                continue
            if n in targets and n not in goals:   # never through a day that is not eaten yet
                continue
            prev[n] = c
            if n in goals:                        # a day is the end of a path, never a passage
                path, x = [], n
                while x != start:
                    path.append(x)
                    x = prev[x]
                found.append(path[::-1])
                continue
            q.append((n, d + 1))
    return found

def tail_path():
    t = len(route) - 1
    L = length_at(t)
    if L < 3:
        return []
    tail, start = route[max(0, t - (L - 1))], route[-1]
    prev, q = {start: None}, deque([(start, 0)])
    while q:
        c, d = q.popleft()
        for n in neighbours(c):
            if n in prev or n in targets:
                continue
            if n == tail:
                path, x = [n], c
                while x != start:
                    path.append(x)
                    x = prev[x]
                return path[::-1]
            if not blocked(t, n, d + 1):
                prev[n] = c
                q.append((n, d + 1))
    return None

def safe_after(path):
    n_route, n_bites, n_targets = len(route), len(bites), set(targets)
    for c in path:
        route.append(c)
        if c in targets:
            targets.discard(c)
            bites.append(len(route) - 1)
    ok = tail_path() is not None
    del route[n_route:]
    del bites[n_bites:]
    targets.clear()
    targets.update(n_targets)
    return ok

def plan_free():
    reset()
    waited = 0
    while targets:
        if len(route) > 20 * AREA:
            return False
        levels = sorted({grid[c] for c in targets})
        L = length_at(len(route) - 1)
        # first the lightest level; while the own body is in the way, follow the tail a while
        # so it moves off; only then eat a later day that blocks the way
        tries = levels[:1] if waited < 2 * L + 20 else levels
        path = None
        for lv in tries:
            path = next((p for p in paths_to({c for c in targets if grid[c] == lv}) if safe_after(p)), None)
            if path:
                break
        if path:
            waited = 0
            for c in path:
                step_to(c)
            continue
        chase = tail_path()
        if chase:
            waited += 1
            step_to(chase[0])
            continue
        if waited < 2 * L + 20:                   # cannot even follow the tail: allow later days now
            waited = 2 * L + 20
            continue
        return False
    return verify()

# --- planner 2: a Hamiltonian cycle with safe shortcuts, always finishes ---
def plan_cycle():
    reset()
    while targets:
        t = len(route) - 1
        head = route[-1]
        L = length_at(t)
        level = min(grid[c] for c in targets)
        goal = min((c for c in targets if grid[c] == level), key=lambda c: ahead(head, c))
        tail = route[max(0, t - (L - 1))]
        room = ahead(head, tail) if L > 1 else AREA
        cycle_next = CYCLE[(IDX[head] + 1) % AREA]
        safe_moves = []
        for n in neighbours(head):
            if blocked(t, n, 1):
                continue
            jump = ahead(head, n)
            if (n == cycle_next or (L < AREA // 2 and 0 < jump < room - 3)) and ahead(n, goal) < ahead(head, goal):
                safe_moves.append(n)
        clear = [n for n in safe_moves if not (n in targets and grid[n] != level)]
        if clear:
            nxt = min(clear, key=lambda n: ahead(n, goal))
        elif safe_moves:
            nxt = min(safe_moves, key=lambda n: (grid[n], ahead(n, goal)))
        else:
            nxt = cycle_next
        step_to(nxt)
        if len(route) > 50 * AREA:
            sys.exit("route did not finish")
    if not verify():
        sys.exit("cycle route broke a rule")

# run both, keep the free route when it finished and keeps the order at least as well
free_ok = plan_free()
free = (list(route), list(bites), dict(eaten_at), out_of_order) if free_ok else None
plan_cycle()
planner = "cycle"
if free and free[3] <= out_of_order:
    route, bites, eaten_at, out_of_order = free
    targets = set()
    planner = "free"
last_bite = bites[-1] if bites else 0

# coil up: keep turning towards the own body, so it winds into a tight spiral
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
def heading(a, b):
    return DIRS.index((b[0] - a[0], b[1] - a[1])) if a != b else 0
h = heading(route[-2], route[-1]) if len(route) > 1 else 0
for _ in range(40):
    t = len(route) - 1
    moved = False
    for turn in (1, 0, 3):  # right, straight, left
        nh = (h + turn) % 4
        n = (route[-1][0] + DIRS[nh][0], route[-1][1] + DIRS[nh][1])
        if inside(n) and not blocked(t, n, 1):
            route.append(n)
            h = nh
            moved = True
            break
    if not moved:
        break

# frames: one per route step, then the hold with time standing still
R = len(route)
STEP = min(STEP, 55 / R)
taus = list(range(R)) + [R - 1] * round((HOLD + FADE) / STEP)
N = len(taus)
DUR = round(N * STEP, 2)
def kt(frame):
    return f"{frame / (N - 1):.4f}"
fade_start, hold_start = N - 1 - round(FADE / STEP), R - 1

# safety check: the head only ever enters a day at the moment it eats it
for f, c in enumerate(route):
    if c in eaten_at and eaten_at[c] > f:
        sys.exit(f"crawled over an uneaten day at step {f}")
# safety check: no two segments in one cell at any frame
for f in range(R):
    visible = [route[f - i] for i in range(length_at(f)) if f - i >= 0]  # stacked start cells excluded
    if len(set(visible)) != len(visible):
        sys.exit(f"route crosses itself at step {f}")

# ---------------- drawing ----------------
FONT = base64.b64encode(open(os.path.join(ROOT, "assets", "fonts", "JBM-500.woff2"), "rb").read()).decode()
def mix(a, b, f):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))

def anim(attr, values, extra=""):
    return f'<animate attributeName="{attr}" values="{values}" dur="{DUR}s" repeatCount="indefinite"{extra}/>'

def svg(theme):
    th = THEMES[theme]
    left, top = 48, 64
    width, height = W * CELL + left + 44, H * CELL + top + 66
    o = [f'<svg viewBox="{-left} {-top} {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
         '<desc>Contribution snake, generated by scripts/snake.py</desc>',
         f"<style>@font-face{{font-family:'Mono';src:url(data:font/woff2;base64,{FONT}) format('woff2');}}"
         f".m{{font-family:'Mono',Menlo,Consolas,monospace;font-size:10px;fill:{th['label']}}}</style>"]
    # month labels (where a new month starts in a week) and weekday labels
    last_x = -10
    for x, w in enumerate(weeks):
        first = datetime.date.fromisoformat(w["contributionDays"][0]["date"])
        prev_month = datetime.date.fromisoformat(weeks[x - 1]["contributionDays"][0]["date"]).month if x else None
        if (x == 0 or first.month != prev_month) and x - last_x >= 3:
            o.append(f'<text x="{x * CELL + 2}" y="-24" class="m">{first.strftime("%b")}</text>')
            last_x = x
    for row, name in enumerate(("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
        o.append(f'<text x="-22" y="{row * CELL + 11}" class="m" text-anchor="end">{name}</text>')
    # days: an empty dot below, the coloured one on top shrinks away when eaten
    off = (CELL - DOT) / 2
    for (x, y), lv in sorted(grid.items()):
        px, py = x * CELL + off, y * CELL + off
        o.append(f'<rect x="{px}" y="{py}" width="{DOT}" height="{DOT}" rx="{RADIUS}" fill="{th["dots"][0]}" stroke="{th["border"]}"/>')
        if lv and (x, y) in eaten_at:
            te = eaten_at[(x, y)]
            cx, cy = px + DOT / 2, py + DOT / 2
            o.append(f'<g transform="translate({cx} {cy})"><rect x="{-DOT / 2}" y="{-DOT / 2}" width="{DOT}" height="{DOT}" rx="{RADIUS}" '
                     f'fill="{th["dots"][lv]}" stroke="{th["border"]}">'
                     f'<animateTransform attributeName="transform" type="scale" values="1;1;1.25;0;0" '
                     f'keyTimes="0;{kt(te - 1)};{kt(te)};{kt(te + 2)};1" dur="{DUR}s" repeatCount="indefinite"/></rect>')
            if lv == 4:  # sparks on the busiest days
                for dx, dy in ((9, -9), (-9, -9), (9, 9), (-9, 9)):
                    o.append(f'<circle r="1.6" fill="{th["dots"][4]}" opacity="0">'
                             f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{kt(te)};{kt(te + 1)};{kt(te + 4)};1" dur="{DUR}s" repeatCount="indefinite"/>'
                             f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx} {dy};{dx} {dy}" '
                             f'keyTimes="0;{kt(te)};{kt(te + 4)};1" dur="{DUR}s" repeatCount="indefinite"/></circle>')
            o.append('</g>')
    # progress bar, split per level (light to violet); each day colours its piece when eaten
    by = H * CELL + 26
    full = W * CELL
    o.append(f'<clipPath id="bar"><rect x="0" y="{by}" width="{full}" height="5" rx="2.5"/></clipPath>')
    o.append(f'<rect x="0" y="{by}" width="{full}" height="5" rx="2.5" fill="{th["bar"]}"/><g clip-path="url(#bar)">')
    piece = full / max(1, len(eaten_at))
    x0 = 0.0
    for lv in (1, 2, 3, 4):
        days = sorted((te for c, te in eaten_at.items() if grid[c] == lv))
        for te in days:
            o.append(f'<rect x="{x0:.2f}" y="{by}" width="{piece + 0.4:.2f}" height="5" fill="{th["dots"][lv]}" opacity="0">'
                     f'<animate attributeName="opacity" calcMode="discrete" values="0;1;1" keyTimes="0;{kt(te)};1" '
                     f'dur="{DUR}s" repeatCount="indefinite"/></rect>')
            x0 += piece
    o.append('</g>')
    # legend, as under the GitHub graph
    lx, ly = (W + 1) * CELL, H * CELL + 44
    o.append(f'<text x="{lx}" y="{ly + 10}" class="m" text-anchor="end">More</text>')
    for k in range(5):
        o.append(f'<rect x="{lx - 46 - (4 - k) * 15}" y="{ly}" width="12" height="12" rx="{RADIUS}" fill="{th["dots"][k]}" stroke="{th["border"]}"/>')
    o.append(f'<text x="{lx - 46 - 4 * 15 - 6}" y="{ly + 10}" class="m" text-anchor="end">Less</text>')
    # counter, one text per stage, shown while it is current
    total_days = len(bites)
    marks = [0] + bites + [N - 1]
    for k in range(total_days + 1):
        a, b = marks[k], marks[k + 1] if k < total_days else hold_start
        L = min(MAX_LEN, START_LEN + k)
        vis = f'values="0;1;0;0" keyTimes="0;{kt(a)};{kt(b)};1"' if a > 0 else f'values="1;0;0" keyTimes="0;{kt(b)};1"'
        o.append(f'<text x="{W * CELL}" y="-44" class="m" text-anchor="end" opacity="{1 if a == 0 else 0}">'
                 f'<tspan fill="{th["accent"]}">{k} / {total_days}</tspan> days eaten &#183; length {L}'
                 f'<animate attributeName="opacity" calcMode="discrete" {vis} dur="{DUR}s" repeatCount="indefinite"/></text>')
    # snake: tail first so the head is drawn on top
    o.append(f'<g>' + anim("opacity", "1;1;0;0", f' keyTimes="0;{kt(fade_start)};{kt(N - 2)};1"'))
    # positions in whole cells inside a scale(16) group keeps the file small
    o.append(f'<g transform="scale({CELL})">')
    for i in reversed(range(1, MAX_LEN)):
        size = max(6, 12 - i * 0.12)
        o2 = (CELL - size) / 2 / CELL
        xs = ";".join(str(route[max(0, tau - i)][0]) for tau in taus)
        ys = ";".join(str(route[max(0, tau - i)][1]) for tau in taus)
        appear = next((f for f in range(R) if length_at(f) > i), R - 1)
        vis = (f'<animate attributeName="opacity" calcMode="discrete" values="0;1;1" keyTimes="0;{kt(appear)};1" '
               f'dur="{DUR}s" repeatCount="indefinite"/>') if i >= START_LEN else ""
        sz = size / CELL
        o.append(f'<g transform="translate({o2:.3f} {o2:.3f})"><rect width="{sz:.3f}" height="{sz:.3f}" rx="{sz / 2.4:.3f}" '
                 f'fill="{mix(th["head"], th["tail"], i / MAX_LEN)}" opacity="{1 if i < START_LEN else 0}">'
                 + anim("x", xs) + anim("y", ys) + vis + '</rect></g>')
    o.append('</g>')
    # head: moves, turns with the direction, eyes and a flicking tongue
    centers = ";".join(f"{route[tau][0] * CELL + CELL / 2} {route[tau][1] * CELL + CELL / 2}" for tau in taus)
    angles = []
    for tau in taus:
        a, b = route[max(0, tau - 1)], route[tau]
        angles.append(str(heading(a, b) * 90) if a != b else (angles[-1] if angles else "0"))
    o.append(f'<g><animateTransform attributeName="transform" type="translate" values="{centers}" dur="{DUR}s" repeatCount="indefinite"/>'
             f'<animateTransform attributeName="transform" type="rotate" values="{";".join(angles)}" calcMode="discrete" additive="sum" dur="{DUR}s" repeatCount="indefinite"/>'
             f'<path d="M6 0H10.5M10.5 0l2.2-1.8M10.5 0l2.2 1.8" stroke="#ef4444" stroke-width="1.3" stroke-linecap="round" fill="none" opacity="0">'
             f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.55;0.6;0.78;1" dur="1.6s" repeatCount="indefinite"/></path>'
             f'<rect x="-6.5" y="-6.5" width="13" height="13" rx="5" fill="{th["head"]}"/>'
             f'<circle cx="2" cy="-3" r="2" fill="#ffffff"/><circle cx="2" cy="3" r="2" fill="#ffffff"/>'
             f'<circle cx="2.7" cy="-3" r="1" fill="{th["pupil"]}"/><circle cx="2.7" cy="3" r="1" fill="{th["pupil"]}"/></g>')
    o.append('</g>')
    # the year's total, shown while the snake lies coiled up
    o.append(f'<text x="{W * CELL / 2}" y="{H * CELL / 2 + 6}" text-anchor="middle" '
             f'style="font-family:\'Mono\',Menlo,monospace;font-size:20px;font-weight:700" fill="{th["text"]}" opacity="0">'
             f'<tspan fill="{th["accent"]}">{TOTAL:,}</tspan> contributions in the last year'
             + anim("opacity", "0;0;1;1;0;0", f' keyTimes="0;{kt(hold_start)};{kt(hold_start + 4)};{kt(fade_start)};{kt(N - 2)};1"')
             + '</text>')
    o.append('</svg>')
    return "".join(o)

if targets:
    sys.exit(f"{len(targets)} days left uneaten")
if TEST_DENSITY is not None:  # stress test: draw both themes, write only when asked to
    for name in THEMES:
        out = svg(name)
        assert out.endswith("</svg>")
        if os.environ.get("SNAKE_TEST_OUT"):
            os.makedirs(os.environ["SNAKE_TEST_OUT"], exist_ok=True)
            open(os.path.join(os.environ["SNAKE_TEST_OUT"], name), "w").write(out)
    print(f"ok: density {TEST_DENSITY}, {len(bites)} days, length {length_at(R - 1)}, {R} steps, out of order {out_of_order}, {planner}")
    sys.exit(0)
os.makedirs(OUT, exist_ok=True)
for name in THEMES:
    with open(os.path.join(OUT, name), "w") as f:
        f.write(svg(name))
print(f"{len(bites)} days eaten, {R} steps, {DUR}s per round, eaten out of order to get past: {out_of_order}, planner: {planner}")
