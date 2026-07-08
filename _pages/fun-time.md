---
layout: archive
title: "Activity"
permalink: /fun-time/
description: "Bootcamps, summer schools, conferences, oral presentations, and delegate activities attended by Md Selim Sarowar."
---

<div class="filter-chips reveal" id="activity-filters" role="group" aria-label="Filter activities by category" style="margin-bottom:1.5rem">
  <button class="filter-chip is-active" data-value="all" type="button">All</button>
  <button class="filter-chip" data-value="bootcamp" type="button">Bootcamps</button>
  <button class="filter-chip" data-value="summer-school" type="button">Summer Schools</button>
  <button class="filter-chip" data-value="oral" type="button">Oral Talks</button>
  <button class="filter-chip" data-value="delegate" type="button">Delegate</button>
  <button class="filter-chip" data-value="in-person" type="button">In Person</button>
  <button class="filter-chip" data-value="virtual" type="button">Virtual</button>
</div>

<div id="activity-list">
{% for group in site.data.fun_time %}
<section class="activity-year timeline-group reveal">
  <h2 class="timeline-group__year">{{ group.year }}</h2>
  <div class="activity-grid">
    {% for ev in group.events %}
    {% case ev.cat %}
      {% when 'bootcamp' %}{% assign ic = 'fa-laptop-code' %}
      {% when 'summer-school' %}{% assign ic = 'fa-sun' %}
      {% when 'oral' %}{% assign ic = 'fa-microphone-alt' %}
      {% when 'delegate' %}{% assign ic = 'fa-users' %}
      {% when 'virtual' %}{% assign ic = 'fa-video' %}
      {% else %}{% assign ic = 'fa-globe' %}
    {% endcase %}
    <article class="activity-card" data-cat="{{ ev.cat }}">
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
    </article>
    {% endfor %}
  </div>
</section>
{% endfor %}
</div>
<p class="pub-empty" id="activity-empty">No activities match this filter.</p>
