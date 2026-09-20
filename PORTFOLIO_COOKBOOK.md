# Portfolio Cookbook & Maintenance Guide 🍳

This cookbook provides guides, shortcuts, and commands to manage, update, and run your academic portfolio website.

---

## 🛠️ Portfolio Management Utility (`scripts/manage.py`)

A custom Python script has been added to `scripts/manage.py` to automate common updates. To use it, make sure you are in your active Python environment where `pyyaml` is installed.

### 1. Run the Local Development Server
Starts the Jekyll server with hot-reloading enabled.
```bash
./scripts/manage.py serve
# Or: python3 scripts/manage.py serve
```
*The website will be hosted locally at `http://localhost:4000/`.*

### 2. Add a Publication (Interactive)
Prompts you for all metadata, sets up tags (Year, Venue, Rank, Impact), links, and custom BibTeX, then formats and inserts it in the correct year order inside `_data/publications.yml`.
```bash
./scripts/manage.py add-pub
```

### 3. Add a Project (Interactive)
Prompts you to add a new **Bootcamp**, **Research Project**, or **Industry Collaboration**, handles point list formats, and saves to `_data/projects.yml`.
```bash
./scripts/manage.py add-project
```

### 4. Log a Research Idea (Interactive)
Prompts for the theme, status, priority, source, open questions and next actions, then prepends the entry to `_data/research_ideas.yml`. The schema comment at the top of that file is preserved on save.
```bash
./scripts/manage.py add-idea
```
*The entry renders on `/research-ideas/` as a card and as a node on the mind map, and is reachable at `/research-ideas/#idea-<id>`.*

### 5. Import Bookmarks into the Link Library
Merges a browser bookmarks export (Chrome: Bookmark manager > Export bookmarks) into `_data/link_library.yml`. Existing entries and hand edits are kept, new URLs are appended, duplicates are dropped, tracking parameters are stripped, and anything behind a login or inside a private workspace is skipped and reported.
```bash
./scripts/manage.py import-bookmarks --file ../bookmarks_9_21_26.html --dry-run   # report only
./scripts/manage.py import-bookmarks --file ../bookmarks_9_21_26.html
./scripts/manage.py add-link                                                      # one link, interactively
```
*Folder mapping: `Robo Labs` to Robotics Labs, `Robo Labs/Benchmark` to Benchmarks, `CV Labs` to Computer Vision Labs, `Scientists` to Researchers. Anything else lands in Tools, or in Funding when the link looks like a job or fellowship call. Change `FOLDER_GROUPS` in `scripts/manage.py` to add a mapping.*

### 6. Add a News/Update Item
Quickly prepends a new update to the home page timeline modal.
```bash
./scripts/manage.py add-news --text "Paper on VLA models accepted at <strong>CVPR'27</strong>! Check project page <a href='https://example.com' target='_blank'>here</a>."
```
*Note: You can specify a custom date (e.g. `July 2026`) using the optional `--date` flag. Defaults to the current Month & Year.*

---

## 📂 Content Data Guide (`_data/`)

The website is fully data-driven. You can update any page content by editing the corresponding YAML file in the `_data/` folder:

### 📖 `publications.yml`
List of research publications.
* **Fields**:
  * `title`: Title of the paper.
  * `authors`: Full authors list (use `*` for corresponding author, `†` for co-first authors).
  * `venue`: Full name of the conference or journal.
  * `venue_short`: Abbreviation (e.g. `IROS'27` or `BMVC'26`).
  * `year`: Grouping year (4 digits).
  * `type`: `conference` | `journal` | `preprint` | `workshop`.
  * `flagship`: `vision` | `robotics` (renders a custom flagship badge).
  * `rank`: CORE Rank (e.g. `A*`, `A`).
  * `impact`: Journal impact details (e.g. `SCIE-Q1, IF: 4.2`, renders strong text).
  * `image`: Path to paper thumbnail (e.g., `/images/my_paper.png`). Clicking it opens a zoomable lightbox overlay.
  * `url`: Link to the project page or paper.
  * `bibtex`: Optional custom BibTeX string. If omitted, Jekyll automatically generates one.
  * `links`: Additional buttons (PDF, Code, Project Page).

### 💼 `education.yml`
Education details rendered on the **Experience** page.
* **Fields**:
  * `institution`: University name with country flag element (e.g., `Yeungnam University, South Korea <span class="fi fi-kr"></span>`).
  * `date`: Duration.
  * `current`: Set to `true` to display a pulsing green "Current" badge.
  * `degrees`: List of degrees (supports HTML `<br>` to break lines).
  * `thesis`: Title of your thesis (rendered with a book icon).
  * `extra`: Advisor details (rendered with a teacher icon).

### 🏢 `experience.yml`
Research and professional work experience.
* **Fields**:
  * `role`: Your position title.
  * `org`: Organization name.
  * `date`: Duration (displays as a clean, gray text-pill).
  * `current`: Set to `true` to highlight as a current role.
  * `points`: Detailed bullets outlining achievements and projects.

### 🌐 `collaborations.yml`
Academic collaborations rendered on the **Experience** page (interactive shimmer-on-hover cards).
* **Fields**:
  * `lab`: Lab/group name.
  * `institution`: Institution name with country flag element (same format as `education.yml`).
  * `type`: Short badge text (e.g. `Joint Research`).

### 🎓 `teaching.yml`
Courses taught or assisted.
* **Fields**:
  * `course`: Course code/name.
  * `role`: `Instructor` (blue tag background) or `Teaching Assistant` (blue tag border).
  * `university`: School name.
  * `date`: Semester/Duration.

### 💡 `research_ideas.yml`
Capture log behind `/research-ideas/`, reached from the home page hero chip and from Cmd/Ctrl-K, deliberately not in the navigation.
* **`themes`**: the ring of the mind map and the colour of every card.
  * `id`, `label`, `icon` (Font Awesome solid class), `color` (hex), `blurb`.
  * Order in the file is the order clockwise around the map. Adding a theme needs no CSS: the colour is read from YAML.
* **`ideas`** (newest first):
  * `id`: stable slug, used by the anchor, the map node and `related`. Never rename one.
  * `theme` / `also`: primary theme, plus secondary themes drawn as dashed edges.
  * `status`: `spark` | `shaping` | `active` | `parked` | `shipped`.
  * `priority` 1-5, `effort` and `risk` (`low` | `medium` | `high`), `added` (YYYY-MM-DD).
  * `summary`, `why`, `angle`: what it is, the gap it addresses, and your own attack including its cost.
  * `facts`: label/value pairs read from the source. `questions`, `next`: lists.
  * `source`: `kind` (`linkedin` | `arxiv` | `paper` | `talk` | `lab` | `self` | `web`), `author`, `label`, `url`, `captured`.
  * `links`, `connects`, `related`, `tags`, `note`.
* The page is a working log, not a publication list. Publication status stays in `publications.yml`.

### 🔖 `link_library.yml`
Directory rendered below the idea board on `/research-ideas/`. Generated by `import-bookmarks`, safe to edit by hand.
* **`groups`**: sections in display order, each with `id`, `label`, `icon`, `color`, `blurb`.
* **`links`**: `id` (stable slug and anchor), `title`, `url`, `group`, `kind`, `site`, optional `note`, `added`.
  * `kind` is `lab` | `code` | `reading` | `dataset` | `people` | `course` | `position` | `talk` | `tool`. It drives the row icon, set in `_research-ideas.scss` from the `.lk--<kind>` class, and the type filter.
  * Re-sorting a link is a one-word edit to its `group`. A re-import will not undo it: merging is keyed on the URL.

### 🏆 `awards.yml`
Scholarships, medals, and academic awards.
* **Fields**:
  * `title`: Award name.
  * `date`: Date/Semester.
  * `org`: Issuing body.
  * `desc`: Description of the award.

---

## 🎨 Layout & CSS Structures (`_sass/theme/`)

The website styling has been modularized:
* `_tokens.scss`: Color variables (including shiny gradients, backgrounds, and fonts).
* `_base.scss`: Reset styles, custom text, and flag alignment rules (`.fi`).
* `_cards.scss`: Project cards, publications, and layouts like `.project-double-grid`.
* `_timeline.scss`: Experience timelines, news timelines, and `.xp-pill` badge layouts.
* `_research-ideas.scss`: Idea cards and the SVG mind map. Theme colour arrives as `--idea-color`, so every tint is mixed from the YAML value.

---

## 🚀 Publishing Updates

To deploy changes to your live portfolio:

1. Edit the relevant file (or use `manage.py`).
2. Test changes locally using `./scripts/manage.py serve`.
3. Commit and push the updates:
   ```bash
   git add .
   git commit -m "update: add new paper to publications"
   git push origin master
   ```
