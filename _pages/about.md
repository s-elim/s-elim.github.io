---
permalink: /
layout: home
title: Home
description: "Md Selim Sarowar: M.Sc. student in Computer Vision & AI at Yeungnam University (GKS Scholar). Research in 3D computer vision, 6D pose estimation, vision-language-action models, world models, and agentic robotics toward physical AGI."
redirect_from:
  - /about/
  - /about.html
---

{% assign p = site.data.profiles %}

<section class="hero reveal">
  <img class="hero__avatar" src="{{ '/images/' | append: p.avatar | relative_url }}" alt="{{ p.name }}" width="200" height="200">
  <div class="hero__intro">
    <h1 class="hero__name">{{ p.name }}</h1>
    <span class="hero__role">M.Sc. Student · 3D Computer Vision &amp; Physical AI · Advanced Visual Intelligence Lab</span>
    <p class="hero__availability"><a class="chip chip--open" href="https://mail.google.com/mail/?view=cm&amp;fm=1&amp;to={{ p.email }}&amp;su=Research%20collaboration%20%2F%20PhD%20opportunity" target="_blank" rel="noopener" title="Email me about a collaboration or PhD opportunity"><i class="fas fa-handshake" aria-hidden="true"></i> Open to research collaborations &amp; PhD opportunities <span class="chip__cta"><i class="fas fa-envelope" aria-hidden="true"></i> Get in touch <i class="fas fa-arrow-right" aria-hidden="true"></i></span></a></p>
    <div class="hero__chips">
      <span class="chip">Causal Learning</span>
      <span class="chip">Spatial Intelligence</span>
      <span class="chip">Self Modeling</span>
      <span class="chip">VLAs</span>
      <span class="chip">World Models</span>
      <span class="chip chip--long">Joint Embedding Predictive Architecture (V-JEPA)</span>
      <span class="chip">Agentic Robotics</span>
      <span class="chip">Robot Learning</span>
      <span class="chip">5D AI Robotics</span>
    </div>
    <div style="margin-bottom: 1.15rem; display: flex; flex-wrap: wrap; gap: 0.6rem 1.2rem; align-items: center;">
      <button type="button" class="js-modal-open" data-modal-target="#about-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-user-circle" aria-hidden="true"></i> Click to read about me <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
      </button>
      <span class="text-muted" style="font-size: 0.85rem; user-select: none;">|</span>
      <button type="button" class="js-modal-open" data-modal-target="#updates-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-bullhorn" aria-hidden="true"></i> Click to see updates <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
      </button>
      <span class="text-muted" style="font-size: 0.85rem; user-select: none;">|</span>
      <a href="#deadlines" class="js-dl-jump" style="text-decoration: none; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-stopwatch" aria-hidden="true"></i> AI Conference Deadlines <span id="deadlines-next-badge"></span> <i class="fas fa-arrow-down" aria-hidden="true" style="font-size: 0.9em;"></i>
      </a>
      <span class="text-muted" style="font-size: 0.85rem; user-select: none;">|</span>
      <button type="button" class="js-modal-open" data-modal-target="#journals-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-book-open" aria-hidden="true"></i> Top Journals (Robotics &amp; Vision) <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
      </button>
      <span class="text-muted" style="font-size: 0.85rem; user-select: none;">|</span>
      <button type="button" class="js-modal-open" data-modal-target="#rankings-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-trophy" aria-hidden="true"></i> World University Rankings (THE &amp; QS Top 400) <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
      </button>
    </div>
    <div class="hero__actions">
      <a class="btn btn--strong" href="{{ p.cv_url }}" target="_blank" rel="noopener"><i class="fas fa-file-alt" aria-hidden="true"></i> View CV</a>
      <button class="btn btn--ghost js-copy-email" type="button" data-email="{{ p.email }}" title="Copy email address to clipboard"><i class="fas fa-copy" aria-hidden="true"></i> Copy Email</button>
      <a class="btn btn--ghost" href="https://mail.google.com/mail/?view=cm&amp;fm=1&amp;to={{ p.email }}&amp;su=Contact%20via%20portfolio" target="_blank" rel="noopener"><i class="fas fa-envelope" aria-hidden="true"></i> Contact</a>
      <a class="btn btn--ghost" href="{{ p.scholar }}" target="_blank" rel="noopener"><i class="fas fa-graduation-cap" aria-hidden="true"></i> Scholar</a>
      <span class="hero__social">
        <a href="https://github.com/{{ p.github }}" target="_blank" rel="noopener" aria-label="GitHub"><i class="fab fa-github" aria-hidden="true"></i></a>
        <a href="https://www.linkedin.com/in/{{ p.linkedin }}" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="fab fa-linkedin" aria-hidden="true"></i></a>
        <a href="{{ p.researchgate }}" target="_blank" rel="noopener" aria-label="ResearchGate"><i class="fab fa-researchgate" aria-hidden="true"></i></a>
      </span>
    </div>
  </div>
</section>

<div class="quote-banner card reveal" id="quote-banner">
  <i class="fas fa-quote-right quote-banner__bg-icon" aria-hidden="true"></i>
  <div class="quote-banner__content">
    <div class="quote-banner__header">
      <span class="quote-banner__badge"><i class="fas fa-compass" aria-hidden="true"></i> Research Philosophy</span>
    </div>
    <blockquote class="quote-banner__quote">
      <p class="quote-banner__text">&ldquo;In research, there is no free lunch&mdash;<span class="quote-banner__highlight">achieve brilliance or step aside.</span>&rdquo;</p>
      <footer class="quote-banner__author">
        &mdash; <span class="quote-banner__author-name">Md Selim Sarowar</span>
      </footer>
    </blockquote>
  </div>
</div>

<section class="deadlines reveal" id="deadlines" aria-labelledby="deadlines-heading">
  <div class="deadlines__head">
    <h2 class="section-title deadlines__title" id="deadlines-heading">
      <i class="fas fa-stopwatch" aria-hidden="true"></i> AI Conference Deadlines
    </h2>
    <p class="deadlines__tagline">Live countdowns for the venues I track. <span class="deadlines__verified">Verified 31 Aug 2026</span></p>
  </div>

  <div class="deadlines__ticker" id="deadlines-ticker" aria-live="off">
    <span class="deadlines__ticker-label"><i class="fas fa-bolt" aria-hidden="true"></i> Next up</span>
    <span class="deadlines__ticker-body">Loading&hellip;</span>
  </div>

  <div class="deadlines__toolbar">
    <div class="deadlines__filters" role="group" aria-label="Filter by research domain">
      <button type="button" class="dl-pill is-active" data-filter="all"><span class="dl-pill__dot dl-pill__dot--all"></span> All</button>
      <button type="button" class="dl-pill" data-filter="robotics"><span class="dl-pill__dot dl-pill__dot--robotics"></span> Robotics</button>
      <button type="button" class="dl-pill" data-filter="vision"><span class="dl-pill__dot dl-pill__dot--vision"></span> Vision</button>
      <button type="button" class="dl-pill" data-filter="aiml"><span class="dl-pill__dot dl-pill__dot--aiml"></span> AI/ML</button>
    </div>

    <div class="deadlines__tools">
      <label class="dl-search" for="deadline-search">
        <i class="fas fa-search" aria-hidden="true"></i>
        <input type="search" id="deadline-search" placeholder="Search conferences" autocomplete="off" aria-label="Search conferences by name or location">
      </label>
      <div class="dl-segment" role="group" aria-label="Filter by CORE rank">
        <button type="button" class="dl-seg is-active" data-rank="all">All ranks</button>
        <button type="button" class="dl-seg" data-rank="A*">A*</button>
        <button type="button" class="dl-seg" data-rank="A">A</button>
      </div>
      <button type="button" class="dl-toggle is-active" id="deadline-open-only" aria-pressed="true">
        <i class="fas fa-door-open" aria-hidden="true"></i> Dated calls only
      </button>
      <div class="dl-segment dl-segment--view" role="group" aria-label="Change layout">
        <button type="button" class="dl-seg is-active" data-view="grid" aria-label="Card view"><i class="fas fa-th-large" aria-hidden="true"></i></button>
        <button type="button" class="dl-seg" data-view="list" aria-label="Compact list view"><i class="fas fa-list" aria-hidden="true"></i></button>
      </div>
    </div>
  </div>

  <div class="deadlines__grid" id="deadlines-grid">
    {% for c in site.data.conferences %}
    {% assign slug = c.name | slugify %}
    <article class="dl-card dl-card--{{ c.category }}" data-category="{{ c.category }}" data-rank="{{ c.rank | default: 'unranked' }}" data-name="{{ c.name }}" data-location="{{ c.location }}" id="conf-{{ slug }}">
      <div class="dl-card__glow" aria-hidden="true"></div>

      <header class="dl-card__head">
        <div class="dl-card__id">
          <h3 class="dl-card__name">{{ c.name }} <span class="dl-card__edition">{{ c.edition }}</span></h3>
          <p class="dl-card__place">{% if c.flag %}<span class="dl-card__flag">{{ c.flag }}</span> {% endif %}{{ c.location }}</p>
        </div>
        <div class="dl-card__marks">
          {% if c.rank %}<span class="dl-rank dl-rank--{% if c.rank == 'A*' %}astar{% else %}a{% endif %}">{{ c.rank }}</span>{% endif %}
          <span class="dl-cat dl-cat--{{ c.category }}">
            {% if c.category == 'robotics' %}<i class="fas fa-robot" aria-hidden="true"></i>{% elsif c.category == 'vision' %}<i class="fas fa-eye" aria-hidden="true"></i>{% else %}<i class="fas fa-brain" aria-hidden="true"></i>{% endif %}
          </span>
        </div>
      </header>

      <div class="dl-card__clock">
        <p class="dl-card__stage">&mdash;</p>
        <div class="dl-card__count" aria-live="off"><span class="dl-card__count-main">&mdash;</span></div>
        <div class="dl-card__bar" aria-hidden="true"><span class="dl-card__bar-fill"></span></div>
      </div>

      <ol class="dl-card__timeline">
        {% for t in c.timeline %}
        <li class="dl-stage" data-date="{{ t.date }}"{% if t.time %} data-time="{{ t.time }}"{% endif %}{% if t.tz %} data-tz="{{ t.tz }}"{% endif %}>
          <span class="dl-stage__dot" aria-hidden="true"></span>
          <span class="dl-stage__label">{{ t.label }}</span>
          <span class="dl-stage__date">
            {%- if t.date == 'tba' -%}TBA{%- else -%}{{ t.date | date: "%b %-d, %Y" }}{%- endif -%}
          </span>
        </li>
        {% endfor %}
      </ol>

      <footer class="dl-card__foot">
        <span class="dl-card__dates">{% if c.dates %}<i class="fas fa-calendar-alt" aria-hidden="true"></i> {{ c.dates }}{% endif %}</span>
        <button type="button" class="dl-card__more js-dl-more" aria-expanded="false" aria-controls="conf-{{ slug }}-details">Details <i class="fas fa-chevron-down" aria-hidden="true"></i></button>
      </footer>

      <div class="dl-card__details" id="conf-{{ slug }}-details" hidden>
        {% if c.note %}<p class="dl-card__note"><i class="fas fa-info-circle" aria-hidden="true"></i> {{ c.note }}</p>{% endif %}
        <dl class="dl-card__meta">
          {% if c.dates %}<div><dt>Conference</dt><dd>{{ c.dates }}</dd></div>{% endif %}
          <div><dt>Location</dt><dd>{% if c.flag %}{{ c.flag }} {% endif %}{{ c.location }}</dd></div>
          {% if c.rank %}<div><dt>CORE rank</dt><dd>{{ c.rank }}</dd></div>{% endif %}
        </dl>
        {% if c.website %}<a class="dl-card__link" href="{{ c.website }}" target="_blank" rel="noopener"><i class="fas fa-external-link-alt" aria-hidden="true"></i> Call for papers</a>{% endif %}
      </div>
    </article>
    {% endfor %}
  </div>

  <p class="deadlines__empty" id="deadlines-empty" hidden>No conference matches those filters.</p>

  <p class="deadlines__foot">
    <i class="fas fa-info-circle" aria-hidden="true"></i>
    Dates are checked against official calls for papers and the
    <a href="https://github.com/ccfddl/ccf-deadlines" target="_blank" rel="noopener">ccf-deadlines</a> dataset.
    Always confirm on the conference site before submitting.
  </p>
</section>

<div class="modal" id="about-modal" role="dialog" aria-modal="true" aria-labelledby="about-modal-title">
  <div class="modal__dialog">
    <div class="modal__head">
      <h3 class="modal__title" id="about-modal-title"><i class="fas fa-user" aria-hidden="true"></i> About</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close about popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body">
<p>I am pursuing an <strong>M.Sc. in Computer Vision &amp; AI</strong> at <a href="http://www.ynu.kr/_english/main/index.php" target="_blank" rel="noopener">Yeungnam University (YU)</a>, where I am maintaining a perfect <strong>CGPA of 4.5/4.5 (Ranked 1st / Top 1)</strong>. I am a <a href="https://www.studyinkorea.go.kr/" target="_blank" rel="noopener">Global Korea Scholarship (GKS)</a> scholar funded by NIIED, with additional support from the <strong>RLRC &amp; RISE</strong> industry-collaboration projects. I am a member of the <a href="https://avilabyu.wixsite.com/avil" target="_blank" rel="noopener">Advanced Visual Intelligence Lab</a>, supervised by <a href="https://scholar.google.com/citations?user=3TptC38AAAAJ&hl=en" target="_blank" rel="noopener">Prof. Sungho Kim</a>.</p>

<p>My research focuses on <strong>3D computer vision &amp; spatial intelligence, 6D pose estimation, vision-language-action (VLA) models, world models, and agentic robotics</strong> for robot manipulation. I aim to build embodied agents capable of perceiving, reasoning, and acting within the physical world, working toward <strong>physical AGI</strong>. My contributions in these areas include first-author publications at <strong>BMVC'26</strong> and in <strong>IEEE Access (SCIE-Q1)</strong>.</p>

<p>Before joining YU, I completed a one-year Korean Language &amp; Literature program at KLI under the GKS program, and spent a year as a full-time Research Assistant in the <a href="https://nthu-en.site.nthu.edu.tw/" target="_blank" rel="noopener">WCSP Lab at National Tsing Hua University</a>, Taiwan. I earned my B.Tech (Electronics &amp; Electrical Engineering) as an <a href="https://studyinindia.gov.in/" target="_blank" rel="noopener">SII Scholar</a> from the <a href="https://kiit.ac.in/" target="_blank" rel="noopener">Kalinga Institute of Industrial Technology (KIIT)</a>, and interned at <a href="https://www.iitr.ac.in/" target="_blank" rel="noopener">IIT Roorkee</a> on image processing for biomedical signals.</p>
    </div>
  </div>
</div>

<div class="modal" id="updates-modal" role="dialog" aria-modal="true" aria-labelledby="updates-modal-title">
  <div class="modal__dialog">
    <div class="modal__head">
      <h3 class="modal__title" id="updates-modal-title"><i class="fas fa-bullhorn" aria-hidden="true"></i> Updates</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close updates popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body">
      <div class="updates-card card" style="border: 0; box-shadow: none; padding: 0; background: transparent;">
        <div class="updates-card__scroll" id="updates-scroll" tabindex="0" aria-label="Updates timeline, scroll for older news" style="max-height: 28rem;">
          <ul class="timeline">
            {% for item in site.data.news %}
            <li class="timeline-item">
              <span class="timeline-item__date">{{ item.date }}</span>
              <p class="timeline-item__body">{{ item.text }}</p>
            </li>
            {% endfor %}
          </ul>
        </div>
        <div class="updates-card__hint" aria-hidden="true"><i class="fas fa-chevron-down"></i> Scroll for older updates</div>
      </div>
    </div>
  </div>
</div>

<div class="modal" id="journals-modal" role="dialog" aria-modal="true" aria-labelledby="journals-modal-title">
  <div class="modal__dialog" style="max-width: 52rem;">
    <div class="modal__head">
      <h3 class="modal__title" id="journals-modal-title"><i class="fas fa-book-open" aria-hidden="true"></i> Top SCIE-Q1 Journals in Robotics, Vision &amp; AI</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close journals popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body" style="padding-top: 0.5rem;">
      <div class="journal-filters" style="display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.75rem; align-items: center;">
        <span style="font-size: 0.8rem; font-weight: 600; color: var(--muted); margin-right: 0.2rem;">Filter by Domain:</span>
        <button type="button" class="journal-filter-btn active" data-filter="all">All (79)</button>
        <button type="button" class="journal-filter-btn" data-filter="robotics">🤖 Robotics (27)</button>
        <button type="button" class="journal-filter-btn" data-filter="vision">👁️ Vision &amp; Graphics (18)</button>
        <button type="button" class="journal-filter-btn" data-filter="aiml">🧠 AI &amp; Machine Learning (34)</button>
      </div>
      <div style="margin-bottom: 0.85rem;">
        <input type="text" id="journal-search" placeholder="Search journal name, abbreviation, or rank..." style="width: 100%; padding: 0.45rem 0.85rem; font-size: 0.82rem; font-family: var(--font-head); border: 1px solid var(--border); border-radius: 6px; background: var(--surface-2); color: var(--text-strong); outline: none;">
      </div>
      <div style="overflow-x: auto; max-height: 28rem; overflow-y: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.74rem; text-align: left;" id="journals-table">
          <thead>
            <tr style="border-bottom: 2px solid var(--border); color: var(--text-strong); position: sticky; top: 0; background: var(--surface); z-index: 2;">
              <th style="padding: 0.65rem 0.4rem; font-weight: 600; text-align: center; width: 2.2rem;">#</th>
              <th style="padding: 0.65rem 0.5rem; font-weight: 600;">Journal Name (Abbr.)</th>
              <th style="padding: 0.65rem 0.5rem; font-weight: 600;">Category</th>
              <th style="padding: 0.65rem 0.5rem; font-weight: 600; text-align: center;">Impact Factor</th>
              <th style="padding: 0.65rem 0.5rem; font-weight: 600; text-align: center;">Percentile Rank</th>
              <th style="padding: 0.65rem 0.5rem; font-weight: 600; text-align: center;">Quartile</th>
            </tr>
          </thead>
          <tbody>
            <tr class="category-header-row" data-category-header="robotics" style="background: var(--surface-2);">
              <td colspan="6" style="padding: 0.45rem 0.6rem; font-weight: 700; font-size: 0.72rem; color: var(--accent); letter-spacing: 0.03em; text-transform: uppercase;">
                <i class="fas fa-robot" aria-hidden="true"></i> Robotics SCIE-Q1 Journals
              </td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">1</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Science Robotics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(Sci. Robot.)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">25.5</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">2</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Journal of Manufacturing Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(JMS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">14.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">3</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Intelligent Vehicles <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE T-IV)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">14.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">4</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Robotics and Computer-Integrated Manufacturing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(RCIM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">12.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 2%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">5</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Advanced Engineering Informatics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(AEI)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">11.5</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">6</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Robotics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE T-RO)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">11.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">7</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Mechanical Systems and Signal Processing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(MSSP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">8</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Robotics and Automation Magazine <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE RAM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">9</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Intelligent Transportation Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE T-ITS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">10</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Automation Science and Engineering <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE T-ASE)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">11</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">The International Journal of Robotics Research <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IJRR)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 2%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">12</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Journal of Intelligent Manufacturing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(JIM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">13</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Automatic Control <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TAC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">14</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Instrumentation and Measurement <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TIM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">15</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Advanced Intelligent Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(Adv. Intell. Syst.)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">16</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE/ASME Transactions on Mechatronics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE/ASME T-MECH)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">17</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Automatica</td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">18</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Autonomous Robots <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(AURO)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">19</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Robotics and Autonomous Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(RAS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 15%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">20</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Soft Robotics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(SoRo)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">5.5</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">21</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Robotics and Automation Letters <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE RA-L)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">5.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">22</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Control Engineering Practice <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(CEP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">5.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">23</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Cognitive and Developmental Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TCDS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">24</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Human-Machine Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE THMS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">25</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Control Systems Technology <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TCST)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">26</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Journal of Field Robotics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(JFR)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 15%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="robotics">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">27</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Journal of Intelligent &amp; Robotic Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(JINT)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--robotics"><i class="fas fa-robot" aria-hidden="true" style="font-size: 0.75em;"></i> Robotics</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">3.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #f1f5f9; color: #334155; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 600; font-size: 0.68rem;">Top 20%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr class="category-header-row" data-category-header="vision" style="background: var(--surface-2);">
              <td colspan="6" style="padding: 0.45rem 0.6rem; font-weight: 700; font-size: 0.72rem; color: var(--accent); letter-spacing: 0.03em; text-transform: uppercase;">
                <i class="fas fa-eye" aria-hidden="true"></i> Computer Vision, Image Processing &amp; Graphics SCIE-Q1 Journals
              </td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">28</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Pattern Analysis and Machine Intelligence <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TPAMI)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">20.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">29</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Image Processing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TIP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">15.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">30</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Medical Image Analysis <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(MedIA)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">14.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">31</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">ACM Transactions on Graphics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(ACM TOG)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">13.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">32</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">ISPRS Journal of Photogrammetry and Remote Sensing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(ISPRS J. P&RS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">12.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">33</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Medical Imaging <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TMI)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">12.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">34</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Circuits and Systems for Video Technology <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TCSVT)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">35</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Signal Processing Magazine <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE SPM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">36</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">International Journal of Computer Vision <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IJCV)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">37</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Multimedia <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TMM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">38</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Geoscience and Remote Sensing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TGRS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">39</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Pattern Recognition <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(PR)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">40</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Journal of Selected Topics in Signal Processing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE JSTSP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.5</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">41</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Visualization and Computer Graphics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TVCG)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">42</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE/ACM Transactions on Audio, Speech, and Language Processing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE/ACM TASLP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">5.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">43</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Computer Vision and Image Understanding <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(CVIU)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 15%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">44</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Image and Vision Computing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IVC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">4.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 15%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="vision">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">45</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Signal Processing: Image Communication <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(SPIC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--vision"><i class="fas fa-eye" aria-hidden="true" style="font-size: 0.75em;"></i> Vision</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">3.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #f1f5f9; color: #334155; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 600; font-size: 0.68rem;">Top 20%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr class="category-header-row" data-category-header="aiml" style="background: var(--surface-2);">
              <td colspan="6" style="padding: 0.45rem 0.6rem; font-weight: 700; font-size: 0.72rem; color: var(--accent); letter-spacing: 0.03em; text-transform: uppercase;">
                <i class="fas fa-brain" aria-hidden="true"></i> General AI &amp; Machine Learning SCIE-Q1 Journals
              </td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">46</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Proceedings of the IEEE <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(Proc. IEEE)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">30.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">47</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">ACM Computing Surveys <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(ACM CSUR)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">30.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">48</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Nature Machine Intelligence <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(Nat. Mach. Intell.)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">29.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">49</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Artificial Intelligence Review <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(AIRE)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">18.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">50</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Information Fusion <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(INFUS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">17.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">51</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Evolutionary Computation <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TEVC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">15.9</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">52</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Artificial Intelligence <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(AIJ)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">14.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">53</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Knowledge and Data Engineering <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TKDE)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">11.6</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">54</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Cybernetics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE T-CYB)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">11.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">55</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Affective Computing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TAFFC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">11.3</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">56</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Fuzzy Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TFS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">57</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Computers in Industry <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(COMIND)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">10.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">58</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Industrial Informatics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TII)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 2%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">59</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Neural Networks and Learning Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TNNLS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 3%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">60</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Swarm and Evolutionary Computation <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(SWEVO)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.6</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">61</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Expert Systems with Applications <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(ESWA)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">62</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Engineering Applications of Artificial Intelligence <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(EAAI)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">9.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">63</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Mobile Computing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TMC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">64</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Internet of Things Journal <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE IoT-J)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 6%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">65</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Systems, Man, and Cybernetics: Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TSMC-S)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">66</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Transportation Research Part C: Emerging Technologies <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(TR-C)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">67</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Information Processing & Management <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IPM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">68</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Big Data <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TBD)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.1</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">69</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Knowledge-Based Systems <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(KBS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">8.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">70</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Applied Soft Computing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(ASOC)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">71</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Artificial Intelligence in Medicine <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(AIIM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.8</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">72</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Computational Intelligence Magazine <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE CIM)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 1%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">73</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Industrial Electronics <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TIE)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">74</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Cognitive Computation <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(Cogn. Comput.)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.4</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">75</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Neural Networks</td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">7.2</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">76</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Neurocomputing</td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.7</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">77</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">Information Sciences <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(INS)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 5%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">78</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Emerging Topics in Computational Intelligence <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TETCI)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">6.0</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 25%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-category="aiml">
              <td style="padding: 0.55rem 0.4rem; text-align: center; font-weight: 600; color: var(--muted);">79</td>
              <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: var(--text-strong);">IEEE Transactions on Signal Processing <span style="color: var(--muted); font-size: 0.8em; font-weight: 400;">(IEEE TSP)</span></td>
              <td style="padding: 0.55rem 0.5rem;"><span class="conf-tag conf-tag--aiml"><i class="fas fa-brain" aria-hidden="true" style="font-size: 0.75em;"></i> AI/ML</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center; font-weight: 700; color: var(--accent);">5.5</td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">Top 10%</span></td>
              <td style="padding: 0.55rem 0.5rem; text-align: center;"><span style="background: #e0f2fe; color: #0369a1; padding: 0.12rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.68rem;">SCIE-Q1</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div class="modal" id="rankings-modal" role="dialog" aria-modal="true" aria-labelledby="rankings-modal-title" data-rank-src="{{ '/assets/data/university-rankings.json' | relative_url }}">
  <div class="modal__dialog" style="max-width: 54rem;">
    <div class="modal__head">
      <h3 class="modal__title" id="rankings-modal-title"><i class="fas fa-trophy" aria-hidden="true"></i> World University Rankings &mdash; Top 400</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close university rankings popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body" style="padding-top: 0.5rem;">
      {% assign rk = site.data.university_rankings %}
      {% assign rk_keys = "the,qs" | split: "," %}
      <div class="rank-tags" role="tablist" aria-label="Ranking system">
        <span class="rank-tags__label">Ranking</span>
        {% for k in rk_keys %}{% assign src = rk[k] %}
        <button type="button" class="rank-tab{% if forloop.first %} active{% endif %}" data-rank-tab="{{ k }}" role="tab" aria-selected="{% if forloop.first %}true{% else %}false{% endif %}" aria-controls="rank-panel-{{ k }}">
          <i class="fas {% if k == 'the' %}fa-landmark{% else %}fa-globe-americas{% endif %}" aria-hidden="true"></i> {{ src.short }} <span class="rank-tab__year">&rsquo;{{ src.edition | slice: 2, 2 }}</span>
        </button>
        {% endfor %}
      </div>

      {% for k in rk_keys %}{% assign src = rk[k] %}
      {% if k == "the" %}{% assign other = rk.qs %}{% else %}{% assign other = rk.the %}{% endif %}
      <div class="rank-panel" id="rank-panel-{{ k }}" data-rank-panel="{{ k }}" role="tabpanel" data-rank-other="{{ other.short }}" data-rank-other-title="Position in the {{ other.name }} {{ other.edition }}"{% unless forloop.first %} hidden{% endunless %}>
        <p class="rank-meta">
          <strong>{{ src.name }} {{ src.edition }}</strong> &middot; published {{ src.published }} &middot; full table covers {{ src.total_ranked }}. Showing the top {{ src.count }} positions.
        </p>

        {% assign countries = src.entries | group_by: "country" | sort: "size" | reverse %}
        <div class="rank-tags rank-tags--country">
          <span class="rank-tags__label">Country</span>
          <div class="rank-chips" data-rank-countries="{{ k }}">
            <button type="button" class="rank-chip active" data-country="">All <span class="rank-chip__n">{{ src.count }}</span></button>
            {% for c in countries %}
            <button type="button" class="rank-chip" data-country="{{ c.name }}">{{ c.name }} <span class="rank-chip__n">{{ c.size }}</span></button>
            {% endfor %}
          </div>
          <button type="button" class="rank-more" data-rank-more="{{ k }}" aria-expanded="false">Show all {{ countries | size }} countries</button>
        </div>

        <div class="rank-toolbar">
          <input type="text" class="rank-search" data-rank-search="{{ k }}" placeholder="Search university or country&hellip;" aria-label="Search the {{ src.short }} {{ src.edition }} top 400">
          <span class="rank-count" data-rank-count="{{ k }}">Showing <b>{{ src.count }}</b> / {{ src.count }}</span>
        </div>
        <div class="rank-scroll">
          <table class="rank-table" data-rank-table="{{ k }}">
            <thead>
              <tr>
                <th style="text-align:center;">Rank</th>
                <th>University</th>
                <th>Country<span class="rank-th-full"> / Territory</span></th>
              </tr>
            </thead>
            <!-- Rows are fetched from assets/data/university-rankings.json on first
                 open: inlining 800 of them tripled the homepage DOM. -->
            <tbody>
              <tr class="rank-empty" hidden><td colspan="3">No university matches that filter.</td></tr>
              <tr class="rank-loading"><td colspan="3">Loading the {{ src.short }} {{ src.edition }} top {{ src.count }}&hellip;</td></tr>
            </tbody>
          </table>
        </div>
        <p class="rank-note">
          {{ src.note }} As published by <a href="{{ src.url }}" target="_blank" rel="noopener">{{ src.short }} {{ src.edition }}</a> &mdash; reproduced for reference; rankings remain the property of their publisher.
        </p>
      </div>
      {% endfor %}
    </div>
  </div>
</div>

<h2 class="section-title reveal"><i class="fas fa-lightbulb" aria-hidden="true"></i> Research Highlights</h2>
<div class="highlight-grid">
  <article class="highlight-card card reveal" data-delay="1">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/10-years-robotics-taxonomy.webp' | relative_url }}" data-caption="Physical AI &amp; Agentic Robotics: Embodied agents that plan and act in latent world models for robot manipulation, bridging perception, reasoning, and control toward physical AGI." aria-label="Zoom figure">
      {% include figure-img.html src="/images/10-years-robotics-taxonomy.webp" alt="Ten-year robotics taxonomy for physical AI and agentic robotics" sizes="(max-width: 700px) 92vw, 350px" %}
    </button>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">Physical AI &amp; Agentic Robotics</h3>
      <p class="highlight-card__desc">Embodied agents that plan and act in latent world models for robot manipulation, bridging perception, reasoning, and control toward physical AGI.</p>
      <div class="tag-list"><span class="tag">VLAs</span><span class="tag">World Models</span><span class="tag">Agentic Robotics</span><span class="tag">Causal Learning</span><span class="tag">Self Modeling</span><span class="tag">Human-Robot Interaction</span><span class="tag">5D AI Robotics</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="2">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/c3g-vm6d-architecture.webp' | relative_url }}" data-caption="3D Vision &amp; 6D Pose Estimation: Recovering full object pose and geometry from images and point clouds for spatially-grounded, robust scene understanding." aria-label="Zoom figure">
      {% include figure-img.html src="/images/c3g-vm6d-architecture.webp" alt="6D pose estimation architecture" sizes="(max-width: 700px) 92vw, 350px" %}
    </button>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">3D Vision &amp; 6D Pose Estimation</h3>
      <p class="highlight-card__desc">Recovering full object pose and geometry from images and point clouds for spatially-grounded, robust scene understanding.</p>
      <div class="tag-list"><span class="tag">3D Vision</span><span class="tag">6D Pose</span><span class="tag">Spatial Intelligence</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="3">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/3d-point-cloud-visualization.webp' | relative_url }}" data-caption="Perception &amp; Representation Learning: Learning transferable visual representations, from image denoising and autoencoders to point-cloud understanding for downstream 3D tasks." aria-label="Zoom figure">
      {% include figure-img.html src="/images/3d-point-cloud-visualization.webp" alt="Point cloud representation learning" sizes="(max-width: 700px) 92vw, 350px" %}
    </button>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">Perception &amp; Representation Learning</h3>
      <p class="highlight-card__desc">Learning transferable visual representations, from image denoising and autoencoders to point-cloud understanding for downstream 3D tasks.</p>
      <div class="tag-list"><span class="tag">Point Clouds</span><span class="tag">Representation Learning</span><span class="tag">Denoising</span></div>
    </div>
  </article>
</div>

<h2 class="section-title reveal"><i class="fas fa-award" aria-hidden="true"></i> Awards &amp; Honors</h2>
<div class="awards-carousel-container reveal">
  <button class="carousel-btn prev" aria-label="Previous Award" onclick="document.getElementById('awards-carousel').scrollBy({left: -370, behavior: 'smooth'})">
    <i class="fas fa-chevron-left" aria-hidden="true"></i>
  </button>
  
  <div class="awards-carousel" id="awards-carousel">
    {% for a in site.data.awards %}
    <div class="award-card carousel-card">
      <div class="xp-head">
        <h3 class="award-card__title">
          <i class="fas fa-medal award-card__medal" aria-hidden="true"></i> 
          <span>{{ a.title }}</span>
        </h3>
        {% if a.date %}<span class="xp-pills"><span class="xp-pill">{{ a.date }}</span></span>{% endif %}
      </div>
      {% if a.org %}
      <ul class="entry-meta">
        <li><i class="fas fa-building" aria-hidden="true"></i> {{ a.org }}</li>
      </ul>
      {% endif %}
      {% if a.points %}
      <ul class="entry-points">
        {% for pt in a.points %}
        <li>{{ pt }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </div>

  <button class="carousel-btn next" aria-label="Next Award" onclick="document.getElementById('awards-carousel').scrollBy({left: 370, behavior: 'smooth'})">
    <i class="fas fa-chevron-right" aria-hidden="true"></i>
  </button>
</div>

<h2 class="section-title reveal"><i class="fas fa-tasks" aria-hidden="true"></i> Professional Activities</h2>
<div class="activities-carousel-container reveal">
  <button class="carousel-btn prev" aria-label="Previous Activity" onclick="document.getElementById('activities-carousel').scrollBy({left: -370, behavior: 'smooth'})">
    <i class="fas fa-chevron-left" aria-hidden="true"></i>
  </button>
  
  <div class="activities-carousel" id="activities-carousel">
    {% for group in site.data.fun_time %}
      {% for ev in group.events %}
      {% case ev.cat %}
        {% when 'bootcamp' %}{% assign ic = 'fa-laptop-code' %}
        {% when 'summer-school' %}{% assign ic = 'fa-sun' %}
        {% when 'oral' %}{% assign ic = 'fa-microphone-alt' %}
        {% when 'delegate' %}{% assign ic = 'fa-users' %}
        {% when 'virtual' %}{% assign ic = 'fa-video' %}
        {% when 'reviewer' %}{% assign ic = 'fa-clipboard-check' %}
        {% else %}{% assign ic = 'fa-globe' %}
      {% endcase %}
      <div class="activity-card carousel-card" data-cat="{{ ev.cat }}">
        <h3 class="activity-card__title">
          <i class="fas {{ ic }} activity-card__icon activity-card__icon--{{ ev.cat }}" aria-hidden="true"></i>
          <span>{% if ev.url %}<a href="{{ ev.url }}" target="_blank" rel="noopener">{{ ev.title }}</a>{% else %}{{ ev.title }}{% endif %}</span>
        </h3>
        <ul class="entry-meta">
          <li><i class="fas fa-tag" aria-hidden="true"></i> {{ ev.type }} · {{ group.year }}</li>
          {% if ev.detail %}<li><i class="fas fa-clock" aria-hidden="true"></i> {{ ev.detail }}</li>{% endif %}
          {% if ev.org %}<li><i class="fas fa-building" aria-hidden="true"></i> {{ ev.org }}</li>{% endif %}
          {% if ev.where %}<li><i class="fas fa-map-marker-alt" aria-hidden="true"></i> {{ ev.where }}</li>{% endif %}
        </ul>
      </div>
      {% endfor %}
    {% endfor %}
  </div>

  <button class="carousel-btn next" aria-label="Next Activity" onclick="document.getElementById('activities-carousel').scrollBy({left: 370, behavior: 'smooth'})">
    <i class="fas fa-chevron-right" aria-hidden="true"></i>
  </button>
</div>

<h2 class="section-title reveal"><i class="fas fa-star" aria-hidden="true"></i> Featured Publications</h2>
<div id="featured-pubs" class="pub-grid">
{% assign featured = site.data.publications | where: "featured", true %}
{% for pub in featured %}{% include pub-card.html pub=pub %}{% endfor %}
</div>
<p class="reveal" style="display:flex;justify-content:space-between;align-items:baseline;gap:1rem"><span class="text-muted" style="font-size:.82rem">* Corresponding author</span><a class="chip" href="{{ '/publications/' | relative_url }}">All publications <i class="fas fa-arrow-right" aria-hidden="true"></i></a></p>


