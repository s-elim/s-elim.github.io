#!/usr/bin/env python3
import os
import sys
import datetime
import argparse
import subprocess
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
    elif args.command == 'serve':
        run_server()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
