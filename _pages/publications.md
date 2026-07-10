---
layout: archive
title: "Publications"
permalink: /publications/
description: "Peer-reviewed publications and preprints by Md Selim Sarowar across 3D computer vision, 6D pose estimation, vision-language-action models, and robot learning."
---

{% assign pubs = site.data.publications | where_exp: "p", "p.status != 'To be submitted'" %}
{% assign prep = site.data.publications | where_exp: "p", "p.status == 'To be submitted'" %}
{% assign total = pubs | size %}
{% assign scie = 0 %}{% for pub in pubs %}{% if pub.venue contains "SCIE-Q1" %}{% assign scie = scie | plus: 1 %}{% endif %}{% endfor %}
{% assign ranked = 0 %}{% for pub in pubs %}{% if pub.rank %}{% assign ranked = ranked | plus: 1 %}{% endif %}{% endfor %}
{% assign years = pubs | map: "year" | uniq %}

<div class="stat-row reveal">
  <div class="stat"><div class="stat__num">{{ total }}</div><div class="stat__label">Publications</div></div>
  <div class="stat"><div class="stat__num">{{ ranked }}</div><div class="stat__label">CORE Rank A</div></div>
  <div class="stat"><div class="stat__num">{{ scie }}</div><div class="stat__label">SCIE-Q1 Journals</div></div>
  <div class="stat"><div class="stat__num">{{ prep | size }}</div><div class="stat__label">In Preparation</div></div>
</div>

<div class="pub-toolbar">
  <div class="pub-search">
    <i class="fas fa-search" aria-hidden="true"></i>
    <input id="pub-search" type="search" placeholder="Search title, author, or venue…" aria-label="Search publications">
  </div>
  <div class="filter-chips" data-group="type" role="group" aria-label="Filter by type">
    <button class="filter-chip is-active" data-value="all" type="button">All Types</button>
    <button class="filter-chip" data-value="conference" type="button">Conference</button>
    <button class="filter-chip" data-value="journal" type="button">Journal</button>
    <button class="filter-chip" data-value="preprint" type="button">Preprint</button>
    <button class="filter-chip" data-value="workshop" type="button">Workshop</button>
  </div>
  <div class="filter-chips" data-group="year" role="group" aria-label="Filter by year" style="margin-top:.5rem">
    <button class="filter-chip is-active" data-value="all" type="button">All Years</button>
    {% for y in years %}<button class="filter-chip" data-value="{{ y }}" type="button">{{ y }}</button>{% endfor %}
  </div>
</div>

<div id="pub-list">
{% for y in years %}
  <section class="pub-year-section" data-year="{{ y }}">
    <h2 class="pub-year">{{ y }}</h2>
    {% for pub in pubs %}{% if pub.year == y %}{% include pub-card.html pub=pub %}{% endif %}{% endfor %}
  </section>
{% endfor %}
{% if prep.size > 0 %}
  <section class="pub-year-section">
    <h2 class="pub-year">In Preparation</h2>
    {% for pub in prep %}{% include pub-card.html pub=pub %}{% endfor %}
  </section>
{% endif %}
</div>
<p class="pub-empty" id="pub-empty">No publications match your filters.</p>
<p class="text-muted reveal" style="font-size:.82rem;margin-top:1.2rem">* Corresponding author</p>
