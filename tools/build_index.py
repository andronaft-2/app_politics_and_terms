"""Rebuilds the app list in index.html and the table in README.md from the app folders.

Every folder with privacy.html, terms.html and support.html is an app. Its display name comes from the
current index.html (the <h2> above its links), or from the <title> of its privacy page for a new app.
A folder with only support.html is an app too when it has links.json: {"name": ..., "privacy": url, "terms": url}
for pages hosted elsewhere (Water Buddy).
Language links (es, uk, de) appear when the page has a section with that id.
Run after adding an app, or to resolve merge conflicts in index.html / README.md:  python3 tools/build_index.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://andronaft-2.github.io/app_politics_and_terms/'
PAGES = ('privacy', 'terms', 'support')
LABELS = {
    'en': {'privacy': 'Privacy policy', 'terms': 'Terms of use', 'support': 'Support'},
    'uk': {'privacy': 'Політика конфіденційності', 'terms': 'Умови використання', 'support': 'Підтримка'},
    'de': {'privacy': 'Datenschutzerklärung', 'terms': 'Nutzungsbedingungen', 'support': 'Hilfe'},
    'es': {'privacy': 'Política de privacidad', 'terms': 'Términos de uso', 'support': 'Soporte'},
}


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def external(folder):
    """Links for pages hosted elsewhere, or None."""
    path = os.path.join(ROOT, folder, 'links.json')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def apps():
    found = [d for d in os.listdir(ROOT)
             if all(os.path.isfile(os.path.join(ROOT, d, f'{p}.html')) for p in PAGES)
             or (os.path.isfile(os.path.join(ROOT, d, 'support.html')) and external(d))]
    index = read('index.html')
    # Keep the current order and names; conflict markers or broken sections don't matter here.
    order, names = [], {}
    for m in re.finditer(r'<h2>(.*?)</h2>(.*?)(?=<h2>|</main>)', index, re.S):
        folders = re.findall(r'href="([a-z0-9-]+)/(?:privacy|support)\.html"', m.group(2))
        if folders and folders[0] not in names:
            names[folders[0]] = m.group(1).strip()
            order.append(folders[0])
    for d in sorted(found):
        if d not in names:
            ext = external(d)
            if ext:
                names[d] = ext['name']
                order.append(d)
                continue
            title = re.search(r'<title>(.*?)</title>', read(f'{d}/privacy.html'), re.S)
            names[d] = re.sub(r'\s*privacy policy\s*$', '', title.group(1).strip(), flags=re.I) if title else d
            order.append(d)
    return [(d, names[d]) for d in order if d in found]


def langs(folder, page):
    html = read(f'{folder}/{page}.html')
    return ['en'] + [l for l in ('es', 'uk', 'de') if f'id="{l}"' in html]


def page_url(folder, page):
    ext = external(folder)
    return ext[page] if ext and page in ext else f'{SITE}{folder}/{page}.html'


def section(folder, name):
    rows = []
    ext = external(folder)
    for p in PAGES:
        if ext and p in ext:
            links = [f'<a href="{ext[p]}">{LABELS["en"][p]}</a>']
        else:
            links = [f'<a href="{folder}/{p}.html{"" if l == "en" else "#" + l}">{LABELS[l][p]}</a>' for l in langs(folder, p)]
        rows.append(f'      <li>{" · ".join(links)}</li>')
    return '  <section class="doc">\n    <h2>' + name + '</h2>\n    <ul>\n' + '\n'.join(rows) + '\n    </ul>\n  </section>'


def main():
    items = apps()
    index = read('index.html')
    head = index[:index.index('<section class="doc">')].rstrip(' ')
    head = re.sub(r'<<<<<<<.*?>>>>>>>[^\n]*\n', '', head, flags=re.S)
    body = '\n'.join(section(d, n) for d, n in items)
    with open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(head + body + '\n</main>\n</body>\n</html>\n')

    readme = read('README.md')
    table_start = readme.index('| App |')
    table_end = readme.index('\n\n', table_start)
    rows = ['| App | Privacy policy | Terms of use | Support |', '| --- | --- | --- | --- |']
    for d, n in items:
        plain = n.replace('&amp;', '&')
        rows.append(f'| {plain} | ' + ' | '.join(f'[{d}/{p}.html]({page_url(d, p)})' for p in PAGES) + ' |')
    with open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme[:table_start] + '\n'.join(rows) + readme[table_end:])
    print(f'{len(items)} apps:', ', '.join(d for d, _ in items))


if __name__ == '__main__':
    main()
