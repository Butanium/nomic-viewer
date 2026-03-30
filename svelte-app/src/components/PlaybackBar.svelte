<!--
  Playback controls: play/pause, step, seek, speed.
-->
<script>
  import { game, visibleEvents, SPEEDS,
           stepForward, stepBack, jumpForward, jumpBack, togglePlay, seekTo, speedUp, speedDown } from '../stores/game.svelte.js';
  import { shortTime } from '../lib/utils.js';

  let total = $derived(visibleEvents().length);
  let idx = $derived(game.currentIdx + 1);
  let pct = $derived(total > 0 ? (idx / total) * 100 : 0);
  function handleSeek(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    seekTo(fraction);
  }
</script>

<svelte:window onkeydown={(e) => {
  if (e.key === ' ' || e.key === 'k') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowRight' || e.key === 'l') { stepForward(); }
  else if (e.key === 'ArrowLeft' || e.key === 'j') { stepBack(); }
  else if (e.key === '+' || e.key === '=') { speedUp(); }
  else if (e.key === '-') { speedDown(); }
}} />

<div class="playback-bar">
  <div class="pb-controls">
    <button class="pb-btn" title="Rewind 30" onclick={jumpBack}>
      <svg width="14" height="10" viewBox="0 0 14 10"><path d="M7 0L0 5l7 5V0z" fill="currentColor"/><path d="M14 0L7 5l7 5V0z" fill="currentColor"/></svg>
    </button>
    <button class="pb-btn" title="Previous event" onclick={stepBack}>
      <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0" y="0" width="2" height="10" fill="currentColor"/><path d="M10 0L3 5l7 5V0z" fill="currentColor"/></svg>
    </button>
    <button class="pb-btn play" class:active={game.isPlaying} title="Play/Pause" onclick={togglePlay}>
      {#if game.isPlaying}
        <svg width="8" height="10" viewBox="0 0 8 10"><rect x="0" y="0" width="2.5" height="10" fill="currentColor"/><rect x="5.5" y="0" width="2.5" height="10" fill="currentColor"/></svg>
      {:else}
        <svg width="8" height="10" viewBox="0 0 8 10"><path d="M0 0l8 5-8 5V0z" fill="currentColor"/></svg>
      {/if}
    </button>
    <button class="pb-btn" title="Next event" onclick={stepForward}>
      <svg width="10" height="10" viewBox="0 0 10 10"><path d="M0 0l7 5-7 5V0z" fill="currentColor"/><rect x="8" y="0" width="2" height="10" fill="currentColor"/></svg>
    </button>
    <button class="pb-btn" title="Skip 30" onclick={jumpForward}>
      <svg width="14" height="10" viewBox="0 0 14 10"><path d="M0 0l7 5-7 5V0z" fill="currentColor"/><path d="M7 0l7 5-7 5V0z" fill="currentColor"/></svg>
    </button>
  </div>

  <div class="pb-time">{idx} / {total}</div>

  <div class="pb-track-wrap">
    <div class="pb-track" role="slider" tabindex="0" aria-valuenow={idx} aria-valuemin={1} aria-valuemax={total} onclick={handleSeek}
      onkeydown={(e) => { if (e.key === 'ArrowRight') stepForward(); else if (e.key === 'ArrowLeft') stepBack(); }}>
      <div class="pb-progress" style="width: {pct}%"></div>
    </div>
  </div>

  <div class="pb-event-count">{total} events</div>

  <div class="pb-speed-group">
    <button class="pb-speed-btn" onclick={speedDown}>−</button>
    <span class="pb-speed-label">{SPEEDS[game.speedIdx]}x</span>
    <button class="pb-speed-btn" onclick={speedUp}>+</button>
  </div>

</div>

<style>
  .playback-bar {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 20px;
    border-top: 1px solid var(--border);
    background: var(--bg); flex-shrink: 0; height: 48px;
  }
  .pb-controls { display: flex; align-items: center; gap: 3px; flex-shrink: 0; }
  .pb-btn {
    width: 28px; height: 28px;
    border: 1px solid var(--border); border-radius: 4px;
    background: var(--bg-raised); color: var(--text-dim);
    cursor: pointer; display: flex; align-items: center;
    justify-content: center; font-size: 12px; transition: all 0.15s;
  }
  .pb-btn:hover { background: var(--bg-hover); color: var(--text); }
  .pb-btn.active { background: var(--accent); color: var(--bg); border-color: var(--accent); }
  .pb-time {
    font-family: var(--font-mono); font-size: 11px;
    color: var(--text-dim); flex-shrink: 0; min-width: 50px;
  }
  .pb-track-wrap { flex: 1; }
  .pb-track {
    height: 6px; background: var(--bg-panel);
    border-radius: 3px; position: relative; cursor: pointer;
  }
  .pb-progress {
    height: 100%; background: var(--accent); border-radius: 3px;
    position: relative; transition: width 0.1s linear;
  }
  .pb-progress::after {
    content: ''; position: absolute; right: -4px; top: -2px;
    width: 10px; height: 10px; background: var(--text);
    border-radius: 50%; box-shadow: 0 0 4px rgba(0,0,0,0.5);
  }
  .pb-event-count {
    font-family: var(--font-mono); font-size: 10px;
    color: var(--text-muted); flex-shrink: 0;
  }
  .pb-speed-group {
    display: flex; align-items: center; gap: 2px; flex-shrink: 0;
  }
  .pb-speed-label {
    font-family: var(--font-mono); font-size: 10px;
    color: var(--text-dim); min-width: 32px; text-align: center;
  }
  .pb-speed-btn {
    font-size: 10px; padding: 4px 6px;
    border: 1px solid var(--border); border-radius: 4px;
    background: var(--bg-raised); color: var(--text-dim);
    cursor: pointer;
  }
  .pb-speed-btn:hover { color: var(--text); background: var(--bg-hover); }
</style>
