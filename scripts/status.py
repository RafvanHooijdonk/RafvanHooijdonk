import datetime, json, os, sys, urllib.request, zoneinfo

TOKEN = os.environ["GH_TOKEN"]
DRY = os.environ.get("STATUS_DRY_RUN") == "1"
PROJECTS = {"Alpha-Stock/": "AlphaStock", "RafvanHooijdonk/Apps": "Mijn Uren & PlateCollector",
            "RafvanHooijdonk/RafvanHooijdonk": "my GitHub profile"}


def gql(query, variables=None):
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        if any(e.get("type") == "INSUFFICIENT_SCOPES" for e in body["errors"]):
            print("token lacks the user scope, status not changed")
            sys.exit(0)
        sys.exit(body["errors"])
    return body["data"]


data = gql("""{ viewer {
  contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } }
  repositories(first: 30, orderBy: {field: PUSHED_AT, direction: DESC}, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
    nodes { nameWithOwner pushedAt primaryLanguage { name } } } } }""")["viewer"]

days = sorted((d for w in data["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]),
              key=lambda d: d["date"])
total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
today = days[-1]["contributionCount"] if days else 0

streak = 0
for d in reversed(days):
    if d["contributionCount"] > 0:
        streak += 1
    elif d is days[-1]:
        continue
    else:
        break

top = max(days, key=lambda d: d["contributionCount"]) if days else None
active_days = sum(1 for d in days if d["contributionCount"] > 0)

now = datetime.datetime.now(datetime.timezone.utc)
week_ago = now - datetime.timedelta(days=7)
langs = {}
for r in data["repositories"]["nodes"]:
    pushed = datetime.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
    if pushed >= week_ago and r["primaryLanguage"]:
        langs[r["primaryLanguage"]["name"]] = langs.get(r["primaryLanguage"]["name"], 0) + 1
week_lang = max(langs, key=langs.get) if langs else None

project = None
for r in data["repositories"]["nodes"]:
    name = next((label for prefix, label in PROJECTS.items() if r["nameWithOwner"].startswith(prefix)), None)
    if name:
        project = name
        break

options = []
if streak > 1:
    options.append((":fire:", f"{streak}-day contribution streak"))
if today > 0:
    options.append((":chart_with_upwards_trend:", f"{today} contribution{'s' if today != 1 else ''} today"))
options.append((":spiral_calendar:", f"{total:,} contributions in the last year"))
if top and top["contributionCount"] > 0:
    day = datetime.date.fromisoformat(top["date"])
    options.append((":trophy:", f"Busiest day: {top['contributionCount']} contributions on {day.day} {day:%b %Y}"))
options.append((":zap:", f"Active on {active_days} days in the last year"))

slot = (now.hour * 60 + now.minute) // 10
emoji, message = options[slot % len(options)]
stamp = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam"))
message = f"{message} | {stamp:%d/%m/%Y %H:%M}"
print(f"{len(options)} statuses, slot {slot} -> {emoji} {message}")
for e, m in options:
    print("  ", e, m)

if not DRY:
    gql("""mutation($emoji: String!, $message: String!) {
      changeUserStatus(input: {emoji: $emoji, message: $message, limitedAvailability: false}) { status { message } } }""",
        {"emoji": emoji, "message": message[:80]})
    print("status updated")
