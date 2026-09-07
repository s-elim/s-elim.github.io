---
layout: archive
title: "Publications"
permalink: /publications/
wide: true
description: "Peer-reviewed publications and preprints by Md Selim Sarowar across 3D computer vision, 6D pose estimation, vision-language-action models, and robot learning."
---

{% assign pubs = site.data.publications %}
{% assign total = pubs | size %}
{% assign prep = pubs | where: "status", "In Preparation" %}
{% assign prepcount = prep | size %}
{% assign published = 0 %}
{% for pub in pubs %}
  {% if pub.status != "In Preparation" and pub.type != "patent" %}
    {% assign published = published | plus: 1 %}
  {% endif %}
{% endfor %}
{% assign scie = 0 %}
{% for pub in pubs %}
  {% if pub.status != "In Preparation" %}
    {% if pub.impact contains "SCIE-Q1" or pub.venue contains "SCIE-Q1" %}
      {% assign scie = scie | plus: 1 %}
    {% endif %}
  {% endif %}
{% endfor %}
{% assign ranked = 0 %}
{% for pub in pubs %}
  {% if pub.status != "In Preparation" %}
    {% if pub.rank %}
      {% assign ranked = ranked | plus: 1 %}
    {% endif %}
  {% endif %}
{% endfor %}
{% assign years = pubs | map: "year" | uniq %}

<div class="stat-row reveal">
  <div class="stat"><div class="stat__num">{{ published }}</div><div class="stat__label">Publications</div></div>
  <div class="stat"><div class="stat__num">{{ ranked }}</div><div class="stat__label">Flagship Conference (A* &amp; A Rank)</div></div>
  <div class="stat"><div class="stat__num">{{ scie }}</div><div class="stat__label">SCIE-Q1 Journals</div></div>
  <div class="stat"><div class="stat__num">{{ prepcount }}</div><div class="stat__label">In Preparation</div></div>
</div>

<div class="pub-toolbar">
  <div class="pub-toolbar__top">
    <div class="pub-search">
      <i class="fas fa-search" aria-hidden="true"></i>
      <input id="pub-search" type="search" placeholder="Search title, author, or venue…" aria-label="Search publications">
    </div>
    <div class="pub-showing" aria-live="polite">Showing <strong id="pub-shown">{{ total }}</strong> / {{ total }}</div>
  </div>
  <div class="filter-chips" data-group="type" role="group" aria-label="Filter by type">
    <button class="filter-chip is-active" data-value="all" type="button">All Types</button>
    <button class="filter-chip" data-value="conference" type="button">Conference</button>
    <button class="filter-chip" data-value="journal" type="button">Journal</button>
    <button class="filter-chip" data-value="preprint" type="button">Preprint</button>
    <button class="filter-chip" data-value="workshop" type="button">Workshop</button>
    <button class="filter-chip" data-value="patent" type="button">Patent</button>
    <button class="filter-chip" data-value="lead" type="button"><i class="fas fa-star filter-chip__star" aria-hidden="true"></i> First / Lead Author</button>
    <button class="filter-chip" data-value="q1" type="button">Q1</button>
    <button class="filter-chip" data-value="toprank" type="button">A*/A</button>
  </div>
  <div class="filter-chips filter-chips--years" data-group="year" role="group" aria-label="Filter by year">
    <button class="filter-chip is-active" data-value="all" type="button">All Years</button>
    {% for y in years %}<button class="filter-chip" data-value="{{ y }}" type="button">{{ y }}</button>{% endfor %}
  </div>
  <div class="pub-actions">
    <button class="pub-action" id="pub-order" type="button" aria-pressed="false" title="Switch between newest-first and oldest-first">
      <i class="fas fa-sort-amount-down" aria-hidden="true"></i> <span class="pub-order__label">Newest first</span>
    </button>
    <button class="pub-action" id="pub-copy-all" type="button" title="Copy the BibTeX of every publication currently shown">
      <i class="fas fa-quote-right" aria-hidden="true"></i> <span class="js-copy-label">Copy BibTeX</span>
    </button>
    <button class="pub-action" id="pub-reset" type="button" disabled title="Clear the search box and every active filter">
      <i class="fas fa-undo" aria-hidden="true"></i> Reset
    </button>
  </div>
</div>

<div id="pub-list">
{% for y in years %}
  {% assign y_total = pubs | where: "year", y | size %}
  <section class="pub-year-section" data-year="{{ y }}">
    <h2 class="pub-year">{{ y }} <span class="pub-year__count">{{ y_total }}</span></h2>
    <div class="pub-grid">
    {% for pub in pubs %}{% if pub.year == y %}{% include pub-card.html pub=pub %}{% endif %}{% endfor %}
    </div>
  </section>
{% endfor %}
</div>
<p class="pub-empty" id="pub-empty">No publications match your filters.</p>
<p class="pub-legend text-muted reveal">* Corresponding author &nbsp;·&nbsp; † Equal contribution</p>
