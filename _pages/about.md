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
      <button type="button" class="js-modal-open" data-modal-target="#deadlines-modal" style="background: none; border: none; padding: 0; font-family: var(--font-head); font-size: var(--fs-sm); font-weight: 600; color: var(--accent); cursor: pointer; display: inline-flex; align-items: center; gap: 0.45rem; transition: color 0.2s var(--ease);" onmouseover="this.style.color='var(--accent-hover)'" onmouseout="this.style.color='var(--accent)'">
        <i class="fas fa-calendar-alt" aria-hidden="true"></i> AI Conference Deadlines <span id="deadlines-next-badge"></span> <i class="fas fa-arrow-right" aria-hidden="true" style="font-size: 0.9em;"></i>
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

<div class="modal" id="deadlines-modal" role="dialog" aria-modal="true" aria-labelledby="deadlines-modal-title">
  <div class="modal__dialog" style="max-width: 42rem;">
    <div class="modal__head">
      <h3 class="modal__title" id="deadlines-modal-title"><i class="fas fa-calendar-alt" aria-hidden="true"></i> AI Conference Deadlines</h3>
      <button type="button" class="modal__close js-modal-close" aria-label="Close deadlines popup">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
    <div class="modal__body" style="padding-top: 0.5rem;">
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: left;" id="deadlines-table">
          <thead>
            <tr style="border-bottom: 2px solid var(--border); color: var(--text-strong);">
              <th style="padding: 0.75rem 0.5rem; font-weight: 600;">Conference</th>
              <th style="padding: 0.75rem 0.5rem; font-weight: 600; text-align: center;">Rank</th>
              <th style="padding: 0.75rem 0.5rem; font-weight: 600;">Deadline, Location</th>
              <th style="padding: 0.75rem 0.5rem; font-weight: 600; text-align: center;">Countdown</th>
            </tr>
          </thead>
          <tbody>
            <!-- A* Conferences -->
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-05-06">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">NeurIPS</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">May 6, 2026, Vancouver, Canada</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-09-30">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ICLR</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">September 30, 2026, New Orleans, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2027-01-27">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ICML</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">January 27, 2027, Honolulu, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-11-11">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">CVPR</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">November 11, 2026, Nashville, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-03-05">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ECCV</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 5, 2026, Munich, Germany</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2027-03-11">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ICCV</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 11, 2027, Sydney, Australia</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-09-10">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">CHI</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">September 10, 2026, Pittsburgh, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-07-29">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">AAAI</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">July 29, 2026, Montréal, Canada</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-10-13">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">WWW</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">October 13, 2026, Dublin, Ireland</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-09-15">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ICRA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #fee2e2; color: #991b1b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A*</span></td>
              <td style="padding: 0.75rem 0.5rem;">September 15, 2026, Seoul, South Korea</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>

            <!-- A Conferences -->
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-05-30">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">BMVC</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A</span></td>
              <td style="padding: 0.75rem 0.5rem;">May 30, 2026, London, UK</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-06-27">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">WACV</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A</span></td>
              <td style="padding: 0.75rem 0.5rem;">June 27, 2026, Waikoloa, Hawaii, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-03-02">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">IROS</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 2, 2026, Pittsburgh, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-03-02">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">Interspeech</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 2, 2026, Sydney, Australia</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-03-10">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">MICCAI</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #ffedd5; color: #c2410c; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">A</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 10, 2026, Strasbourg, France</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>

            <!-- B Conferences -->
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-07-03">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">ACCV</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #f1f5f9; color: #334155; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">B</span></td>
              <td style="padding: 0.75rem 0.5rem;">July 3, 2026, Taipei, Taiwan</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>

            <!-- No Rank Conferences -->
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-05-28">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">CoRL</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #f1f5f9; color: #64748b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 500; font-size: 0.78rem;">—</span></td>
              <td style="padding: 0.75rem 0.5rem;">May 28, 2026, Austin, USA</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
            <tr style="border-bottom: 1px solid var(--border);" data-deadline="2026-03-06">
              <td style="padding: 0.75rem 0.5rem; font-weight: 600; color: var(--text-strong);">RSS</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;"><span style="background: #f1f5f9; color: #64748b; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 500; font-size: 0.78rem;">—</span></td>
              <td style="padding: 0.75rem 0.5rem;">March 6, 2026, Sydney, Australia</td>
              <td style="padding: 0.75rem 0.5rem; text-align: center;" class="deadline-countdown"></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<h2 class="section-title reveal"><i class="fas fa-lightbulb" aria-hidden="true"></i> Research Highlights</h2>
<div class="highlight-grid">
  <article class="highlight-card card reveal" data-delay="1">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/10-years-robotics-taxonomy.webp' | relative_url }}" data-caption="Physical AI &amp; Agentic Robotics: Embodied agents that plan and act in latent world models for robot manipulation, bridging perception, reasoning, and control toward physical AGI." aria-label="Zoom figure">
      <img src="{{ '/images/10-years-robotics-taxonomy.webp' | relative_url }}" alt="Ten-year robotics taxonomy for physical AI and agentic robotics" loading="lazy">
    </button>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">Physical AI &amp; Agentic Robotics</h3>
      <p class="highlight-card__desc">Embodied agents that plan and act in latent world models for robot manipulation, bridging perception, reasoning, and control toward physical AGI.</p>
      <div class="tag-list"><span class="tag">Vision-Language-Action</span><span class="tag">World Models</span><span class="tag">Agentic Robotics</span><span class="tag">Robot Learning</span><span class="tag">5D AI Robotics</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="2">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/C3G_VM6D_Architecture.webp' | relative_url }}" data-caption="3D Vision &amp; 6D Pose Estimation: Recovering full object pose and geometry from images and point clouds for spatially-grounded, robust scene understanding." aria-label="Zoom figure">
      <img src="{{ '/images/C3G_VM6D_Architecture.webp' | relative_url }}" alt="6D pose estimation architecture" loading="lazy">
    </button>
    <div class="highlight-card__body">
      <h3 class="highlight-card__title">3D Vision &amp; 6D Pose Estimation</h3>
      <p class="highlight-card__desc">Recovering full object pose and geometry from images and point clouds for spatially-grounded, robust scene understanding.</p>
      <div class="tag-list"><span class="tag">3D Vision</span><span class="tag">6D Pose</span><span class="tag">Spatial Intelligence</span></div>
    </div>
  </article>
  <article class="highlight-card card reveal" data-delay="3">
    <button class="highlight-card__media js-lightbox" type="button" data-full="{{ '/images/3d_point_cloud_visualization.webp' | relative_url }}" data-caption="Perception &amp; Representation Learning: Learning transferable visual representations, from image denoising and autoencoders to point-cloud understanding for downstream 3D tasks." aria-label="Zoom figure">
      <img src="{{ '/images/3d_point_cloud_visualization.webp' | relative_url }}" alt="Point cloud representation learning" loading="lazy">
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


