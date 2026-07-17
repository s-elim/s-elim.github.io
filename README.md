# 🌌 Md Selim Sarowar · Personal & Research Portfolio

[![Live Portfolio](https://img.shields.io/badge/Live_Portfolio-00C853?style=for-the-badge&logo=google-chrome&logoColor=white)](https://s-elim.github.io/)
[![Google Scholar](https://img.shields.io/badge/Google_Scholar-4285F4?style=for-the-badge&logo=google-scholar&logoColor=white)](https://scholar.google.com/citations?user=dE-Jp50AAAAJ&hl=en)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/selimsarowar)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:selim.sarowar.cve@gmail.com)

Welcome to the official repository for my academic and research portfolio website. This site is built using **Jekyll**, styled with customized **SASS**, and deployed automatically via **GitHub Pages**.

---

## 🎓 Academic Profile & Research Focus

I am an **M.Sc. (Research) Student** in Computer Vision & AI at the **Advanced Visual Intelligence Lab (AVI)**, Yeungnam University, South Korea, funded by the prestigious **Global Korea Scholarship (GKS)**.

*   🏆 **Academic Standing**: Ranked 1st / Top 1 (Perfect CGPA **4.5 / 4.5**)
*   🤖 **Primary Focus**: Embodied AI & Agentic Robotics (VLA Models, Latent World Models)
*   👁️ **Core Competencies**: 3D Computer Vision (6D Pose Estimation, 3D Gaussian Splatting)

---

## 📂 Repository Directory Structure

```bash
├── _data/                 # Core site database (YML)
│   ├── publications.yml   # Papers, Patents, Preprints, and Workshops
│   ├── experience.yml     # Research & Professional work experience
│   ├── fun_time.yml       # Activities, Bootcamps, and Invited Talks
│   ├── projects.yml       # Highlighted projects
│   └── profiles.yml       # Social links, sidebar credentials, and email
├── _includes/             # Jekyll HTML templates
│   ├── pub-card.html      # Renders individual publication items
│   └── footer.html        # Site footer (includes visitor counter widget)
├── _pages/                # Layout structures for main subpages
│   ├── about.md           # Biography introduction popup
│   ├── publications.md    # Publications page with search & filters
│   └── experience.html    # Work experience & education timelines
├── _sass/                 # Styling architecture (SCSS)
│   └── theme/
│       ├── _cards.scss    # Publication card layouts
│       └── _footer.scss   # Footer styling & glow animations
└── scripts/               # Developer automation scripts
    └── manage.py          # Interactive CLI helper for managing content
```

---

## 🛠️ Developer Cookbook (Local Setup & Management)

### 1. Run the Portfolio Locally
Make sure you have Ruby, Bundler, and NodeJS installed, then run:
```bash
# Clean previous builds
bundle clean

# Install dependencies
bundle install

# Start local server with live reloading
bundle exec jekyll serve
```
Your site will be served locally at `http://localhost:4000`.

### 2. Add New Content via CLI
Use the interactive Python CLI helper to add new items to the portfolio easily without manual YAML editing:
```bash
# Launch the manager CLI
python scripts/manage.py
```
Options available:
*   `1`: Add a Publication (Conference, Journal, Patent, Preprint)
*   `2`: Add a Project
*   `3`: Add an Activity (Invited Talk, Bootcamp, Reviewing Services)

---

## 🗺️ Repo Visitors

[![Flag Counter](https://s05.flagcounter.com/count2/AbBN/bg_FFFFFF/txt_000000/border_CCCCCC/columns_8/maxflags_100/viewers_0/labels_0/pageviews_1/flags_0/percent_0/)](https://info.flagcounter.com/AbBN)
