#!/usr/bin/env python3
import os
import re
import sys
import datetime
import argparse
import subprocess
import urllib.parse
from html.parser import HTMLParser
import yaml

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '_data')

# Custom YAML Dumper to preserve list indentation and single quotes for HTML
class CleanDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(CleanDumper, self).increase_indent(flow, False)

def string_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    # Long prose (idea summaries, angles, facts) folds across lines instead of
    # running off the right edge, so the file stays editable by hand.
    if len(data) > 120:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
    if any(char in data for char in ["'", '"', '<', '>', '&', '·', '🇰🇷', '🇮🇳', '🇧🇩']):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

CleanDumper.add_representer(str, string_representer)

def load_yaml(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            sys.exit(1)

def leading_comment(filename):
    """Return the comment block at the top of a data file, verbatim.

    research_ideas.yml carries its own schema documentation. Re-emitting that
    block on save is what keeps `add-idea` from deleting the instructions.
    """
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return ''
    kept = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                kept.append(line)
            elif line.strip() == '' and kept:
                kept.append(line)
            else:
                break
    return ''.join(kept)

def save_yaml(filename, data, header=None, width=1000):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        if header:
            f.write(header)
        # Print a header comment if applicable
        elif filename == 'news.yml':
            f.write("# Home page \"Updates\" timeline (most recent first). HTML allowed in `text`.\n")
        elif filename == 'publications.yml':
            f.write('# Publications, newest year first. `year` groups + drives the year filter.\n')
            f.write('# `type`: conference | journal | preprint | workshop. `flagship`: vision | robotics.\n')
        elif filename == 'projects.yml':
            f.write('# Research projects, bootcamps, and industrial collaborations.\n')
        
        yaml.dump(data, f, Dumper=CleanDumper, default_flow_style=False, sort_keys=False, allow_unicode=True, width=width)
    print(f"Successfully updated {filename}")

def add_news_item(text, date=None):
    if not date:
        now = datetime.datetime.now()
        date = now.strftime("%B %Y")
    
    news = load_yaml('news.yml')
    new_item = {
        'date': date,
        'text': text
    }
    # Prepend to news list (newest first)
    news.insert(0, new_item)
    save_yaml('news.yml', news)

def add_publication_interactive():
    print("=== Add New Publication ===")
    title = input("Title: ").strip()
    if not title:
        print("Title is required!")
        return

    authors = input("Authors (default: 'Md Selim Sarowar, and Sungho Kim'): ").strip()
    if not authors:
        authors = "Md Selim Sarowar, and Sungho Kim"

    venue = input("Venue (Full Name, e.g. 'IEEE/RSJ International Conference on Intelligent Robots and Systems'): ").strip()
    venue_short = input("Venue Abbreviation (e.g. 'IROS\\'27' or empty): ").strip()
    
    try:
        year = int(input(f"Year (default: {datetime.datetime.now().year}): ").strip() or datetime.datetime.now().year)
    except ValueError:
        print("Invalid year!")
        return

    pub_type = input("Type (conference | journal | preprint | workshop): ").strip().lower()
    if pub_type not in ['conference', 'journal', 'preprint', 'workshop']:
        print("Invalid type! Defaulting to 'conference'")
        pub_type = 'conference'

    flagship = input("Flagship (vision | robotics | none): ").strip().lower()
    if flagship not in ['vision', 'robotics']:
        flagship = None

    rank = input("CORE Rank (A* | A | B | none): ").strip()
    if rank.lower() == 'none' or not rank:
        rank = None

    impact = None
    if pub_type == 'journal':
        impact = input("Impact info (e.g. 'SCIE-Q1, IF: 4.2' or empty): ").strip()
        if not impact:
            impact = None

    url = input("URL (e.g. project page link or arXiv link): ").strip()
    
    # Links
    links = []
    pdf_url = input("PDF URL (optional): ").strip()
    if pdf_url:
        links.append({'label': 'PDF', 'url': pdf_url, 'kind': 'pdf'})
    
    code_url = input("Code GitHub URL (optional): ").strip()
    if code_url:
        links.append({'label': 'Code', 'url': code_url, 'kind': 'code'})
        
    project_url = input("Project Page URL (optional): ").strip()
    if project_url:
        links.append({'label': 'Project Page', 'url': project_url, 'kind': 'project'})

    # Custom BibTeX
    print("Enter custom BibTeX citation (press Enter on empty line to finish):")
    bib_lines = []
    while True:
        line = input()
        if not line:
            break
        bib_lines.append(line)
    bibtex = "\n".join(bib_lines).strip() if bib_lines else None

    # Construct publication object
    pub = {
        'title': title,
        'authors': authors,
        'venue': venue,
    }
    if venue_short:
        pub['venue_short'] = venue_short
    pub['year'] = year
    pub['type'] = pub_type
    if flagship:
        pub['flagship'] = flagship
    if rank:
        pub['rank'] = rank
    if impact:
        pub['impact'] = impact
    if url:
        pub['url'] = url
    if bibtex:
        pub['bibtex'] = bibtex
    if links:
        pub['links'] = links

    publications = load_yaml('publications.yml')
    
    # Insert in order of year (newest first)
    inserted = False
    for i, p in enumerate(publications):
        if year >= p.get('year', 0):
            publications.insert(i, pub)
            inserted = True
            break
    if not inserted:
        publications.append(pub)

    save_yaml('publications.yml', publications)

def add_project_interactive():
    print("=== Add New Project ===")
    category = input("Category (bootcamp | research | industry): ").strip().lower()
    if category not in ['bootcamp', 'research', 'industry']:
        print("Invalid category!")
        return

    if category == 'industry':
        name = input("Partner Name (e.g. 'YUJINMS Co. Ltd., Korea'): ").strip()
        timeline = input("Timeline (default: 'During M.Sc.'): ").strip() or "During M.Sc."
        
        print("Enter detail points (press Enter on empty line to finish):")
        points = []
        # First point is the Project Title
        title_point = input("Project Title Point: ").strip()
        if title_point:
            points.append(title_point)
            while True:
                pt = input("Detail Point: ").strip()
                if not pt:
                    break
                points.append(pt)
        
        proj_item = {
            'name': name,
            'timeline': timeline,
            'points': points
        }
        
        projects_data = load_yaml('projects.yml')
        # Prepend to industry projects (YUJINMS is first, we put it at index 0 or append)
        if 'industry' not in projects_data:
            projects_data['industry'] = []
        projects_data['industry'].insert(0, proj_item)
        save_yaml('projects.yml', projects_data)

    else:
        # Bootcamp or Research goes into 'latest' list with a category field
        title = input("Project Title: ").strip()
        meta = input("Meta / Duration (e.g. '3-Month Extensive Bootcamp · Vizuara AI Lab'): ").strip()
        desc = input("Short Description (Korean/English): ").strip()
        
        proj_item = {
            'title': title,
            'category': 'Bootcamp' if category == 'bootcamp' else 'Research',
            'meta': meta,
            'desc': desc
        }
        
        repo = input("GitHub Repository URL (optional): ").strip()
        if repo:
            proj_item['repo'] = repo

        projects_data = load_yaml('projects.yml')
        if 'latest' not in projects_data:
            projects_data['latest'] = []
        projects_data['latest'].insert(0, proj_item)
        save_yaml('projects.yml', projects_data)

IDEA_STATUSES = ['spark', 'shaping', 'active', 'parked', 'shipped']
IDEA_LEVELS = ['low', 'medium', 'high']
IDEA_SOURCES = ['linkedin', 'arxiv', 'paper', 'talk', 'lab', 'self', 'web']

def slugify(text):
    out = ''.join(c.lower() if c.isalnum() else '-' for c in text)
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')[:48]

def ask(label, default=None, required=False):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("  Required.")

def ask_choice(label, options, default=None):
    print(f"{label} ({', '.join(options)})")
    while True:
        value = ask("  >", default)
        if value in options:
            return value
        print(f"  Pick one of: {', '.join(options)}")

def ask_list(label):
    print(f"{label} (one per line, blank line ends)")
    items = []
    while True:
        value = input("  - ").strip()
        if not value:
            return items
        items.append(value)

def add_idea_interactive():
    """Append an entry to _data/research_ideas.yml, newest first."""
    data = load_yaml('research_ideas.yml')
    if not isinstance(data, dict):
        print("research_ideas.yml is malformed: expected a mapping with `themes` and `ideas`.")
        sys.exit(1)
    themes = data.get('themes', [])
    ideas = data.get('ideas', [])
    theme_ids = [t['id'] for t in themes]

    print("\n--- New research idea ---")
    title = ask("Title (short claim or question)", required=True)

    print("\nThemes:")
    for t in themes:
        print(f"  {t['id']:<16} {t['label']}")
    theme = ask_choice("Primary theme", theme_ids, theme_ids[0] if theme_ids else None)
    also = [a.strip() for a in ask("Secondary themes (comma separated, optional)").split(',') if a.strip()]
    unknown = [a for a in also if a not in theme_ids]
    if unknown:
        print(f"  Ignoring unknown theme ids: {', '.join(unknown)}")
        also = [a for a in also if a in theme_ids]

    status = ask_choice("Status", IDEA_STATUSES, 'spark')
    priority = ask("Priority 1-5", '3')
    effort = ask_choice("Effort to a first result", IDEA_LEVELS, 'medium')
    risk = ask_choice("Risk the idea does not survive contact", IDEA_LEVELS, 'medium')
    venue = ask("Candidate venue (optional)")
    summary = ask("Summary (one or two sentences)", required=True)
    why = ask("Why it matters (optional)")
    angle = ask("My angle, including what makes it hard (optional)")

    questions = ask_list("Open questions")
    next_steps = ask_list("Next actions")
    tags = [t.strip() for t in ask("Tags (comma separated)").split(',') if t.strip()]
    connects = [c.strip() for c in ask("Own projects it touches (comma separated)").split(',') if c.strip()]

    print("\nSource:")
    src_kind = ask_choice("  kind", IDEA_SOURCES, 'web')
    src_author = ask("  author")
    src_label = ask("  label")
    src_url = ask("  url")

    print("\nExtra links (blank label ends)")
    links = []
    while True:
        label = input("  label: ").strip()
        if not label:
            break
        url = input("  url:   ").strip()
        links.append({'label': label, 'url': url})

    note = ask("Caveat printed at the bottom of the card (optional)")

    suggested = slugify(title)
    idea_id = ask("Id (stable slug, used by links)", suggested)
    existing = {i.get('id') for i in ideas}
    if idea_id in existing:
        print(f"  Id '{idea_id}' is already used. Pick another.")
        sys.exit(1)

    try:
        priority = max(1, min(5, int(priority)))
    except ValueError:
        priority = 3

    item = {
        'id': idea_id,
        'title': title,
        'theme': theme,
    }
    if also:
        item['also'] = also
    item.update({
        'status': status,
        'priority': priority,
        'added': datetime.date.today().isoformat(),
        'effort': effort,
        'risk': risk,
    })
    for key, value in (('venue', venue), ('summary', summary), ('why', why), ('angle', angle)):
        if value:
            item[key] = value
    if questions:
        item['questions'] = questions
    if next_steps:
        item['next'] = next_steps
    if src_url or src_label or src_author:
        item['source'] = {
            'kind': src_kind,
            'author': src_author,
            'label': src_label,
            'url': src_url,
            'captured': datetime.date.today().isoformat(),
        }
    if links:
        item['links'] = links
    if connects:
        item['connects'] = connects
    item['related'] = []
    if tags:
        item['tags'] = tags
    if note:
        item['note'] = note

    ideas.insert(0, item)
    data['ideas'] = ideas
    save_yaml('research_ideas.yml', data, header=leading_comment('research_ideas.yml'), width=86)
    print(f"Added idea '{idea_id}'. It renders at /research-ideas/#idea-{idea_id}.")

# ---------------------------------------------------------------------------
#  Link library: import a browser bookmarks export into _data/link_library.yml
# ---------------------------------------------------------------------------

LINK_GROUPS = [
    {'id': 'robotics', 'label': 'Robotics Labs', 'icon': 'fa-robot', 'color': '#ea7317',
     'blurb': 'Groups, institutes and people working on robot learning and control.'},
    {'id': 'vision', 'label': 'Computer Vision Labs', 'icon': 'fa-eye', 'color': '#0891b2',
     'blurb': 'Vision, graphics and perception groups worth watching.'},
    {'id': 'benchmarks', 'label': 'Benchmarks & Datasets', 'icon': 'fa-database', 'color': '#ef4444',
     'blurb': 'Simulators, task suites and datasets used for evaluation.'},
    {'id': 'people', 'label': 'Researchers', 'icon': 'fa-user-graduate', 'color': '#8b5cf6',
     'blurb': 'Individual homepages and profiles.'},
    {'id': 'funding', 'label': 'Funding & Positions', 'icon': 'fa-award', 'color': '#f59e0b',
     'blurb': 'Fellowships, mobility schemes and open calls.'},
    {'id': 'tools', 'label': 'Tools & Trackers', 'icon': 'fa-toolbox', 'color': '#10b981',
     'blurb': 'Writing, figure, deadline and paper-tracking tools.'},
]

# Bookmark folder (below the bar) -> group id. Anything unmapped lands in the
# fallback group and can be re-sorted by editing the data file.
FOLDER_GROUPS = {
    ('Robo Labs',): 'robotics',
    ('Robo Labs', 'Benchmark'): 'benchmarks',
    ('CV Labs',): 'vision',
    ('Scientists',): 'people',
}

# Hosts that are private accounts, chat sessions or workspaces. A portfolio
# page is public, so these never leave the browser.
SKIP_HOSTS = {
    'mail.google.com', 'keep.google.com', 'docs.google.com', 'drive.google.com',
    'notebook.google.com', 'calendar.google.com', 'app.notion.com', 'www.notion.so',
    'notion.so', 'claude.ai', 'chatgpt.com', 'chat.openai.com', 'prism.openai.com',
    'gemini.google.com', 'grok.com', 'perplexity.ai', 'www.perplexity.ai',
    'chat.sakana.ai', 'manus.im', 'www.meta.ai', 'meta.ai', 'portal.yu.ac.kr',
    'factchat.yu.ac.kr', 'www.google.com', 'google.com', 'www.canva.com',
    'huggingface.co/selim-sarowar',
}
SKIP_PATTERNS = ('/login', '/signin', '/sign-in', '/sso/', 'mentor-login', 'localhost')
# authuser, usp and pli ride along on Google Sites links and say nothing about
# the page, so they are stripped rather than treated as private.
TRACKING_PREFIXES = ('utm_', 'fbclid', 'gclid', 'icid', 'linkid', 'rcm', 'mibextid',
                     'authuser', 'usp', 'pli', 'sa', 'ved')

def _host(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ''

def _is_public(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False, 'not a web link'
    host = parsed.netloc.lower()
    if not host:
        return False, 'no host'
    if re.match(r'^\d{1,3}(\.\d{1,3}){3}', host):
        return False, 'internal address'
    if host in SKIP_HOSTS:
        return False, 'private account or workspace'
    low = url.lower()
    for pat in SKIP_PATTERNS:
        if pat in low:
            return False, 'session or login URL'
    return True, ''

def clean_url(url):
    parsed = urllib.parse.urlparse(url)
    keep = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query)
            if not any(k.lower().startswith(p) for p in TRACKING_PREFIXES)]
    query = urllib.parse.urlencode(keep)
    return urllib.parse.urlunparse(parsed._replace(query=query))

def url_key(url):
    parsed = urllib.parse.urlparse(clean_url(url))
    path = parsed.path.rstrip('/')
    return (parsed.netloc.lower().replace('www.', ''), path, parsed.query)

def classify(url, title, group):
    """Best-guess kind, stored in the file so it can be corrected by hand."""
    host = _host(url).replace('www.', '')
    low = (url + ' ' + title).lower()
    if host in ('github.com', 'gitlab.com', 'huggingface.co', 'gitee.com'):
        return 'code'
    if host in ('arxiv.org', 'openreview.net', 'proceedings.mlr.press') or 'substack.com' in host \
            or '/blog' in low or 'medium.com' in host:
        return 'reading'
    if 'youtube.com' in host or 'youtu.be' in host:
        return 'talk'
    if any(w in low for w in ('jobs', 'careers', 'vacanc', 'recruit', 'position', 'phd-candidate',
                              'fellowship', 'scholarship', 'euraxess', 'jobbnorge')):
        return 'position'
    if group == 'benchmarks' or any(w in low for w in ('benchmark', 'dataset', 'challenge', 'leaderboard')):
        return 'dataset'
    if group == 'people' or 'sites.google.com/view' in low:
        return 'people'
    if any(w in low for w in ('lecture', 'course', 'tutorial', 'summer school')):
        return 'course'
    if group == 'tools':
        return 'tool'
    return 'lab'

def tidy_title(title, url):
    title = re.sub(r'\s+', ' ', title or '').strip()
    note = ''
    if _host(url).endswith('github.com') and ': ' in title:
        title, note = title.split(': ', 1)
    if len(title) > 96:
        title = title[:95].rstrip() + '\u2026'
    if len(note) > 160:
        note = note[:159].rstrip() + '\u2026'
    return title or urllib.parse.urlparse(url).netloc, note

class BookmarkParser(HTMLParser):
    """Netscape bookmark format: nested <DL> with <H3> folders and <A> links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.path, self.items = [], []
        self._mode, self._attrs, self._buf = None, {}, ''

    def handle_starttag(self, tag, attrs):
        if tag == 'h3':
            self._mode, self._buf = 'h3', ''
        elif tag == 'a':
            self._mode, self._buf, self._attrs = 'a', '', dict(attrs)

    def handle_endtag(self, tag):
        if tag == 'h3':
            self.path.append(self._buf.strip())
            self._mode = None
        elif tag == 'a':
            self.items.append({
                'folder': tuple(self.path),
                'title': self._buf.strip(),
                'url': self._attrs.get('href', ''),
                'added': self._attrs.get('add_date', ''),
            })
            self._mode = None
        elif tag == 'dl' and self.path:
            self.path.pop()

    def handle_data(self, data):
        if self._mode:
            self._buf += data

LINK_LIBRARY_HEADER = """\
# ==========================================================================
#  Link Library - data source for the directory on /research-ideas/
# ==========================================================================
#
#  Rendered by _pages/research-ideas.html below the idea board, filtered by
#  initLinkLibrary() in assets/js/main.js.
#
#  Import a browser bookmarks export (File > Bookmark manager > Export):
#      ./scripts/manage.py import-bookmarks --file bookmarks.html
#  It merges: existing entries and any hand edits are kept, new URLs are
#  appended, duplicates and private links are skipped. Add one by hand with:
#      ./scripts/manage.py add-link
#
#  groups   Sections of the directory, in display order.
#             id, label, icon (Font Awesome solid), color (hex), blurb
#  links    id     stable slug, used by the anchor
#           title  display name
#           url    the link
#           group  group id
#           kind   lab | code | reading | dataset | people | course |
#                  position | talk | tool   (drives the icon and the filter)
#           site   host shown under the title
#           note   one line of context, optional
#           added  YYYY-MM-DD the link was captured
#
#  Folders that the importer maps: Robo Labs -> robotics,
#  Robo Labs/Benchmark -> benchmarks, CV Labs -> vision,
#  Scientists -> people. Everything else lands in the fallback group.
# ==========================================================================

"""

def link_slug(title, url, taken):
    base = slugify(title) or slugify(_host(url)) or 'link'
    base = base[:44]
    slug, n = base, 2
    while slug in taken:
        slug = '%s-%d' % (base, n)
        n += 1
    taken.add(slug)
    return slug

def import_bookmarks(path, fallback='tools', dry_run=False):
    if not os.path.exists(path):
        print(f"No such file: {path}")
        sys.exit(1)
    parser = BookmarkParser()
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        parser.feed(f.read())

    data = load_yaml('link_library.yml')
    if not isinstance(data, dict) or not data:
        data = {'groups': LINK_GROUPS, 'links': []}
    data.setdefault('groups', LINK_GROUPS)
    data.setdefault('links', [])

    known = {url_key(l['url']) for l in data['links']}
    taken = {l['id'] for l in data['links']}
    added, skipped, dupes = [], {}, 0

    for item in parser.items:
        url = clean_url(item['url'])
        ok, reason = _is_public(url)
        if not ok:
            skipped.setdefault(reason, []).append(item['title'] or url)
            continue
        key = url_key(url)
        if key in known:
            dupes += 1
            continue
        known.add(key)
        folder = tuple(p for p in item['folder'] if p.lower() not in ('bookmarks bar', 'bookmarks menu', 'other bookmarks'))
        group = FOLDER_GROUPS.get(folder)
        title, note = tidy_title(item['title'], url)
        kind = classify(url, title, group or fallback)
        if group is None:
            # An unmapped folder: let the kind decide rather than dumping
            # everything into one bucket.
            group = 'funding' if kind == 'position' else fallback
        entry = {
            'id': link_slug(title, url, taken),
            'title': title,
            'url': url,
            'group': group,
            'kind': kind,
            'site': _host(url).replace('www.', ''),
        }
        if note:
            entry['note'] = note
        if item['added']:
            try:
                entry['added'] = datetime.date.fromtimestamp(int(item['added'])).isoformat()
            except (ValueError, OverflowError, OSError):
                pass
        added.append(entry)

    print(f"Parsed {len(parser.items)} bookmarks from {os.path.basename(path)}")
    print(f"  new: {len(added)}   already present: {dupes}   skipped: {sum(len(v) for v in skipped.values())}")
    for reason, titles in sorted(skipped.items()):
        print(f"  skipped ({reason}): {len(titles)}")
        for t in titles[:40]:
            print(f"      - {t[:76]}")
    by_group = {}
    for e in added:
        by_group[e['group']] = by_group.get(e['group'], 0) + 1
    for g, n in sorted(by_group.items(), key=lambda kv: -kv[1]):
        print(f"  -> {g}: {n}")

    if dry_run:
        print("Dry run: nothing written.")
        return

    data['links'] = data['links'] + added
    save_yaml('link_library.yml', data,
              header=leading_comment('link_library.yml') or LINK_LIBRARY_HEADER, width=92)
    print(f"{len(data['links'])} links in _data/link_library.yml")

def add_link_interactive():
    data = load_yaml('link_library.yml')
    if not isinstance(data, dict) or not data:
        data = {'groups': LINK_GROUPS, 'links': []}
    groups = [g['id'] for g in data.get('groups', LINK_GROUPS)]
    kinds = ['lab', 'code', 'reading', 'dataset', 'people', 'course', 'position', 'talk', 'tool']

    print("\n--- New link ---")
    url = clean_url(ask("URL", required=True))
    ok, reason = _is_public(url)
    if not ok:
        print(f"  Refusing: {reason}. This page is public.")
        sys.exit(1)
    if url_key(url) in {url_key(l['url']) for l in data['links']}:
        print("  Already in the library.")
        sys.exit(0)
    title = ask("Title", required=True)
    group = ask_choice("Group", groups, groups[0])
    kind = ask_choice("Kind", kinds, classify(url, title, group))
    note = ask("One line of context (optional)")

    entry = {
        'id': link_slug(title, url, {l['id'] for l in data['links']}),
        'title': title,
        'url': url,
        'group': group,
        'kind': kind,
        'site': _host(url).replace('www.', ''),
    }
    if note:
        entry['note'] = note
    entry['added'] = datetime.date.today().isoformat()
    data['links'].append(entry)
    save_yaml('link_library.yml', data,
              header=leading_comment('link_library.yml') or LINK_LIBRARY_HEADER, width=92)
    print(f"Added '{title}' to {group}.")

def run_server():
    print("Starting Jekyll Local Server...")
    try:
        subprocess.run(["bundle", "exec", "jekyll", "serve", "--livereload", "--host", "0.0.0.0", "--port", "4000"], cwd=BASE_DIR)
    except KeyboardInterrupt:
        print("\nStopping server.")
    except Exception as e:
        print(f"Failed to start server: {e}")

def main():
    parser = argparse.ArgumentParser(description="Md Selim Sarowar's Portfolio Codebase Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Add news command
    parser_news = subparsers.add_parser('add-news', help="Add a news update item")
    parser_news.add_argument('--text', required=True, help="News text (HTML allowed)")
    parser_news.add_argument('--date', help="Date label (e.g., 'July 2026')")

    # Add pub command
    subparsers.add_parser('add-pub', help="Interactively add a new publication")

    # Add project command
    subparsers.add_parser('add-project', help="Interactively add a new project")

    # Add idea command
    subparsers.add_parser('add-idea', help="Interactively log a research idea")

    # Link library commands
    parser_bm = subparsers.add_parser('import-bookmarks', help="Merge a browser bookmarks export into the link library")
    parser_bm.add_argument('--file', required=True, help="Path to the exported bookmarks HTML file")
    parser_bm.add_argument('--group', default='tools', help="Group for links whose folder is not mapped")
    parser_bm.add_argument('--dry-run', action='store_true', help="Report what would be imported, write nothing")

    subparsers.add_parser('add-link', help="Add a single link to the library")

    # Serve command
    subparsers.add_parser('serve', help="Run the local Jekyll dev server")

    args = parser.parse_args()

    if args.command == 'add-news':
        add_news_item(args.text, args.date)
    elif args.command == 'add-pub':
        add_publication_interactive()
    elif args.command == 'add-project':
        add_project_interactive()
    elif args.command == 'add-idea':
        add_idea_interactive()
    elif args.command == 'import-bookmarks':
        import_bookmarks(args.file, fallback=args.group, dry_run=args.dry_run)
    elif args.command == 'add-link':
        add_link_interactive()
    elif args.command == 'serve':
        run_server()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
