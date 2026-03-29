<!--
  Full replay view for a single game.
  Includes topbar, scoreboard, panels, clerk drawer, playback bar.
-->
<script>
  import { gameData, clerkOpen, activeTab, agentFeeds, agentStatuses, loadGame, currentIdx, visibleEvents, currentScores } from '../stores/game.js';
  import { agentColor, shortTime } from '../lib/utils.js';
  import PublicChat from './PublicChat.svelte';
  import AgentPanel from './AgentPanel.svelte';
  import AgentEvent from './AgentEvent.svelte';
  import ChatMessage from './ChatMessage.svelte';
  import PlaybackBar from './PlaybackBar.svelte';
  import RulesTab from './RulesTab.svelte';
  import GameLogTab from './GameLogTab.svelte';

  export let onBack; // callback to return to index

  let clerkFeedEl;

  $: title = $gameData ? $gameData.meta.game_id.replace('game-', 'Game ') : '';
  $: players = $gameData?.players || [];
  $: clerk = $gameData?.clerk;
  $: clerkEvents = $agentFeeds['clerk'] || [];
  $: clerkStatus = $agentStatuses['clerk'] || 'idle';
  $: currentTs = $currentIdx >= 0 && $visibleEvents[$currentIdx]
    ? shortTime($visibleEvents[$currentIdx].timestamp)
    : '';

  function switchTab(tab) { activeTab.set(tab); }

  $: if (clerkFeedEl && clerkEvents.length) {
    setTimeout(() => { if (clerkFeedEl) clerkFeedEl.scrollTop = clerkFeedEl.scrollHeight; }, 0);
  }
</script>

<!-- Top Bar -->
<div class="topbar" class:clerk-open={$clerkOpen}>
  <div class="topbar-left">
    <button class="back-btn" on:click={onBack}>←</button>
    <h1>Nomic <span>{title}</span></h1>
    <div class="tab-bar">
      <button class="tab-btn" class:active={$activeTab === 'replay'} on:click={() => switchTab('replay')}>Replay</button>
      <button class="tab-btn" class:active={$activeTab === 'rules'} on:click={() => switchTab('rules')}>Rules</button>
      <button class="tab-btn" class:active={$activeTab === 'gamelog'} on:click={() => switchTab('gamelog')}>Game Log</button>
    </div>
  </div>
  <div class="topbar-right">
    <div class="round-indicator">
      {#if $currentScores.round > 0}
        Round <strong>{$currentScores.round}</strong>
        {#if $currentScores.result} · {$currentScores.result}{/if}
        ·
      {/if}
      {#if currentTs}
        <span style="color: var(--text-muted)">{currentTs} UTC</span>
      {/if}
    </div>
    {#if !$clerkOpen}
      <button class="clerk-toggle-topbar" on:click={() => clerkOpen.set(true)}>Clerk</button>
    {/if}
  </div>
</div>

<!-- Scoreboard -->
<div class="scoreboard" class:clerk-open={$clerkOpen}>
  {#if $currentScores.round > 0}
    <span class="round-badge">R{$currentScores.round}</span>
  {/if}
  {#each players as p}
    <div class="score-chip">
      <div class="dot" style="background: {agentColor($gameData, p.name)}"></div>
      <span class="name">{p.name}</span>
      <span class="pts" style="color: {agentColor($gameData, p.name)}">{$currentScores.scores[p.name] ?? 0}</span>
    </div>
  {/each}
  {#if $currentScores.winner}
    <span class="winner-badge">🏆 {$currentScores.winner}</span>
  {/if}
</div>

<!-- Main Area -->
<div class="main-area" class:clerk-open={$clerkOpen}>
  {#if $activeTab === 'replay'}
    <div class="replay-layout">
      <PublicChat />
      <div class="agent-panels">
        {#each players as p}
          <AgentPanel name={p.name} model={p.model} />
        {/each}
      </div>
    </div>
  {:else if $activeTab === 'rules'}
    <RulesTab />
  {:else if $activeTab === 'gamelog'}
    <GameLogTab />
  {/if}
</div>

<!-- Clerk Panel -->
{#if $clerkOpen}
  <div class="clerk-panel">
    <div class="clerk-panel-header">
      <div class="clerk-panel-label">
        <span class="dot"></span>
        Clerk
        {#if clerk}<span class="model">{clerk.model}</span>{/if}
      </div>
      <button class="clerk-close" on:click={() => clerkOpen.set(false)}>&times;</button>
    </div>
    <div class="agent-col-body" bind:this={clerkFeedEl}>
      {#each clerkEvents as evt (evt.timestamp + evt.type + (evt.tool_use_id || ''))}
        {#if evt.type === 'message'}
          <ChatMessage {evt} variant="agent" />
        {:else}
          <AgentEvent {evt} />
        {/if}
      {/each}
    </div>
  </div>
{/if}

<!-- Playback Bar -->
<div class:clerk-open={$clerkOpen}>
  <PlaybackBar />
</div>

<style>
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 20px; height: 44px;
    border-bottom: 1px solid var(--border);
    background: var(--bg); flex-shrink: 0;
    transition: margin-right 0.25s ease;
  }
  .topbar-left { display: flex; align-items: center; gap: 14px; }
  .back-btn {
    font-size: 16px; color: var(--text-muted); cursor: pointer;
    border: none; background: none; padding: 4px 8px;
    border-radius: 4px; transition: all 0.15s;
  }
  .back-btn:hover { color: var(--text); background: var(--bg-hover); }
  h1 {
    font-family: var(--font-display); font-size: 17px;
    font-weight: 600; font-style: italic; letter-spacing: -0.02em;
  }
  h1 span {
    color: var(--text-muted); font-style: normal;
    font-weight: 300; font-size: 13px;
  }
  .tab-bar {
    display: flex; gap: 2px;
    background: var(--bg-raised); border-radius: 6px; padding: 2px;
  }
  .tab-btn {
    font-family: var(--font-mono); font-size: 11px;
    padding: 5px 14px; border-radius: 4px; border: none;
    background: transparent; color: var(--text-muted);
    cursor: pointer; transition: all 0.15s;
  }
  .tab-btn:hover { color: var(--text-dim); }
  .tab-btn.active { background: var(--bg-panel); color: var(--text); }
  .topbar-right { display: flex; align-items: center; gap: 16px; }
  .round-indicator { font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); }
  .clerk-toggle-topbar {
    font-family: var(--font-mono); font-size: 10px;
    padding: 4px 10px; border: 1px solid var(--border);
    border-radius: 4px; background: var(--bg-raised);
    color: var(--clerk); cursor: pointer; transition: all 0.15s;
  }
  .clerk-toggle-topbar:hover { background: var(--bg-hover); color: var(--text); }

  .scoreboard {
    display: flex; align-items: center;
    padding: 6px 20px; gap: 24px;
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-raised);
    flex-shrink: 0; height: 36px;
    transition: margin-right 0.25s ease;
  }
  .score-chip { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 12px; }
  .score-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
  .score-chip .name { color: var(--text-dim); }
  .score-chip .pts { font-weight: 500; min-width: 20px; }
  .round-badge {
    font-family: var(--font-mono); font-size: 10px;
    color: var(--accent); background: var(--bg);
    padding: 2px 6px; border-radius: 3px;
  }
  .winner-badge {
    font-family: var(--font-mono); font-size: 11px;
    color: var(--win);
  }

  .main-area {
    flex: 1; display: flex; overflow: hidden;
    transition: margin-right 0.25s ease;
  }
  .replay-layout { display: flex; flex: 1; overflow: hidden; }
  .agent-panels { flex: 1; display: flex; overflow: hidden; }

  .clerk-panel {
    position: fixed; top: 0; right: 0; bottom: 0;
    width: 260px;
    border-left: 1px solid var(--border);
    display: flex; flex-direction: column;
    background: var(--bg); z-index: 50;
  }
  .clerk-panel-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 10px; height: 44px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0; background: var(--bg);
  }
  .clerk-panel-label {
    display: flex; align-items: center; gap: 6px;
    font-family: var(--font-mono); font-size: 10px; color: var(--clerk);
  }
  .clerk-panel-label .dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--clerk);
  }
  .clerk-panel-label .model {
    color: var(--text-muted); font-size: 9px;
    padding: 1px 4px; background: var(--bg-raised); border-radius: 2px;
  }
  .clerk-close {
    font-size: 16px; color: var(--text-muted); cursor: pointer;
    border: none; background: none; padding: 2px 6px; line-height: 1;
  }
  .clerk-close:hover { color: var(--text); }
  .agent-col-body {
    flex: 1; overflow-y: auto; padding: 8px;
    display: flex; flex-direction: column; gap: 5px;
  }

  .clerk-open { margin-right: 260px; }
</style>
