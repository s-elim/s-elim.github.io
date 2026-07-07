---
layout: archive
title: "Fun Time & Activities"
permalink: /fun-time/
description: "Bootcamps, summer schools, conferences, oral presentations, and delegate activities attended by Md Selim Sarowar."
---

{% for group in site.data.fun_time %}
<div class="timeline-group reveal">
  <h2 class="timeline-group__year">{{ group.year }}</h2>
  <div class="card" style="padding:.75rem 1.25rem">
    {% for ev in group.events %}
    <div class="activity-item">
      <i class="fas fa-globe activity-item__icon" aria-hidden="true"></i>
      <div><span class="activity-item__type">{{ ev.type }}</span>{{ ev.html }}</div>
    </div>
    {% endfor %}
  </div>
</div>
{% endfor %}
