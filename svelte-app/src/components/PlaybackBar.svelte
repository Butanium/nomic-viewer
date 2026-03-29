<!--
  Playback controls: play/pause, step, seek, speed.
-->
<script>
  import { currentIdx, isPlaying, speedIdx, visibleEvents, SPEEDS,
           stepForward, stepBack, togglePlay, seekTo, cycleSpeed } from '../stores/game.js';
  import { shortTime } from '../lib/utils.js';

  $: total = $visibleEvents.length;
  $: idx = $currentIdx + 1;
  $: pct = total > 0 ? (idx / total) * 100 : 0;
  $: currentTs = $currentIdx >= 0 ? shortTime($visibleEvents[$currentIdx]?.timestamp) : '';

  function handleSeek(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    seekTo(fraction);
  }
</script>

<svelte:window on:keydown={(e) => {
  if (e.key === ' ' || e.key === 'k') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowRight' || e.key === 'l') { stepForward(); }
  else if (e.key === 'ArrowLeft' || e.key === 'j') { stepBack(); }
  else if (e.key === '+' || e.key === '=') { cycleSpeed(); }
}} />

<div class="playback-bar">
  <div class="pb-controls">
    <button class="pb-btn" title="Previous event" on:click={stepBack}>⏮</button>
    <button class="pb-btn" class:active={$isPlaying} title="Play/Pause" on:click={togglePlay}>
      {$isPlaying ? '⏸' : '▶'}
    </button>
    <button class="pb-btn" title="Next event" on:click={stepForward}>⏭</button>
  </div>

  <div class="pb-time">{idx} / {total}</div>

  <div class="pb-track-wrap">
    <div class="pb-track" on:click={handleSeek}>
      <div class="pb-progress" style="width: {pct}%"></div>
    </div>
  </div>

  <div class="pb-event-count">{total} events</div>

  <button class="pb-speed" on:click={cycleSpeed}>{SPEEDS[$speedIdx]}x</button>
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
  .pb-speed {
    font-family: var(--font-mono); font-size: 10px;
    padding: 4px 8px; border: 1px solid var(--border);
    border-radius: 4px; background: var(--bg-raised);
    color: var(--text-dim); cursor: pointer; flex-shrink: 0;
  }
  .pb-speed:hover { color: var(--text); background: var(--bg-hover); }
</style>
