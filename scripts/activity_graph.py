"""Generate a transparent SVG from GitHub's contribution calendar. Python stdlib only."""
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import urllib.request


def fetch_days(username, today):
    start = today - dt.timedelta(days=30)
    query = """query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { weeks { contributionDays { date contributionCount } } }
        }
      }
    }"""
    payload = {"query": query, "variables": {
        "login": username,
        "from": start.isoformat() + "T00:00:00Z",
        "to": today.isoformat() + "T23:59:59Z",
    }}
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Content-Type": "application/json", "User-Agent": "profile-activity-graph"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL: " + "; ".join(e["message"] for e in result["errors"]))
    user = result["data"]["user"]
    if not user:
        raise RuntimeError("GitHub user not found")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    found = {day["date"]: day["contributionCount"] for week in weeks for day in week["contributionDays"]}
    dates = [start + dt.timedelta(days=i) for i in range(31)]
    if any(date.isoformat() not in found for date in dates):
        raise RuntimeError("Incomplete contribution calendar; keeping the previous SVG")
    return [(date, found[date.isoformat()]) for date in dates]


def render(days, preview=False):
    left, right, top, bottom = 62, 1140, 100, 270
    ceiling = max(4, math.ceil(max(count for _, count in days) / 4) * 4)
    points = [(left + i * (right-left)/(len(days)-1), bottom-count/ceiling*(bottom-top))
              for i, (_, count) in enumerate(days)]
    coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    total = sum(count for _, count in days)
    subtitle = "DESIGN PREVIEW - SAMPLE DATA" if preview else f"{total} contributions · {days[0][0]:%d %b} - {days[-1][0]:%d %b %Y} · UTC"
    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="340" viewBox="0 0 1200 340" role="img" aria-labelledby="title desc">
<title id="title">Contribution activity - last 31 days</title>
<desc id="desc">{html.escape(subtitle)}. Daily contribution counts from GitHub.</desc>
<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#378add" stop-opacity=".28"/><stop offset="1" stop-color="#378add" stop-opacity=".015"/></linearGradient></defs>
<style>.label{{fill:#7d91a8}}.grid{{stroke:#378add;stroke-opacity:.13}}text{{font-family:Segoe UI,Arial,sans-serif}}@media(prefers-color-scheme:light){{.label{{fill:#536b84}}}}</style>
<text x="62" y="38" fill="#378add" font-size="24" font-weight="600">Contribution activity</text>
<text class="label" x="62" y="65" font-size="14">{html.escape(subtitle)}</text>''']
    for step in range(5):
        y = bottom - step/4 * (bottom-top)
        svg.append(f'<path class="grid" d="M{left} {y}H{right}"/><text class="label" x="46" y="{y+5}" text-anchor="end" font-size="12">{ceiling*step//4}</text>')
    svg.append(f'<polygon points="{left},{bottom} {coordinates} {right},{bottom}" fill="url(#area)"/>')
    svg.append(f'<polyline points="{coordinates}" fill="none" stroke="#378add" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    for (date, count), (x, y) in zip(days, points):
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#85b7eb"><title>{date}: {count} contributions</title></circle>')
    for index in [0, 5, 10, 15, 20, 25, 30]:
        svg.append(f'<text class="label" x="{points[index][0]:.1f}" y="300" text-anchor="middle" font-size="12">{days[index][0]:%d %b}</text>')
    svg.append('</svg>')
    return "\n".join(svg)


if __name__ == "__main__":
    username = os.environ.get("GH_USERNAME", "luizacoelh")
    today = dt.datetime.now(dt.timezone.utc).date()
    days = fetch_days(username, today)
    output = Path("assets/activity.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(render(days), encoding="utf-8")
    temporary.replace(output)
    print(f"Updated {output}: {len(days)} days")

