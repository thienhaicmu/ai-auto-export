/**
 * Viral template runtime — Phase 5A: Cinematic Polish Engine
 *
 * Reads window.__SCENE__ props + audio direction, maps role → design tokens,
 * applies visual_direction attributes and CSS vars, populates DOM with
 * per-word animated spans, then signals window.__SCENE_READY__ = true.
 *
 * CONTRACT (must never break):
 *   - Only CSS Web Animations / @keyframes — NO setTimeout / setInterval
 *   - window.__SCENE_READY__ = true set after fonts (+ bg image) loaded
 *   - window.__SCENE__ injected by html_renderer.py via addInitScript
 *   - Missing visual_direction must not crash (all reads gated with || {})
 *   - Missing audio must not crash (gated with || {})
 */

(function () {
  'use strict';

  var scene  = window.__SCENE__ || {};
  var props  = scene.props     || {};

  // ── Audio Direction (Phase 4A) ─────────────────────────────────────────────

  var AUDIO = scene.audio || {};
  window.__SCENE_AUDIO__ = {
    bpm:             AUDIO.bpm            || 128,
    beat_markers:    AUDIO.beat_markers   || [],
    energy:          AUDIO.energy         || 3,
    transition_hit:  AUDIO.transition_hit || null,
    intro_hit:       AUDIO.intro_hit      || null,
    outro_hit:       AUDIO.outro_hit      || null,
  };

  // ── Extract props ──────────────────────────────────────────────────────────

  var ROLE            = scene.role                       || '';
  var ANIMATION_SEED  = props.animation_seed             || ((scene.index || 0) * 37 + 1000);
  var HEADLINE        = (props.headline || 'UNTITLED').toUpperCase();
  var SUBHEAD         = props.subhead                    || '';
  var BG_IMAGE        = props.background_image           || null;
  var HIGHLIGHT_IDX   = props.highlight_word_indices     || [];
  var SCENE_IDX       = scene.index != null ? scene.index : 0;
  var SCENE_DURATION  = ((scene.end || 0) - (scene.start || 0)) || 6;
  var SCENE_START     = scene.start || 0;

  // ── Visual Direction ───────────────────────────────────────────────────────

  var VD = props.visual_direction || {};
  var VD_ENERGY     = Math.max(1, Math.min(5, parseInt(VD.energy_level, 10) || 3));
  var VD_MOTION     = VD.motion_intensity  || 'medium';
  var VD_LAYOUT     = VD.layout_mode       || 'center';
  var VD_TRANSITION = VD.transition_style  || 'cut';
  var VD_BG         = VD.background_treatment || 'gradient';
  var VD_SUB_EM     = !!VD.subtitle_emphasis;
  var VD_EMPHASIS   = Array.isArray(VD.emphasis_words) ? VD.emphasis_words : [];

  // ── Role → design tokens ───────────────────────────────────────────────────

  var ROLE_MAP = {
    hook:        { accent: '#FF3D2E', label: 'BREAKING'   },
    context:     { accent: '#00C2E0', label: 'CONTEXT'    },
    escalation:  { accent: '#FF8C00', label: 'ESCALATION' },
    twist:       { accent: '#FFD700', label: 'REVEAL'     },
    payoff:      { accent: '#06D6A0', label: 'ACTION'     },
  };

  var roleData   = ROLE_MAP[ROLE] || { accent: '#7C5CFF', label: 'SCENE' };
  var ACCENT     = props.accent_color || roleData.accent;
  var LABEL_TEXT = roleData.label;

  // ── Derive glow / dim variants from accent hex ─────────────────────────────

  function hexToRgb(hex) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
    return parseInt(h.slice(0,2),16) + ',' +
           parseInt(h.slice(2,4),16) + ',' +
           parseInt(h.slice(4,6),16);
  }

  var rgb = hexToRgb(ACCENT);

  // ── Motion scale ──────────────────────────────────────────────────────────
  //
  //   calm=slow (1.4×), medium=normal (1.0×), high=fast (0.55×), impact=instant (0.22×)
  //   Cut transition overrides to near-instant regardless of motion_intensity.

  var MOTION_SCALE = { calm: 1.4, medium: 1.0, high: 0.55, impact: 0.22 };
  var motionFactor = MOTION_SCALE[VD_MOTION] || 1.0;
  if (VD_TRANSITION === 'cut') motionFactor = Math.min(motionFactor, 0.08);

  // ── Energy → glow alpha / dim alpha ──────────────────────────────────────

  var glowAlpha = 0.25 + (VD_ENERGY / 5) * 0.38;   // 0.33 – 0.63
  var dimAlpha  = 0.10 + (VD_ENERGY / 5) * 0.18;   // 0.12 – 0.28

  // ── Beat-sync delay ───────────────────────────────────────────────────────
  //
  //   intro_hit is an absolute timestamp (seconds from video start).
  //   We compute the beat position relative to this scene's start.
  //   If the beat falls in the first 40% of the scene, delay all reveal
  //   animations to land the label chip on the beat.
  //   Clamp to 0 if no data or beat is out of useful range.

  var beatDelay = 0.05;   // default: very short delay, not zero
  var introHit  = window.__SCENE_AUDIO__.intro_hit;
  if (introHit !== null && introHit !== undefined) {
    var relBeat = introHit - SCENE_START;
    if (relBeat > 0.02 && relBeat < SCENE_DURATION * 0.38) {
      beatDelay = relBeat;
    }
  }

  // ── Stagger timing ────────────────────────────────────────────────────────
  //
  //   WORD_STAGGER: gap between consecutive word reveals (seconds).
  //   At motionFactor=1.0, each word is 80ms after the previous.
  //   At motionFactor=0.22 (impact), all words appear almost simultaneously (18ms apart).

  var WORD_STAGGER = 0.08;   // seconds between words at 1× speed
  var word0Delay   = beatDelay;
  var words        = HEADLINE.trim().split(/\s+/);
  var wordCount    = words.length;

  // Time when the last word's animation starts
  var lastWordStart = word0Delay + (wordCount - 1) * WORD_STAGGER * motionFactor;
  // Divider appears after the last word settles
  var dividerDelay  = lastWordStart + 0.28 * motionFactor;
  // Subhead follows divider
  var subheadDelay  = dividerDelay  + 0.20 * motionFactor;

  // ── Headline energy boost ─────────────────────────────────────────────────

  var baseBoost   = VD_LAYOUT === 'full_bleed' ? 1.15 : 1.0;
  var energyBoost = baseBoost * (0.90 + (VD_ENERGY / 5) * 0.20);   // 0.936 – 1.38

  // ── Apply CSS custom properties ────────────────────────────────────────────

  var root = document.documentElement;

  root.style.setProperty('--accent',          ACCENT);
  root.style.setProperty('--accent-glow',     'rgba(' + rgb + ',' + glowAlpha.toFixed(2) + ')');
  root.style.setProperty('--accent-dim',      'rgba(' + rgb + ',' + dimAlpha.toFixed(2)  + ')');
  root.style.setProperty('--scene-duration',  SCENE_DURATION + 's');

  // Scaled motion durations
  root.style.setProperty('--dur-xs', (0.28 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-sm', (0.42 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-md', (0.65 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-lg', (0.92 * motionFactor).toFixed(3) + 's');

  // Beat-sync and cascade timing
  root.style.setProperty('--beat-delay',    beatDelay.toFixed(3)   + 's');
  root.style.setProperty('--divider-delay', dividerDelay.toFixed(3) + 's');
  root.style.setProperty('--subhead-delay', subheadDelay.toFixed(3) + 's');

  // Energy headline boost
  root.style.setProperty('--energy-headline-boost', energyBoost.toFixed(3));

  // ── Apply data attributes for CSS selectors ────────────────────────────────

  if (ROLE)          root.setAttribute('data-role',         ROLE);
  if (VD_MOTION)     root.setAttribute('data-motion',       VD_MOTION);
  if (VD_LAYOUT)     root.setAttribute('data-layout',       VD_LAYOUT);
  if (VD_TRANSITION) root.setAttribute('data-transition',   VD_TRANSITION);
  if (VD_BG)         root.setAttribute('data-bg-treatment', VD_BG);

  if (VD_SUB_EM) root.classList.add('subtitle-emphasis');

  // ── Adaptive headline size ─────────────────────────────────────────────────
  //
  //   Breakpoints:
  //     1 word  → 18.0 vw  (massive, fills frame)
  //     2 words → 15.0 vw
  //     3 words → 12.5 vw
  //     4 words → 10.5 vw
  //     5 words → 9.0 vw
  //     6+ words → 8.0 vw  (allows two-line wrapping at safe width)
  //
  //   Energy multiplier: energy 5 → +10%, energy 1 → −10%.
  //   Seed micro-variation: ±0.4 vw to avoid identical frames across scenes.

  var baseSizeTable = [0, 18.0, 15.0, 12.5, 10.5, 9.0, 8.0];
  var tableIdx      = Math.min(wordCount, baseSizeTable.length - 1);
  var baseSize      = baseSizeTable[tableIdx];

  // Energy nudge: ±10% spread over 5 levels
  var energyNudge = ((VD_ENERGY - 3) / 2) * 0.10;   // −0.10 to +0.10
  var baseAfterE  = baseSize * (1 + energyNudge);

  // Seed micro-variation (deterministic, not random)
  var seedMod  = ANIMATION_SEED % 100;
  var sizeVar  = ((seedMod % 10) - 5) * 0.08;   // ±0.4 vw

  var finalSize = Math.max(7.5, baseAfterE + sizeVar).toFixed(1);
  root.style.setProperty('--headline-size', finalSize + 'vw');

  // ── Seed-based halo position ───────────────────────────────────────────────

  var haloX = 44 + (seedMod % 12);
  root.style.setProperty('--halo-x', haloX + '%');

  // ── Background image ───────────────────────────────────────────────────────

  var bgEl = document.getElementById('bg');
  if (bgEl && BG_IMAGE) {
    bgEl.style.backgroundImage = "url('" + BG_IMAGE + "')";
    root.classList.add('has-bg');
  }

  // ── Label ──────────────────────────────────────────────────────────────────

  var labelEl = document.getElementById('label');
  if (labelEl) labelEl.textContent = LABEL_TEXT;

  // ── Headline — per-word animated spans ───────────────────────────────────
  //
  //   Structure built: .word-wrap > .word[.hl]
  //
  //   Each .word-wrap is an inline-block overflow:hidden clip boundary.
  //   Each .word slides up from 110% with staggered --word-delay.
  //   Highlighted words (.hl) use ease-back overshoot + glow pulse.
  //   Emphasis words (from VD.emphasis_words) are also highlighted.

  var emphasisSet = {};
  VD_EMPHASIS.forEach(function (ew) {
    emphasisSet[ew.toLowerCase().replace(/[^a-z0-9]/g, '')] = true;
  });

  var headlineEl = document.getElementById('headline');
  if (headlineEl) {
    headlineEl.innerHTML = words.map(function (word, i) {
      var normalised = word.toLowerCase().replace(/[^a-z0-9]/g, '');
      var isHl       = HIGHLIGHT_IDX.indexOf(i) !== -1 || emphasisSet[normalised];
      var wordClass  = 'word' + (isHl ? ' hl' : '');
      var delay      = (word0Delay + i * WORD_STAGGER * motionFactor).toFixed(3) + 's';

      // --word-delay is set as inline CSS custom property on the .word span.
      // This is picked up by the animation-delay in style.css:
      //   animation: wordReveal var(--dur-md) var(--word-delay, 0s) ...
      var wordSpan = '<span class="' + wordClass + '" style="--word-delay:' + delay + '">' +
                       word +
                     '</span>';
      return '<span class="word-wrap">' + wordSpan + '</span>';
    }).join('');
  }

  // ── Subhead ────────────────────────────────────────────────────────────────

  var subheadEl = document.getElementById('subhead');
  if (subheadEl && SUBHEAD) subheadEl.textContent = SUBHEAD;

  // ── Scene badge ────────────────────────────────────────────────────────────

  var badgeEl = document.getElementById('badge');
  if (badgeEl) badgeEl.textContent = String(SCENE_IDX + 1).padStart(2, '0');

  // ── Signal ready ───────────────────────────────────────────────────────────
  //
  //   Playwright waits for window.__SCENE_READY__ === true before capturing
  //   frames. We wait for:
  //     1. document.fonts.ready  — Noto Sans/CJK @font-face loaded
  //     2. Background image decoded (if present)
  //
  //   If the bg image 404s we revert has-bg so layout stays centred.

  document.fonts.ready.then(function () {
    if (BG_IMAGE) {
      var img      = new Image();
      img.onload   = function () { window.__SCENE_READY__ = true; };
      img.onerror  = function () {
        root.classList.remove('has-bg');
        window.__SCENE_READY__ = true;
      };
      img.src = BG_IMAGE;
    } else {
      window.__SCENE_READY__ = true;
    }
  });

})();
