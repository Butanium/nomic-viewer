<!--
  Interactive tutorial overlay for the Nomic game replay viewer.
  Walks users through game rules and UI via z-index spotlight + explanation cards.

  Approach: instead of clip-path cutouts (which break under CSS zoom / viewport
  transforms), we elevate the target element above a simple dark overlay using
  z-index + box-shadow glow. No coordinate math needed for the spotlight itself.
-->
<script>
  import { game, visibleEvents, advanceTo } from '../stores/game.svelte.js';

  let { visible = $bindable(false), onBack = null } = $props();

  let step = $state(0);
  let cardStyle = $state('');
  let transitioning = $state(false);
  let cardEl = $state(null);
  let currentTarget = $state(null);

  const STEPS = [
    {
      target: null,
      text: "Welcome to Nomic \u2014 a game where AI agents negotiate rule changes. Three Claude models (Opus, Sonnet, Haiku) play against each other, proposing new rules, debating, and voting. The first to 100 points wins. Let's see how to follow a game.",
    },
    {
      target: '.scoreboard',
      text: "The scoreboard shows each player's current score and which round we're in. Players earn points from successful proposals and dice rolls.",
    },
    {
      target: '.public-chat',
      text: "The public chat shows all broadcast messages \u2014 proposals, debates, and vote results. This is what everyone at the table hears.",
    },
    {
      target: '.agent-panels .agent-col:first-child',
      text: "Each player has their own panel showing everything from their perspective: their messages (sent and received), tool calls, and private strategy notes.",
    },
    {
      target: '.agent-panels .agent-col:first-child .evt-msg-out',
      text: "Messages the player sent appear on the right side, with a border on the right edge. Broadcasts, DMs, and clerk messages all show up here.",
      needsScroll: true,
    },
    {
      target: '.agent-panels .agent-col:first-child .evt-msg-in',
      text: "Messages received from other players appear on the left side, with the sender's color. They show at the moment the player actually saw them.",
      needsScroll: true,
      action: () => { game.activeTab = 'replay'; game.clerkOpen = true; },
    },
    {
      target: '.clerk-panel',
      text: "The Clerk is a neutral administrator \u2014 it manages turns, verifies votes, and updates scores. You can toggle its panel from the topbar.",
      action: () => { game.activeTab = 'replay'; game.clerkOpen = true; },
    },
    {
      target: '.playback-bar',
      text: "Use the playback controls to watch the game unfold. Play/pause with Space, step with arrow keys, and drag the progress bar to jump around.",
      action: () => { game.activeTab = 'replay'; game.clerkOpen = false; },
      needsScroll: true,
    },
    {
      target: '.tab-btn:nth-child(2)',
      text: "The Rules tab shows the current ruleset, updated live as rules change during the game.",
      action: () => { game.activeTab = 'rules'; game.clerkOpen = false; },
    },
    {
      target: '.tab-btn:nth-child(3)',
      text: "The Game Log tracks every round's results \u2014 proposals, votes, scores.",
      action: () => { game.activeTab = 'gamelog'; game.clerkOpen = false; },
    },
    {
      target: null,
      text: "That's it! Press Play to watch the game unfold, or step through events one at a time. Enjoy watching the AIs play politics.",
      action: () => { game.activeTab = 'replay'; game.clerkOpen = true; },
    },
  ];

  let totalSteps = STEPS.length;

  /** Apply spotlight styles directly to a DOM element, elevating it above the overlay. */
  function highlightElement(selector) {
    // Clean up previous target
    if (currentTarget) {
      currentTarget.style.removeProperty('z-index');
      currentTarget.style.removeProperty('position');
      currentTarget.style.removeProperty('outline');
      currentTarget.style.removeProperty('outline-offset');
      currentTarget.style.removeProperty('pointer-events');
    }

    if (!selector) {
      currentTarget = null;
      positionCard(null);
      return;
    }

    const el = document.querySelector(selector);
    if (!el) {
      currentTarget = null;
      positionCard(null);
      return;
    }

    // Elevate above the overlay (z-index 999)
    el.style.zIndex = '1000';
    if (getComputedStyle(el).position === 'static') {
      el.style.position = 'relative';
    }
    el.style.outline = '3px solid var(--accent)';
    el.style.outlineOffset = '-3px';
    el.style.pointerEvents = 'auto';
    currentTarget = el;

    positionCard(el);
  }

  /** Position the explanation card near the target element. */
  function positionCard(el) {
    if (!el) {
      cardStyle = 'top: 50%; left: 50%; transform: translate(-50%, -50%);';
      return;
    }

    // CSS zoom inflates getBoundingClientRect() values and window.innerWidth/Height,
    // but position: fixed top/left operates in CSS (unzoomed) space. Divide by zoom.
    const zoom = parseFloat(getComputedStyle(document.body).zoom) || 1;
    const rawRect = el.getBoundingClientRect();
    const rect = {
      top: rawRect.top / zoom,
      left: rawRect.left / zoom,
      right: rawRect.right / zoom,
      bottom: rawRect.bottom / zoom,
      width: rawRect.width / zoom,
      height: rawRect.height / zoom,
    };
    const cardW = Math.max(cardEl ? cardEl.offsetWidth : 360, 360);
    const cardH = Math.max(cardEl ? cardEl.offsetHeight : 220, 220);
    const gap = 16;
    const vw = window.innerWidth / zoom;
    const vh = window.innerHeight / zoom;

    // Try right of target
    let x = rect.right + gap;
    let y = rect.top + rect.height / 2 - cardH / 2;

    // If overflows right, try left
    if (x + cardW > vw - 20) {
      x = rect.left - cardW - gap;
    }

    // If overflows left, place below
    if (x < 20) {
      x = rect.left + rect.width / 2 - cardW / 2;
      y = rect.bottom + gap;
    }

    // If overflows bottom, place above
    if (y + cardH > vh - 20) {
      y = rect.top - cardH - gap;
    }

    // If still overflows (target near bottom AND tall card), center vertically
    if (y < 20 || y + cardH > vh - 20) {
      y = (vh - cardH) / 2;
      x = rect.left - cardW - gap;
      if (x < 20) x = rect.right + gap;
    }

    // Clamp to viewport
    x = Math.max(20, Math.min(x, vw - cardW - 20));
    y = Math.max(20, Math.min(y, vh - cardH - 20));

    cardStyle = `top: ${y}px; left: ${x}px;`;
  }

  function updateSpotlight() {
    const s = STEPS[step];
    if (!s.target) {
      highlightElement(null);
      return;
    }
    const el = document.querySelector(s.target);
    if (el && s.needsScroll) {
      el.scrollIntoView({ block: 'center', behavior: 'instant' });
      requestAnimationFrame(() => highlightElement(s.target));
    } else {
      highlightElement(s.target);
    }
  }

  function goTo(newStep) {
    transitioning = true;
    step = newStep;
    const s = STEPS[step];
    if (s.action) s.action();
    // If step has an action (tab switch, clerk open/close), wait for CSS
    // transitions to complete before measuring (margin-right 0.25s = 250ms)
    const delay = s.action ? 300 : 0;
    setTimeout(() => {
      requestAnimationFrame(() => {
        updateSpotlight();
        transitioning = false;
      });
    }, delay);
  }

  function next() {
    if (step < totalSteps - 1) goTo(step + 1);
    else close();
  }

  function back() {
    if (step > 0) {
      goTo(step - 1);
    } else if (onBack) {
      close();
      onBack();
    }
  }

  /** Remove all inline styles from current target and reset state. */
  function cleanup() {
    if (currentTarget) {
      currentTarget.style.removeProperty('z-index');
      currentTarget.style.removeProperty('position');
      currentTarget.style.removeProperty('outline');
      currentTarget.style.removeProperty('outline-offset');
      currentTarget.style.removeProperty('pointer-events');
      currentTarget = null;
    }
  }

  function close() {
    cleanup();
    visible = false;
    step = 0;
    localStorage.setItem('nomic-tutorial-seen', '1');
    game.activeTab = 'replay';
  }

  // When tutorial becomes visible, set up initial state
  $effect(() => {
    if (visible) {
      step = 0;
      game.activeTab = 'replay';
      game.clerkOpen = true;
      const events = visibleEvents();
      if (events.length > 0) {
        advanceTo(Math.min(499, events.length - 1));
      }
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          updateSpotlight();
        });
      });
    }
  });

  // Capture-phase keydown to intercept before PlaybackBar
  $effect(() => {
    if (visible) {
      window.addEventListener('keydown', onKeydown, true);
      return () => window.removeEventListener('keydown', onKeydown, true);
    }
  });

  // Recalculate card position on resize
  function onResize() {
    if (visible && currentTarget) positionCard(currentTarget);
  }

  function onKeydown(e) {
    if (!visible) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(); }
    else if (e.key === 'ArrowRight' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopImmediatePropagation(); next(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopImmediatePropagation(); back(); }
  }
</script>

<svelte:window onresize={onResize} />

{#if visible}
  <!-- Dark overlay — simple full-viewport, no clip-path -->
  <div class="tutorial-overlay" onclick={close} role="presentation"></div>

  <!-- Explanation card -->
  <div class="tutorial-card" style={cardStyle} class:transitioning bind:this={cardEl}>
    <div class="card-step">{step + 1} / {totalSteps}</div>
    <div class="card-text">{STEPS[step].text}</div>
    <div class="card-nav">
      {#if step > 0}
        <button class="nav-btn" onclick={back}>&larr; Back</button>
      {:else}
        <div></div>
      {/if}
      <button class="nav-btn skip" onclick={close}>Skip</button>
      <button class="nav-btn primary" onclick={next}>
        {step < totalSteps - 1 ? 'Next \u2192' : 'Done'}
      </button>
    </div>
  </div>
{/if}

<style>
  .tutorial-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 999;
  }

  .tutorial-card {
    position: fixed;
    z-index: 1001;
    width: 360px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    transition: top 0.35s ease, left 0.35s ease, opacity 0.2s ease;
  }
  .tutorial-card.transitioning {
    opacity: 0.7;
  }

  .card-step {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--accent);
    margin-bottom: 10px;
    letter-spacing: 0.05em;
  }

  .card-text {
    font-family: var(--font-body);
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--text);
    margin-bottom: 18px;
  }

  .card-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .nav-btn {
    font-family: var(--font-mono);
    font-size: 11px;
    padding: 6px 14px;
    border-radius: 5px;
    border: 1px solid var(--border);
    background: var(--bg-raised);
    color: var(--text-dim);
    cursor: pointer;
    transition: all 0.15s;
  }
  .nav-btn:hover {
    background: var(--bg-hover);
    color: var(--text);
  }
  .nav-btn.skip {
    color: var(--text-muted);
    border-color: transparent;
    background: transparent;
  }
  .nav-btn.skip:hover {
    color: var(--text-dim);
  }
  .nav-btn.primary {
    background: var(--accent);
    color: var(--bg);
    border-color: var(--accent);
    font-weight: 500;
  }
  .nav-btn.primary:hover {
    opacity: 0.9;
  }
</style>
