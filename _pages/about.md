---
permalink: /
layout: home
title: Home
description: "Md Selim Sarowar: M.Sc. student in Computer Vision & AI at Yeungnam University (GKS Scholar). Research in 3D computer vision, 6D pose estimation, vision-language-action models, world models, and agentic robotics toward physical super intelligence."
og_image: "physical_superintelligence_white_bg.jpg"
redirect_from:
  - /about/
  - /about.html
---

{% assign p = site.data.profiles %}
{%- comment -%}
  "Research arc" hero panel, all from _data/*.yml. The footer counts use the
  same rule as /publications/ (patents and in-preparation work excluded);
  first-author also counts a shared first authorship (dagger). The arc itself
  draws every non-patent paper with a `thrust` onto one of four layers:
  published work as beads, "Under Review" / "In Preparation" work as labelled
  chips (in-preparation papers are drawn even though they are not counted).
  A published paper with `arc_label: true` is drawn as a solid labelled chip.
  Within a layer: published beads first, then chips, each oldest to newest.
{%- endcomment -%}
{%- assign pubs = site.data.publications -%}
{%- assign glance_pubs = 0 -%}
{%- assign glance_first = 0 -%}
{%- for pub in pubs -%}
  {%- if pub.status != "In Preparation" and pub.type != "patent" -%}
    {%- assign glance_pubs = glance_pubs | plus: 1 -%}
    {%- assign lead = pub.authors | remove: "*" | strip | slice: 0, 16 -%}
    {%- if lead == "Md Selim Sarowar" or pub.authors contains "Md Selim Sarowar†" -%}{%- assign glance_first = glance_first | plus: 1 -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- assign arc_pubs = pubs | reverse -%}
{%- assign arc_years = pubs | map: "year" | uniq | sort -%}
{%- assign arc_year_min = arc_years | first -%}
{%- assign arc_year_max = arc_years | last -%}
{%- assign arc_passes = "published,progress" | split: "," -%}
{%- comment -%} key|eyebrow|name, top layer first; "~" separates layers (";" would split "&amp;"). {%- endcomment -%}
{%- assign arc_layers = "agency|Agency|Agentic Robotics~world-models|Imagination|World Models~vla|Action|Vision-Language-Action~perception|Perception|3D Vision & 6D Pose" | split: "~" -%}
{%- assign arc_pubs_url = '/publications/' | relative_url -%}

<section class="hero hero--clean">
  <img class="hero__avatar" src="{{ '/images/' | append: p.avatar | relative_url }}" alt="Portrait of {{ p.name }}" width="152" height="152">
  <div class="hero__intro">
    <h1 class="hero__name">{{ p.name }}</h1>
    <span class="hero__role">M.Sc. (Research) Student &middot; 3D Computer Vision &amp; Physical Super Intelligence</span>
    <span class="hero__affil"><a href="https://avil-lab.github.io/avil/" target="_blank" rel="noopener">Advanced Visual Intelligence Lab</a>, Yeungnam University &middot; GKS Scholar</span>
    <p class="hero__bio">I build embodied agents that perceive, reason and act in the physical world, working toward <strong>physical super intelligence</strong>. My work spans <strong>3D computer vision &amp; 6D pose estimation</strong>, <strong>vision-language-action (VLA) models</strong> and <strong>latent world models</strong> for robot manipulation, with first-author papers at <strong>BMVC&rsquo;26</strong> and in <strong>IEEE Access</strong>. <button type="button" class="news-more js-modal-open" data-modal-target="#about-modal">More about me &rarr;</button></p>
    <a class="hero__status" href="mailto:{{ p.email }}?subject=Research%20collaboration%20%2F%20PhD%20opportunity">Open to research collaborations &amp; PhD positions</a>
    <div class="hero__chips">
      <span class="chip">World Models</span>
      <span class="chip">Vision-Language-Action Models</span>
      <span class="chip">JEPA (H/V-JEPA)</span>
      <span class="chip">Agentic Robotics</span>
      <span class="chip">6D Pose Estimation</span>
      <span class="chip">Spatial Intelligence</span>
      <span class="chip">Causal Learning</span>
    </div>
    <div class="hero__actions">
      <a class="btn btn--strong" href="{{ p.cv_url }}" target="_blank" rel="noopener"><i class="fas fa-file-alt" aria-hidden="true"></i> View CV</a>
      <button class="btn btn--ghost js-copy-email" type="button" data-email="{{ p.email }}" title="Copy email address to clipboard"><i class="fas fa-copy" aria-hidden="true"></i> Copy Email</button>
      <a class="btn btn--ghost" href="{{ p.scholar }}" target="_blank" rel="noopener"><i class="fas fa-graduation-cap" aria-hidden="true"></i> Google Scholar</a>
      <span class="hero__social">
        <a href="https://github.com/{{ p.github }}" target="_blank" rel="noopener" aria-label="GitHub"><i class="fab fa-github" aria-hidden="true"></i></a>
        <a href="https://www.linkedin.com/in/{{ p.linkedin }}" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="fab fa-linkedin" aria-hidden="true"></i></a>
        <a href="{{ p.researchgate }}" target="_blank" rel="noopener" aria-label="ResearchGate"><i class="fab fa-researchgate" aria-hidden="true"></i></a>
      </span>
    </div>
  </div>
  <aside class="glance glance--arc" id="glance" aria-label="Research arc">
    <div class="glance__head">
      <span class="glance__eyebrow">Research arc</span>
      <span class="glance__hint" aria-hidden="true">{{ arc_year_min }} &rarr; {{ arc_year_max }}</span>
    </div>
    <div class="arc">
      <div class="arc__apex" style="--i:4">
        <span class="arc__star" aria-hidden="true">&#9733;</span>
        <span class="arc__apex-label">Physical Super Intelligence</span>
      </div>
      <ol class="arc__layers" aria-label="Research layers, bottom to top">
        {%- for layer in arc_layers -%}
          {%- assign ldef = layer | split: "|" -%}
          {%- assign lkey = ldef[0] -%}
          {%- assign li = 3 | minus: forloop.index0 -%}
          {%- assign j = 0 -%}
        <li class="arc-layer arc-layer--{{ lkey }}" style="--i:{{ li }}">
          <span class="arc-layer__tick" aria-hidden="true"></span>
          <span class="arc-layer__label"><span class="arc-layer__key">{{ ldef[1] }}</span><span class="arc-layer__name">{{ ldef[2] | escape }}</span></span>
          <span class="arc-layer__nodes">
            {%- for pass in arc_passes -%}
            {%- for yr in arc_years -%}
            {%- for pub in arc_pubs -%}
              {%- if pub.type == "patent" or pub.thrust != lkey or pub.year != yr -%}{%- continue -%}{%- endif -%}
              {%- assign kind = "" -%}
              {%- if pub.status == "Under Review" -%}{%- assign kind = "review" -%}
              {%- elsif pub.status == "In Preparation" -%}{%- assign kind = "prep" -%}
              {%- elsif pub.status == nil or pub.status == "" or pub.status == "Accepted" -%}{%- assign kind = "pub" -%}
              {%- endif -%}
              {%- if kind == "" -%}{%- continue -%}{%- endif -%}
              {%- if pass == "published" and kind != "pub" -%}{%- continue -%}{%- endif -%}
              {%- if pass == "progress" and kind == "pub" -%}{%- continue -%}{%- endif -%}
              {%- if pub.short -%}{%- assign nm = pub.short -%}
              {%- else -%}
                {%- assign tparts = pub.title | split: ":" -%}
                {%- if tparts.size > 1 -%}{%- assign nm = tparts[0] -%}{%- else -%}{%- assign nm = pub.title | truncate: 28 -%}{%- endif -%}
              {%- endif -%}
              {%- if pub.status and pub.status != "" -%}{%- assign st = pub.status -%}
              {%- elsif pub.type == "preprint" -%}{%- assign st = "Preprint" -%}
              {%- elsif pub.venue contains "(Accepted)" -%}{%- assign st = "Accepted" -%}
              {%- else -%}{%- assign st = "Published" -%}{%- endif -%}
              {%- assign vshort = pub.venue_short | default: pub.thumb -%}
              {%- assign href = pub.url | default: arc_pubs_url -%}
              {%- assign vclean = pub.venue | remove: " (Accepted)" -%}
              {%- if pub.type == "preprint" -%}{%- assign vclean = "preprints.org" -%}{%- endif -%}
            <a class="arc-node arc-node--{{ kind }}{% if kind == 'pub' and pub.arc_label %} arc-node--named{% endif %}" href="{{ href }}"{% if pub.url %} target="_blank" rel="noopener"{% endif %} style="--j:{{ j }}" aria-label="{{ pub.title | escape }} &mdash; {{ vclean | escape }}, {{ pub.year }}, {{ st }}">
              <span class="arc-node__dot" aria-hidden="true"></span>
              {%- if kind != "pub" or pub.arc_label -%}<span class="arc-node__name">{{ nm | escape }}</span><span class="arc-node__meta">{% if vshort %}{{ vshort | escape }} &middot; {% endif %}{{ st }}</span>{%- endif -%}
              <span class="arc-card" aria-hidden="true"><b class="arc-card__title">{{ pub.title | escape }}</b><span class="arc-card__meta">{{ vclean | escape }} &middot; {{ pub.year }} &middot; <span class="arc-card__state">{{ st }}</span></span></span>
            </a>
              {%- assign j = j | plus: 1 -%}
            {%- endfor -%}
            {%- endfor -%}
            {%- endfor -%}
          </span>
        </li>
        {%- endfor -%}
      </ol>
    </div>
    <div class="arc-foot">
      <p class="arc-counts">
        <a href="{{ arc_pubs_url }}"><b data-count="{{ glance_pubs }}">{{ glance_pubs }}</b> papers</a><span class="arc-sep" aria-hidden="true">&middot;</span>
        <a href="{{ arc_pubs_url }}"><b data-count="{{ glance_first }}">{{ glance_first }}</b> first-author</a><span class="arc-sep" aria-hidden="true">&middot;</span>
        <a href="{{ '/experience/' | relative_url }}"><b data-count="{{ site.data.reviewing | size }}">{{ site.data.reviewing | size }}</b> venues reviewed</a><span class="arc-sep" aria-hidden="true">&middot;</span>
        <a href="#awards"><b data-count="{{ site.data.awards | size }}">{{ site.data.awards | size }}</b> awards</a>
      </p>
      <p class="arc-legend" aria-label="Legend"><span><i class="arc-key arc-key--pub" aria-hidden="true"></i>Published</span><span><i class="arc-key arc-key--review" aria-hidden="true"></i>Under review</span><span><i class="arc-key arc-key--prep" aria-hidden="true"></i>In preparation</span></p>
    </div>
  </aside>
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
<p>I am pursuing an <strong>M.Sc. in Computer Vision &amp; AI</strong> at <a href="http://www.ynu.kr/_english/main/index.php" target="_blank" rel="noopener">Yeungnam University (YU)</a>, where I am maintaining a perfect <strong>CGPA of 4.5/4.5 (Ranked 1st / Top 1)</strong>. I am a <a href="https://www.studyinkorea.go.kr/" target="_blank" rel="noopener">Global Korea Scholarship (GKS)</a> scholar funded by NIIED, with additional support from the <strong>RLRC &amp; RISE</strong> industry-collaboration projects. I am a member of the <a href="https://avil-lab.github.io/avil/" target="_blank" rel="noopener">Advanced Visual Intelligence Lab</a>, supervised by <a href="https://scholar.google.com/citations?user=3TptC38AAAAJ&hl=en" target="_blank" rel="noopener">Prof. Sungho Kim</a>.</p>

<p>My research focuses on <strong>3D computer vision &amp; spatial intelligence, 6D pose estimation, vision-language-action (VLA) models, world models, and agentic robotics</strong> for robot manipulation. I aim to build embodied agents capable of perceiving, reasoning, and acting within the physical world, working toward <strong>physical super intelligence</strong>. My contributions in these areas include first-author publications at <strong>BMVC'26</strong> and in <strong>IEEE Access (SCIE-Q1)</strong>.</p>

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
      <div class="updates-card updates-card--bare card">
        <div class="updates-card__scroll" id="updates-scroll" tabindex="0" aria-label="Updates timeline, scroll for older news">
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

<div class="modal" id="rankings-modal" role="dialog" aria-modal="true" aria-labelledby="rankings-modal-title" data-rank-src="{{ '/assets/data/university-rankings.json' | relative_url }}">
  <div class="modal__dialog modal__dialog--wide">
    <div class="modal__head">
      <h3 class="modal__title" id="rankings-modal-title"><i class="fas fa-trophy" aria-hidden="true"></i> World University Rankings &mdash; Top 400</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close university rankings popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body modal__body--tight">
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
          <strong>{{ src.name }} {{ src.edition }}</strong> &middot; published {{ src.published }} &middot; full table covers {{ src.total_ranked }}. Showing all {{ src.count }} institutions placed in the top 400.
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
                <th class="rank-th-num">Rank</th>
                <th>University</th>
                <th>Country<span class="rank-th-full"> / Territory</span></th>
              </tr>
            </thead>
            <!-- Rows are fetched from assets/data/university-rankings.json on first
                 open: inlining 800 of them tripled the homepage DOM. -->
            <tbody>
              <tr class="rank-empty" hidden><td colspan="3">No university matches that filter.</td></tr>
              <tr class="rank-loading"><td colspan="3">Loading the {{ src.short }} {{ src.edition }} top 400&hellip;</td></tr>
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


<h2 class="section-title reveal">Selected Publications</h2>
<div id="featured-pubs" class="pub-grid">
{% assign featured = site.data.publications | where: "featured", true %}
{% for pub in featured %}{% include pub-card.html pub=pub %}{% endfor %}
</div>
<p class="pub-footnote reveal"><span class="pub-legend text-muted">* Corresponding author</span><a class="chip" href="{{ '/publications/' | relative_url }}">All publications <i class="fas fa-arrow-right" aria-hidden="true"></i></a></p>

<h2 class="section-title reveal">News</h2>
<ul class="news-list reveal">
  {% for item in site.data.news limit: 5 %}
  <li class="news-list__item"><span class="news-list__date">{{ item.date }}</span><p class="news-list__text">{{ item.text }}</p></li>
  {% endfor %}
</ul>
<button type="button" class="news-more js-modal-open" data-modal-target="#updates-modal">All updates &rarr;</button>

<h2 class="section-title reveal" id="awards">Awards &amp; Honors</h2>
<ul class="award-list reveal">
  {% for a in site.data.awards %}
  <li class="award-list__item">
    <i class="fas fa-medal award-list__icon" aria-hidden="true"></i>
    <span class="award-list__title">{{ a.title }}{% if a.org %}<span class="award-list__org">{{ a.org }}</span>{% endif %}</span>
    {% if a.date %}<span class="award-list__date">{{ a.date }}</span>{% endif %}
  </li>
  {% endfor %}
</ul>

<h2 class="section-title reveal">Activities &amp; Training</h2>
<div class="activities-carousel-container reveal" data-carousel>
  <button class="carousel-btn prev" type="button" data-carousel-prev aria-label="Scroll professional activities backwards">
    <i class="fas fa-chevron-left" aria-hidden="true"></i>
  </button>
  
  <div class="activities-carousel" id="activities-carousel" data-carousel-track tabindex="0" role="group" aria-label="Professional activities, scroll horizontally or use the arrow keys">
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

  <button class="carousel-btn next" type="button" data-carousel-next aria-label="Scroll professional activities forwards">
    <i class="fas fa-chevron-right" aria-hidden="true"></i>
  </button>
  <div class="carousel-rail" aria-hidden="true"><span class="carousel-rail__bar" data-carousel-progress></span></div>
</div>

<h2 class="section-title reveal">Resources</h2>
<div class="res-grid reveal">
  <a class="res-card" href="{{ '/deadlines/' | relative_url }}">
    <span class="res-card__icon"><i class="fas fa-stopwatch" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">Conference Deadlines</span><span class="res-card__sub">Live countdowns, CORE A* &amp; A</span><span class="hero__link-badge res-card__badge" id="deadlines-next-badge"></span></span>
  </a>
  <a class="res-card" href="{{ '/journals/' | relative_url }}">
    <span class="res-card__icon"><i class="fas fa-book-open" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">Top Q1 Journals</span><span class="res-card__sub">Where to submit</span></span>
  </a>
  <a class="res-card" href="{{ '/phd-postdoc-openings/' | relative_url }}" title="PhD and Postdoc positions in Physical AI, World Models, and Robotics">
    <span class="res-card__icon"><i class="fas fa-graduation-cap" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">PhD &amp; Postdoc Openings</span><span class="res-card__sub">Physical AI, world models, robotics</span></span>
    {% if site.data.openings.total_count > 0 %}<span class="hero__link-badge"><span class="idea-count-pill">{{ site.data.openings.total_count }}</span></span>{% endif %}
  </a>
  <a class="res-card" href="{{ '/research-ideas/' | relative_url }}" title="{{ site.data.research_ideas.ideas | size }} ideas and {{ site.data.link_library.links | size }} tracked links">
    <span class="res-card__icon"><i class="fas fa-lightbulb" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">Research Resources</span><span class="res-card__sub">Ideas and a curated link library</span></span>
    <span class="hero__link-badge"><span class="idea-count-pill">{{ site.data.research_ideas.ideas | size }}</span></span>
  </a>
  <button type="button" class="res-card js-modal-open" data-modal-target="#rankings-modal">
    <span class="res-card__icon"><i class="fas fa-trophy" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">University Rankings</span><span class="res-card__sub">THE &amp; QS top 400</span></span>
  </button>
  <button type="button" class="res-card js-modal-open" data-modal-target="#updates-modal">
    <span class="res-card__icon"><i class="fas fa-bullhorn" aria-hidden="true"></i></span>
    <span class="res-card__body"><span class="res-card__title">All Updates</span><span class="res-card__sub">Full news timeline</span></span>
  </button>
</div>
<script type="application/json" id="deadlines-mini">[
    {%- assign dl_first = true -%}
    {%- for c in site.data.conferences -%}
      {%- for t in c.timeline -%}
        {%- if t.date and t.date != 'tba' -%}
          {%- unless dl_first %},{% endunless %}{% assign dl_first = false %}
          {"n":{{ c.name | jsonify }},"d":{{ t.date | date: "%Y-%m-%d" | jsonify }},"t":{{ t.time | default: "23:59" | jsonify }},"z":{{ t.tz | default: "" | jsonify }}}
        {%- endif -%}
      {%- endfor -%}
    {%- endfor -%}
    ]</script>
