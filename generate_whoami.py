#!/usr/bin/env python3
"""Builds assets/whoami.svg: a terminal style profile card (portrait + live contribution stats).

Data source: the public contribution calendar fragment on github.com (no token needed).
Usage: python scripts/generate_whoami.py [username]
"""
import base64
import html
import re
import sys
import time
import urllib.request
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "charan270469"
DISPLAY_NAME = "Sai Charan Vullengala"
HANDLE = "charan@github"
ROOT = Path(__file__).resolve().parent.parent
PORTRAIT = ROOT / "assets" / "portrait.jpg"
OUT = ROOT / "assets" / "whoami.svg"

# Palette (violet on near black)
BG = "#1C1A19"
PANEL = "#211F1E"
CARD = "#282524"
BORDER = "#3A3532"
TEXT = "#EDE4DA"
MUTED = "#9A8C80"
ACCENT = "#F2B98A"
ACCENT_DIM = "#8A7361"
TERT = "#7AA5B4"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"


def fetch_calendar(start: date, end: date) -> "OrderedDict[date, int]":
    url = f"https://github.com/users/{USER}/contributions?from={start}&to={end}"
    last_err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 profile-card"})
            page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            break
        except Exception as e:  # network hiccup, retry with backoff
            last_err = e
            time.sleep(2 ** attempt)
    else:
        raise SystemExit(f"could not fetch contributions: {last_err}")

    id_to_date = dict(
        (cid, datetime.strptime(d, "%Y-%m-%d").date())
        for d, cid in re.findall(r'data-date="(\d{4}-\d\d-\d\d)"\s+id="(contribution-day-component-\d+-\d+)"', page)
    )
    counts = {}
    for cid, text in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"(\d+) contribution", text.strip())
        counts[id_to_date[cid]] = int(m.group(1)) if m else 0
    if not counts:
        raise SystemExit("calendar parse returned no days")
    return OrderedDict((d, counts.get(d, 0)) for d in sorted(counts) if start <= d <= end)


def streaks(days: "OrderedDict[date, int]", today: date):
    ordered = list(days.items())
    best = (0, None, None)
    run, run_start = 0, None
    for d, c in ordered:
        if c > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > best[0]:
                best = (run, run_start, d)
        else:
            run = 0
    # current streak: walk back from today (grace: today may still be empty)
    cur, cur_end = 0, None
    d = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    cur_end = d
    while days.get(d, 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    cur_start = d + timedelta(days=1)
    return (cur, cur_start if cur else None, cur_end if cur else None), best


def fmt(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def rng(s, e):
    return f"{fmt(s)} - {fmt(e)}" if s and e else "no active streak"


def monthly(days, today):
    months = []
    y, m = today.year, today.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    totals = {k: 0 for k in months}
    for d, c in days.items():
        if (d.year, d.month) in totals:
            totals[(d.year, d.month)] += c
    return [(("JFMAMJJASOND")[m - 1], totals[(y, m)]) for y, m in months]


def build_svg(days, today) -> str:
    total = sum(days.values())
    active = sum(1 for c in days.values() if c > 0)
    span = len(days)
    best_day = max(days.items(), key=lambda kv: kv[1])
    cur, best = streaks(days, today)
    avg = total / active if active else 0
    bars = monthly(days, today)
    peak = max(v for _, v in bars) or 1

    img = base64.b64encode(PORTRAIT.read_bytes()).decode()
    W, H = 960, 646

    def card(x, y, w, h, label, value, unit, sub, value_color=TEXT):
        unit_svg = ""
        if unit:
            unit_svg = f'<tspan font-size="14" font-weight="400" fill="{MUTED}" dx="6">{html.escape(unit)}</tspan>'
        return f"""
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{CARD}" stroke="{BORDER}"/>
    <text x="{x+14}" y="{y+24}" font-size="11" fill="{MUTED}">$ {html.escape(label)}</text>
    <text x="{x+14}" y="{y+62}" font-size="34" font-weight="700" fill="{value_color}">{html.escape(value)}{unit_svg}</text>
    <text x="{x+14}" y="{y+82}" font-size="10.5" fill="{MUTED}">{html.escape(sub)}</text>
  </g>"""

    rx, rw = 480, 460
    cw = (rw - 28 - 10) // 2
    c1x, c2x = rx + 14, rx + 14 + cw + 10
    y0 = 110
    rows = [y0, y0 + 102, y0 + 204]
    cards = "".join([
        card(c1x, rows[0], cw, 92, "current streak", f"{cur[0]}", "days", rng(cur[1], cur[2]), ACCENT),
        card(c2x, rows[0], cw, 92, "longest streak", f"{best[0]}", "days", rng(best[1], best[2]), TERT),
        card(c1x, rows[1], cw, 92, "contributions", f"{total:,}", "", "in the last year"),
        card(c2x, rows[1], cw, 92, "active days", f"{active}", f"/ {span}", f"{round(100*active/span)}% of the year"),
        card(c1x, rows[2], cw, 92, "best day", f"{best_day[1]}", "", fmt(best_day[0])),
        card(c2x, rows[2], cw, 92, "avg / active day", f"{avg:.1f}", "", "contributions"),
    ])

    # monthly chart card
    cx, cy, cwid, chei = rx + 14, rows[2] + 102, rw - 28, 196
    base_y = cy + chei - 28
    max_h = chei - 76
    slot = (cwid - 28) / len(bars)
    bw = slot * 0.62
    bar_svg = []
    for i, (lab, v) in enumerate(bars):
        h = max(4, v / peak * max_h)
        x = cx + 14 + i * slot + (slot - bw) / 2
        y = base_y - h
        is_peak = v == peak
        fill = ACCENT if is_peak else ACCENT_DIM
        bar_svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" fill="{fill}"/>')
        if is_peak:
            bar_svg.append(
                f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="9.5" font-weight="700" fill="{TEXT}" text-anchor="middle">{v:,}</text>'
            )
        bar_svg.append(
            f'<text x="{x+bw/2:.1f}" y="{base_y+14}" font-size="9" fill="{MUTED}" text-anchor="middle">{lab}</text>'
        )
    chart = f"""
  <g>
    <rect x="{cx}" y="{cy}" width="{cwid}" height="{chei}" rx="8" fill="{CARD}" stroke="{BORDER}"/>
    <text x="{cx+14}" y="{cy+24}" font-size="11" fill="{MUTED}">$ contributions / month</text>
    {''.join(bar_svg)}
  </g>"""

    dots = lambda x, y: (
        f'<circle cx="{x}" cy="{y}" r="4.5" fill="#C5956E"/>'
        f'<circle cx="{x+16}" cy="{y}" r="4.5" fill="#8A7361"/>'
        f'<circle cx="{x+32}" cy="{y}" r="4.5" fill="#7AA5B4"/>'
    )

    stamp = today.strftime("%Y-%m-%d")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(DISPLAY_NAME)} GitHub profile card, updated {stamp}">
<style>text{{font-family:{MONO};}}</style>
<rect width="{W}" height="{H}" fill="{BG}"/>
<rect x="258" y="12" width="444" height="30" rx="6" fill="{CARD}" stroke="{BORDER}"/>
<text x="480" y="32" font-size="14" font-weight="700" fill="{TEXT}" text-anchor="middle">{HANDLE} ~ $ whoami</text>
<rect x="10.5" y="56.5" width="939" height="580" fill="none" stroke="{BORDER}"/>
<line x1="470.5" y1="56.5" x2="470.5" y2="636.5" stroke="{BORDER}"/>

<!-- left window: portrait -->
<rect x="20" y="66" width="440" height="560" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
{dots(36, 82)}
<text x="240" y="86" font-size="10" fill="{MUTED}" text-anchor="middle">{HANDLE}:~$ ./portrait.sh</text>
<line x1="20" y1="98" x2="460" y2="98" stroke="{BORDER}"/>
<image x="20" y="99" width="440" height="486" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/jpeg;base64,{img}" href="data:image/jpeg;base64,{img}"/>
<line x1="20" y1="586" x2="460" y2="586" stroke="{BORDER}"/>
<text x="34" y="610" font-size="10" fill="{MUTED}">{HANDLE}:~$ whoami <tspan fill="{ACCENT}" font-weight="700" dx="4">{html.escape(DISPLAY_NAME)}</tspan></text>

<!-- right window: stats -->
<rect x="{rx}" y="66" width="{rw}" height="560" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
{dots(rx+16, 82)}
<text x="{rx+rw/2}" y="86" font-size="10" fill="{MUTED}" text-anchor="middle">{HANDLE}:~$ ./stats.sh</text>
<line x1="{rx}" y1="98" x2="{rx+rw}" y2="98" stroke="{BORDER}"/>
{cards}
{chart}
</svg>
"""


def main():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    days = OrderedDict()
    # the endpoint clamps a request to one calendar year, so fetch per year and merge
    for year in range(start.year, today.year + 1):
        lo = max(start, date(year, 1, 1))
        hi = min(today, date(year, 12, 31))
        days.update(fetch_calendar(lo, hi))
    days = OrderedDict(sorted(days.items()))
    OUT.write_text(build_svg(days, today), encoding="utf-8")
    print(f"wrote {OUT} ({len(days)} days, {sum(days.values())} contributions)")


if __name__ == "__main__":
    main()
