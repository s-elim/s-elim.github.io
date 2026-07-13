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
      <span class="chip">3D Computer Vision</span>
      <span class="chip">Spatial Intelligence</span>
      <span class="chip">6D Pose Estimation</span>
      <span class="chip">Vision-Language-Action</span>
      <span class="chip">World Models</span>
      <span class="chip">Agentic Robotics</span>
      <span class="chip">Physical AI</span>
      <span class="chip">5D AI Robotics</span>
    </div>
    <div style="margin-bottom: 1.15rem;">
      <button type="button" class="js-modal-open" data-modal-target="#about-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-user-circle" aria-hidden="true"></i> Click to read about me <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
      </button>
    </div>
    <div class="hero__actions">
      <a class="btn btn--strong" href="{{ p.cv_url }}" target="_blank" rel="noopener"><i class="fas fa-file-alt" aria-hidden="true"></i> View CV</a>
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

<div class="modal" id="about-modal" role="dialog" aria-modal="true" aria-labelledby="about-modal-title">
  <div class="modal__dialog">
    <div class="modal__head">
      <h3 class="modal__title" id="about-modal-title"><i class="fas fa-user" aria-hidden="true"></i> About</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close about popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body">
<p>I am pursuing an <strong>M.Sc. in Computer Vision &amp; AI</strong> at <a href="http://www.ynu.kr/_english/main/index.php" target="_blank" rel="noopener">Yeungnam University (YU)</a> as a <a href="https://www.studyinkorea.go.kr/" target="_blank" rel="noopener">Global Korea Scholarship (GKS)</a> scholar funded by NIIED, with additional support from the <strong>RLRC &amp; RISE</strong> industry-collaboration projects. I am a member of the <a href="https://avilabyu.wixsite.com/avil" target="_blank" rel="noopener">Advanced Visual Intelligence Lab</a>, supervised by <a href="https://scholar.google.com/citations?user=3TptC38AAAAJ&hl=en" target="_blank" rel="noopener">Prof. Sungho Kim</a>.</p>

<p>My research focuses on <strong>3D computer vision &amp; spatial intelligence, 6D pose estimation, vision-language-action (VLA) models, world models, and agentic robotics</strong> for robot manipulation. I aim to build embodied agents capable of perceiving, reasoning, and acting within the physical world, working toward <strong>physical AGI</strong>. My contributions in these areas include first-author publications at <strong>BMVC'26</strong> and in <strong>IEEE Access (SCIE-Q1)</strong>.</p>

<p>Before joining YU, I completed a one-year Korean Language &amp; Literature program at KLI under the GKS program, and spent a year as a full-time Research Assistant in the <a href="https://nthu-en.site.nthu.edu.tw/" target="_blank" rel="noopener">WCSP Lab at National Tsing Hua University</a>, Taiwan. I earned my B.Tech (Electronics &amp; Electrical Engineering) as an <a href="https://studyinindia.gov.in/" target="_blank" rel="noopener">SII Scholar</a> from the <a href="https://kiit.ac.in/" target="_blank" rel="noopener">Kalinga Institute of Industrial Technology (KIIT)</a>, and interned at <a href="https://www.iitr.ac.in/" target="_blank" rel="noopener">IIT Roorkee</a> on image processing for biomedical signals.</p>
    </div>
  </div>
</div>

<h2 class="section-title reveal"><i class="fas fa-lightbulb" aria-hidden="true"></i> Research Highlights</h2>
<div class="highlight-grid">
  <article class="highlight-card card reveal" data-delay="1">
    <div class="highlight-card__media"><img src="{{ '/images/10-years-robotics-taxonomy.webp' | relative_url }}" alt="Ten-year robotics taxonomy for physical AI and agentic robotics" loading="lazy"></div>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">Physical AI &amp; Agentic Robotics</h3>
      <p class="highlight-card__desc">Embodied agents that plan and act in latent world models for robot manipulation, bridging perception, reasoning, and control toward physical AGI.</p>
      <div class="tag-list"><span class="tag">Vision-Language-Action</span><span class="tag">World Models</span><span class="tag">Agentic Robotics</span><span class="tag">Robot Learning</span><span class="tag">5D AI Robotics</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="2">
    <div class="highlight-card__media"><img src="{{ '/images/C3G_VM6D_Architecture.webp' | relative_url }}" alt="6D pose estimation architecture" loading="lazy"></div>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">3D Vision &amp; 6D Pose Estimation</h3>
      <p class="highlight-card__desc">Recovering full object pose and geometry from images and point clouds for spatially-grounded, robust scene understanding.</p>
      <div class="tag-list"><span class="tag">3D Vision</span><span class="tag">6D Pose</span><span class="tag">Spatial Intelligence</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="3">
    <div class="highlight-card__media"><img src="{{ '/images/3d_point_cloud_visualization.webp' | relative_url }}" alt="Point cloud representation learning" loading="lazy"></div>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">Perception &amp; Representation Learning</h3>
      <p class="highlight-card__desc">Learning transferable visual representations, from image denoising and autoencoders to point-cloud understanding for downstream 3D tasks.</p>
      <div class="tag-list"><span class="tag">Point Clouds</span><span class="tag">Representation Learning</span><span class="tag">Denoising</span></div>
    </div>
  </article>
</div>

<h2 class="section-title reveal"><i class="fas fa-star" aria-hidden="true"></i> Featured Publications</h2>
<div id="featured-pubs" class="pub-grid">
{% assign featured = site.data.publications | where: "featured", true %}
{% for pub in featured %}{% include pub-card.html pub=pub %}{% endfor %}
</div>
<p class="reveal" style="display:flex;justify-content:space-between;align-items:baseline;gap:1rem"><span class="text-muted" style="font-size:.82rem">* Corresponding author</span><a class="chip" href="{{ '/publications/' | relative_url }}">All publications <i class="fas fa-arrow-right" aria-hidden="true"></i></a></p>

<h2 class="section-title reveal"><i class="fas fa-bullhorn" aria-hidden="true"></i> Updates</h2>
<div class="updates-card card reveal">
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
