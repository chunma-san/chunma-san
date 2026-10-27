"""Public-only profile cards maintained by https://github.com/chunma-san.

Uses public REST resources and GitHub's public contribution calendar. No private
repository content, private activity, estimated lines or fabricated counts.
"""
from collections import Counter
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import urllib.request

OWNER = 'chunma-san'
ROOT = Path(__file__).resolve().parents[1]


def fetch(url, api=False):
    headers = {'User-Agent': 'chunma-san-profile-metrics', 'Accept': 'application/vnd.github+json' if api else 'text/html'}
    token = os.environ.get('GITHUB_TOKEN')
    if api and token:
        headers['Authorization'] = 'Bearer ' + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read().decode('utf-8')


def api(path):
    return json.loads(fetch('https://api.github.com' + path, True))


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'td' and 'data-date' in a and 'data-level' in a:
            self.days[a['data-date']] = int(a['data-level'])


def text(x, y, value, size=13, color='#c9c3c5', weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'


def card(title, subtitle, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" viewBox="0 0 480 {height}" role="img">'
            f'<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>'
            '<rect x=".5" y=".5" width="479" height="' + str(height-1) + '" rx="14" fill="#100b0d" stroke="#392127"/>'
            '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">'
            + text(24, 36, title, 19, '#f1e9eb', 650) + text(24, 58, subtitle, 11, '#a38e94') + body + '</g></svg>')


def main():
    user = api('/users/' + OWNER)
    repos = []
    for page in range(1, 11):
        batch = api(f'/users/{OWNER}/repos?type=owner&per_page=100&page={page}')
        repos += [r for r in batch if not r['private']]
        if len(batch) < 100:
            break
    else:
        raise RuntimeError('Repository pagination exceeded limit')
    starred = api(f'/users/{OWNER}/starred?per_page=4&sort=created&direction=desc')
    html = fetch(f'https://github.com/users/{OWNER}/contributions')
    calendar = Calendar()
    calendar.feed(html)
    count = re.search(r'id="js-contribution-activity-description"[^>]*>\s*([\d,]+)\s+contributions', html)
    if len(calendar.days) < 350 or not count:
        raise RuntimeError('Public contribution calendar markup changed')
    total = int(count[1].replace(',', ''))
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    original = [r for r in repos if not r['fork']]
    body = text(24, 108, '@' + OWNER, 25, '#ef4444', 700)
    body += text(24, 137, 'My tools. My own path.', 15)
    rows = [('Public repositories', len(repos)), ('Original repositories', len(original)),
            ('Stars on public repositories', sum(r['stargazers_count'] for r in repos)),
            ('Forks of public repositories', sum(r['forks_count'] for r in repos)),
            ('Followers', user['followers']), ('Contributions · last year', total)]
    for i, (label, value) in enumerate(rows):
        y = 195 + i*57
        body += text(24, y, label, 13) + text(420, y, f'{value:,}', 22, '#f5e9ec', 650)
        body += f'<path d="M24 {y+17}H456" stroke="#2d1b20"/>'
    body += text(24, 570, 'SELF-HOSTING / AUTOMATION / DISCORD', 11, '#ef7777', 600)
    body += text(24, 600, 'Only public repository statistics are collected.', 12)
    body += text(24, 623, 'Contribution total follows GitHub profile visibility.', 12)
    body += text(24, 664, 'Updated ' + today + ' UTC', 11, '#a38e94')
    classic = card('chunma / GitHub overview', 'Public profile snapshot', 696, body)

    days = sorted(calendar.days)
    start = datetime.fromisoformat(days[0]).date()
    colors = ['#24161c', '#592027', '#8a2831', '#c63740', '#ef4444']
    body = ''
    for date in days:
        current = datetime.fromisoformat(date).date()
        offset = (current-start).days + ((start.weekday()+1) % 7)
        x, y = 24 + (offset//7)*8, 85 + (offset%7)*12
        color = colors[max(0, min(4, calendar.days[date]))]
        body += f'<rect x="{x}" y="{y}" width="6" height="9" rx="1" fill="{color}"><title>{date}: contribution level {calendar.days[date]}</title></rect>'
    body += text(24, 190, f'{total:,} contributions · {days[0]} to {days[-1]}', 12)
    cal = card('A year of contributions', 'GitHub activity levels · rolling public calendar', 212, body)

    languages = Counter(r['language'] for r in original if r.get('language'))
    denominator = sum(languages.values())
    body = ''
    for i, (name, n) in enumerate(languages.most_common(5)):
        y = 89 + i*24
        body += text(24, y, name, 12) + text(363, y, f'{n} repos', 12, '#ef7777')
        body += f'<rect x="165" y="{y-8}" width="{max(2, int(175*n/max(1,denominator)))}" height="7" rx="3" fill="#ef4444"/>'
    if not languages:
        body += text(24, 100, 'No public language data available.')
    lang = card('Languages', 'Primary language by original public repository · not code bytes', 212, body)

    body = ''
    for i, repo in enumerate(starred):
        y = 88 + i*44
        label = repo['full_name']
        if len(label) > 52:
            label = label[:49] + '...'
        body += f'<a href="{escape(repo["html_url"], quote=True)}">' + text(24, y, label, 13, '#f5e9ec', 550) + '</a>'
        body += text(24, y+18, f'{repo.get("language") or "Repository"} / {repo["stargazers_count"]:,} stars', 11, '#a38e94')
    stars = card('Recently starred', 'Four latest repositories saved on GitHub', 256, body)
    assets = ROOT / 'assets'
    assets.mkdir(exist_ok=True)
    for name, svg in [('metrics-classic.svg', classic), ('metrics-calendar.svg', cal), ('metrics-languages.svg', lang), ('metrics-stars.svg', stars)]:
        path = assets / name
        temporary = path.with_suffix('.tmp')
        temporary.write_text(svg, encoding='utf-8')
        temporary.replace(path)
    print('Four public-only profile cards generated')


if __name__ == '__main__':
    main()
