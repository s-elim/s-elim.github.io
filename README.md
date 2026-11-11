# s-elim.github.io

Source of Md Selim Sarowar's academic homepage: **https://s-elim.github.io/**

A Jekyll site served by GitHub Pages from the `master` branch. All page content lives in YAML files under `_data/`, so most updates are a data edit, not a template edit.

[Google Scholar](https://scholar.google.com/citations?user=zzX9GscAAAAJ&hl=en) | [LinkedIn](https://www.linkedin.com/in/selimsarowar) | [ResearchGate](https://www.researchgate.net/profile/Selim_Sarowar)

For field-by-field notes on every data file, see [PORTFOLIO_COOKBOOK.md](PORTFOLIO_COOKBOOK.md).

## Pages

| URL | Source | Data |
|---|---|---|
| `/` | `_pages/about.md` | `profiles.yml`, `news.yml`, `publications.yml`, `awards.yml`, `fun_time.yml`, `reviewing.yml`, plus teasers from `research_ideas.yml`, `link_library.yml`, `conferences.yml`, `openings.yml`, `university_rankings.yml` |
| `/experience/` | `_pages/experience.html` | `experience.yml`, `education.yml`, `teaching.yml`, `reviewing.yml` |
| `/projects/` | `_pages/skills&projects.html` | `projects.yml` |
| `/publications/` | `_pages/publications.md` | `publications.yml` |
| `/research-ideas/` | `_pages/research-ideas.html` | `research_ideas.yml`, `link_library.yml`, `deep_dives.yml` |
| `/deadlines/` | `_pages/deadlines.html` | `conferences.yml` (synced monthly) |
| `/journals/` | `_pages/journals.html` | `journals.yml` |
| `/phd-postdoc-openings/` | `_pages/phd-postdoc-openings.html` | `openings.yml` (synced daily) |
| `/desk/` | `_pages/desk.html` | Google Apps Script backend, see `workers/desk/README.md` |
| `/notes/...` | `_pages/atlas.html`, `vjepa.html`, `vjepa-teardown.html`, `cosmos3.html`, `piml.html`, `language-eats-robotics.html` | explainers in `_includes/` |
| `/learn/mujoco/` | `learn/mujoco/index.html` | static course app, not processed by the Jekyll layouts |

The data column comes from the `site.data.*` references in each page. `assets/data/search-index.json` (the Cmd/Ctrl-K search) also reads most data files.

## Repository layout

```text
├── _config.yml              # site settings, plugins, contact and desk endpoints
├── _config.dev.yml          # local overrides (localhost URL, analytics off)
├── _data/                   # all site content (YAML)
│   ├── publications.yml     # papers, patents, preprints, workshops
│   ├── profiles.yml         # name, links, sidebar credentials
│   ├── news.yml             # home page updates
│   ├── experience.yml, education.yml, teaching.yml, reviewing.yml, awards.yml
│   ├── projects.yml, fun_time.yml, collaborations.yml
│   ├── research_ideas.yml, link_library.yml, deep_dives.yml
│   ├── conferences.yml      # written by the deadlines sync
│   ├── openings.yml         # written by the openings sync
│   └── journals.yml, university_rankings.yml, navigation.yml, image_sizes.yml, ...
├── _pages/                  # one file per page (see the table above)
├── _layouts/                # default, home, archive, desk, frozen
├── _includes/               # head, nav, footer, pub-card, explainers
├── _sass/theme/             # site styles, one partial per component
├── assets/                  # main.scss, main.js, desk app, fonts, generated JSON
├── images/                  # figures and thumbnails (WebP)
├── files/                   # PDFs served as-is
├── learn/mujoco/            # "MuJoCo, Zero to Research" course: lessons, browser labs, Python package
├── scripts/
│   ├── manage.py            # content CLI (add-pub, add-news, openings, deadlines, serve, ...)
│   ├── deadlines/           # conference deadline updater
│   ├── openings/            # PhD and postdoc openings crawler
│   ├── optimize_images.py   # convert images to WebP and rewrite references
│   ├── build_university_rankings.py
│   └── build_dive_artifacts.py
├── tests/                   # tests for the two sync pipelines
├── workers/
│   ├── contact/             # Cloudflare Worker behind the footer message form
│   └── desk/                # Google Apps Script backend for /desk/
└── .github/workflows/       # deadlines_sync.yml, openings_sync.yml
```

## Run the site locally

You need Ruby and Bundler. The `Gemfile` pulls in the `github-pages` gem, which carries Jekyll and every plugin listed in `_config.yml`.

```bash
bundle install
bundle exec jekyll serve --livereload --config _config.yml,_config.dev.yml
```

The site is served at `http://localhost:4000`. Restart the server after editing `_config.yml`; Jekyll does not reload it.

`python3 scripts/manage.py serve` starts the same server without the dev overrides.

## Update content

Edit the YAML file in `_data/` directly, or use the CLI (needs `pyyaml`):

```bash
python3 scripts/manage.py add-pub            # interactive: new entry in _data/publications.yml
python3 scripts/manage.py add-project        # interactive: _data/projects.yml
python3 scripts/manage.py add-news --text "..." [--date "July 2026"]
python3 scripts/manage.py add-idea           # interactive: _data/research_ideas.yml
python3 scripts/manage.py add-link           # interactive: _data/link_library.yml
python3 scripts/manage.py import-bookmarks --file bookmarks.html [--dry-run]
```

**Publications.** `_data/publications.yml` is the single source for the publications page, the home page research arc and the generated BibTeX. Keep `venue` and `status` exactly as they should appear. The schema is documented in the comment at the top of that file.

**Images.** Put new figures in `images/`, then run:

```bash
python3 scripts/optimize_images.py --dry-run   # report only
python3 scripts/optimize_images.py             # write WebP derivatives, rewrite references, delete originals
```

## Automated data syncs

Two GitHub Actions workflows commit to `master` on a schedule. Both use free public sources and no API keys.

| Workflow | Schedule | Command | Writes |
|---|---|---|---|
| `deadlines_sync.yml` | 1st of each month, 18:00 UTC | `scripts/manage.py deadlines run` | `_data/conferences.yml`, `_pages/deadlines.html` |
| `openings_sync.yml` | daily, 19:00 UTC | `scripts/manage.py openings run` | `_data/openings.yml` |

Run them by hand, with the same dependencies the workflows use:

```bash
uv run --with pyyaml --with httpx --with beautifulsoup4 python3 scripts/manage.py deadlines run --dry-run
uv run --with pyyaml --with pydantic --with httpx --with beautifulsoup4 python3 scripts/manage.py openings run --dry-run
```

Pull before you push: the bots commit to the same branch.

## Tests

```bash
# deadlines updater (the command the workflow runs before it writes)
uv run --with pytest --with pyyaml --with httpx --with beautifulsoup4 pytest tests/test_deadlines.py -q

# openings pipeline
uv run --with pytest --with pyyaml --with pydantic --with httpx --with beautifulsoup4 pytest tests/test_openings.py -q

# workers (Node.js)
cd workers/contact && npm test
cd workers/desk && npm test
```

## MuJoCo course

`learn/mujoco/` is a self-contained static app: `index.html`, `course.json`, Markdown lessons in `lessons/`, browser labs in `js/`, and the Python companion package `mjcourse` in `code/`.

```bash
cd learn/mujoco/code
pip install -e ".[dev]"      # Python 3.10 or newer; pins mujoco==3.14.0
pytest

cd ..
python tools/sync_code.py       # refresh code blocks in the lessons from code/
python tools/check_content.py   # static checks; run before every publish
```

## Deploy

Push to `master`. GitHub Pages builds and publishes the site; there is no build workflow in this repository.

```bash
git pull --rebase origin master
git add <files>
git commit -m "docs: add new paper to publications"
git push origin master
```

Publishing is public and immediate. Preview locally first.

## License

The site is built on the Minimal Mistakes Jekyll theme. [LICENSE](LICENSE) is the theme's MIT license (Copyright (c) 2016 Michael Rose).

## Visitors

[![Flag Counter](https://s05.flagcounter.com/count2/AbBN/bg_FFFFFF/txt_000000/border_CCCCCC/columns_8/maxflags_100/viewers_0/labels_0/pageviews_1/flags_0/percent_0/)](https://info.flagcounter.com/AbBN)
