<!--
  Interactive tutorial overlay for the Nomic game replay viewer.
  Walks users through game rules and UI via spotlight + explanation cards.
-->
<script>
  import { game, visibleEvents, advanceTo } from '../stores/game.svelte.js';

  let { visible = $bindable(false) } = $props();

  let step = $state(0);
  let spotlightRect = $state(null);
  let cardStyle = $state('');
  let transitioning = $state(false);
  let cardEl = $state(null);

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
    },
    {
      target: '.clerk-panel',
      text: "The Clerk is a neutral administrator \u2014 it manages turns, verifies votes, and updates scores. You can toggle its panel from the topbar.",
      action: () => { game.clerkOpen = true; },
    },
    {
      target: '.playback-bar',
      text: "Use the playback controls to watch the game unfold. Play/pause with Space, step with arrow keys, and drag the progress bar to jump around.",
      action: () => { game.clerkOpen = false; },
      needsScroll: true,
    },
    {
      target: '.tab-btn:nth-child(2)',
      text: "The Rules tab shows the current ruleset, updated live as rules change during the game.",
      action: () => { game.activeTab = 'rules'; },
    },
    {
      target: '.tab-btn:nth-child(3)',
      text: "The Game Log tracks every round's results \u2014 proposals, votes, scores.",
      action: () => { game.activeTab = 'gamelog'; },
    },
    {
      target: null,
      text: "That's it! Press Play to watch the game unfold, or step through events one at a time. Enjoy watching the AIs play politics.",
      action: () => { game.activeTab = 'replay'; },
    },
  ];

  let totalSteps = STEPS.length;

  function measureAndPosition(el) {
    const r = el.getBoundingClientRect();
    const pad = 6;
    spotlightRect = {
      x: r.left - pad,
      y: r.top - pad,
      w: r.width + pad * 2,
      h: r.height + pad * 2,
    };
    positionCard(spotlightRect);
  }

  function updateSpotlight() {
    const s = STEPS[step];
    if (!s.target) {
      spotlightRect = null;
      positionCard(null);
      return;
    }
    const el = document.querySelector(s.target);
    if (!el) {
      spotlightRect = null;
      positionCard(null);
      return;
    }
    if (s.needsScroll) {
      el.scrollIntoView({ block: 'center', behavior: 'instant' });
      // Wait for scroll to settle before measuring
      requestAnimationFrame(() => measureAndPosition(el));
    } else {
      measureAndPosition(el);
    }
  }

  function positionCard(rect) {
    if (!rect) {
      cardStyle = 'top: 50%; left: 50%; transform: translate(-50%, -50%);';
      return;
    }

    // Measure actual card dimensions, with a minimum floor to prevent clipping
    // when cardEl hasn't fully rendered yet
    const cardW = Math.max(cardEl ? cardEl.offsetWidth : 360, 360);
    const cardH = Math.max(cardEl ? cardEl.offsetHeight : 220, 220);
    const gap = 16;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Try right of spotlight
    let x = rect.x + rect.w + gap;
    let y = rect.y + rect.h / 2 - cardH / 2;

    // If overflows right, try left
    if (x + cardW > vw - 20) {
      x = rect.x - cardW - gap;
    }

    // If overflows left, try below
    if (x < 20) {
      x = rect.x + rect.w / 2 - cardW / 2;
      y = rect.y + rect.h + gap;
    }

    // If overflows bottom, try above
    if (y + cardH > vh - 20) {
      y = rect.y - cardH - gap;
    }

    // Clamp
    x = Math.max(20, Math.min(x, vw - cardW - 20));
    y = Math.max(20, Math.min(y, vh - cardH - 20));

    cardStyle = `top: ${y}px; left: ${x}px;`;
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
    if (step > 0) goTo(step - 1);
  }

  function close() {
    visible = false;
    step = 0;
    spotlightRect = null;
    localStorage.setItem('nomic-tutorial-seen', '1');
    // Restore replay tab
    game.activeTab = 'replay';
  }

  // When tutorial becomes visible, set up initial state
  $effect(() => {
    if (visible) {
      step = 0;
      // Ensure we're on replay tab with clerk open and at a good position
      game.activeTab = 'replay';
      game.clerkOpen = true;
      // Jump to event 500 for rich state
      const events = visibleEvents();
      if (events.length > 0) {
        advanceTo(Math.min(499, events.length - 1));
      }
      // Wait for DOM to settle
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          updateSpotlight();
        });
      });
    }
  });

  // Register capture-phase keydown to intercept before PlaybackBar
  $effect(() => {
    if (visible) {
      window.addEventListener('keydown', onKeydown, true);
      return () => window.removeEventListener('keydown', onKeydown, true);
    }
  });

  // Recalculate on window resize
  function onResize() {
    if (visible) updateSpotlight();
  }

  // Keyboard navigation
  // Use capture phase to intercept keyboard events before PlaybackBar's window listener
  function onKeydown(e) {
    if (!visible) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(); }
    else if (e.key === 'ArrowRight' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopImmediatePropagation(); next(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopImmediatePropagation(); back(); }
  }

  let clipPath = $derived.by(() => {
    if (!spotlightRect) return 'none';
    const r = spotlightRect;
    const vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
    const vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
    // polygon that covers the whole viewport with a rectangular hole
    return `polygon(
      0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%,
      ${r.x}px ${r.y}px,
      ${r.x}px ${r.y + r.h}px,
      ${r.x + r.w}px ${r.y + r.h}px,
      ${r.x + r.w}px ${r.y}px,
      ${r.x}px ${r.y}px
    )`;
  });
</script>

<svelte:window onresize={onResize} />

{#if visible}
  <!-- Overlay with cutout -->
  <div
    class="tutorial-overlay"
    class:no-cutout={!spotlightRect}
    style={spotlightRect ? `clip-path: ${clipPath};` : ''}
    onclick={close}
    role="presentation"
  ></div>

  <!-- Spotlight glow border -->
  {#if spotlightRect}
    <div
      class="spotlight-ring"
      style="top: {spotlightRect.y}px; left: {spotlightRect.x}px; width: {spotlightRect.w}px; height: {spotlightRect.h}px;"
    ></div>
  {/if}

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
    background: rgba(0, 0, 0, 0.72);
    z-index: 1000;
    transition: clip-path 0.35s ease;
  }
  .tutorial-overlay.no-cutout {
    clip-path: none;
  }

  .spotlight-ring {
    position: fixed;
    z-index: 1001;
    border-radius: 6px;
    border: 1.5px solid var(--accent);
    box-shadow: 0 0 20px rgba(196, 160, 255, 0.25), inset 0 0 20px rgba(196, 160, 255, 0.05);
    pointer-events: none;
    transition: all 0.35s ease;
  }

  .tutorial-card {
    position: fixed;
    z-index: 1002;
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
