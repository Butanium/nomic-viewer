<!--
  Index page: browse and select a game to replay.
-->
<script>
  import { onMount } from 'svelte';
  import { agentColor } from '../lib/utils.js';

  export let onSelect; // callback: (gameId) => void

  let games = [];
  let loaded = false;

  onMount(async () => {
    const resp = await fetch('data/games.json');
    games = await resp.json();
    loaded = true;
  });

  function formatDate(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function duration(start, end) {
    if (!start || !end) return '';
    const ms = new Date(end) - new Date(start);
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  function modelColor(model) {
    const map = { opus: 'var(--opus)', sonnet: 'var(--sonnet)', haiku: 'var(--haiku)' };
    return map[model] || 'var(--text-dim)';
  }
</script>

<div class="index">
  <header class="index-header">
    <h1>Nomic</h1>
    <p class="subtitle">AI agents playing the self-amending rule game</p>
  </header>

  {#if !loaded}
    <div class="loading">Loading games...</div>
  {:else}
    <div class="game-grid">
      {#each games as game, i}
        <button class="game-card" onclick={() => onSelect(game.game_id)} style="animation-delay: {i * 60}ms">
          <div class="card-header">
            <span class="game-num">{game.game_id.replace('game-', 'Game ')}</span>
            <span class="game-date">{formatDate(game.start_time)}</span>
          </div>

          <div class="card-players">
            {#each game.players as p}
              <div class="player-chip">
                <span class="player-dot" style="background: {modelColor(p.model)}"></span>
                <span class="player-name">{p.name}</span>
                <span class="player-model">{p.model}</span>
              </div>
            {/each}
          </div>

          <div class="card-stats">
            <span class="stat">{game.total_rounds} rounds</span>
            <span class="stat-sep">·</span>
            <span class="stat">{game.stats.total_messages} messages</span>
            <span class="stat-sep">·</span>
            <span class="stat">{duration(game.start_time, game.end_time)}</span>
          </div>

          {#if game.winner}
            <div class="card-winner">🏆 {game.winner}</div>
          {/if}

          <div class="card-arrow">→</div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .index {
    height: 100%; overflow-y: auto;
    display: flex; flex-direction: column;
    align-items: center;
    padding: 60px 24px 80px;
  }

  .index-header {
    text-align: center; margin-bottom: 48px;
  }

  h1 {
    font-family: var(--font-display);
    font-size: 52px; font-weight: 700;
    font-style: italic; letter-spacing: -0.03em;
    color: var(--text);
    margin-bottom: 8px;
    background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .subtitle {
    font-family: var(--font-mono);
    font-size: 13px; color: var(--text-muted);
    letter-spacing: 0.04em;
  }

  .loading {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--text-muted); padding: 40px;
  }

  .game-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
    width: 100%; max-width: 1100px;
  }

  .game-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    cursor: pointer;
    text-align: left;
    color: var(--text);
    font-family: var(--font-body);
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
    animation: cardIn 0.4s ease-out both;
  }

  .game-card:hover {
    border-color: var(--accent);
    background: var(--bg-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }

  .game-card:hover .card-arrow {
    opacity: 1; transform: translateX(0);
  }

  .card-header {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 14px;
  }

  .game-num {
    font-family: var(--font-display);
    font-size: 20px; font-weight: 600;
    font-style: italic; letter-spacing: -0.01em;
  }

  .game-date {
    font-family: var(--font-mono);
    font-size: 11px; color: var(--text-muted);
  }

  .card-players {
    display: flex; flex-direction: column; gap: 6px;
    margin-bottom: 14px;
  }

  .player-chip {
    display: flex; align-items: center; gap: 7px;
  }

  .player-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  }

  .player-name {
    font-size: 13px; font-weight: 500;
  }

  .player-model {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--text-muted);
    padding: 1px 4px; background: var(--bg);
    border-radius: 2px;
  }

  .card-stats {
    font-family: var(--font-mono);
    font-size: 11px; color: var(--text-muted);
  }

  .stat-sep { margin: 0 4px; opacity: 0.4; }

  .card-winner {
    font-family: var(--font-mono); font-size: 12px;
    color: var(--win); margin-top: 8px;
  }

  .card-arrow {
    position: absolute; right: 16px; top: 50%;
    transform: translateX(8px) translateY(-50%);
    font-size: 20px; color: var(--accent);
    opacity: 0; transition: all 0.2s ease;
  }

  @keyframes cardIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
