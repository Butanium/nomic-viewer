<!--
  Renders a single message event in an agent panel.
  Handles outgoing (sent), incoming (received), and public chat variants.
-->
<script>
  import { gameData } from '../stores/game.js';
  import { agentColor, shortTime, renderMarkdown } from '../lib/utils.js';

  export let evt;
  export let variant = 'agent'; // 'agent' | 'public'

  let expanded = false;

  $: incoming = evt._incoming;
  $: isBroadcast = evt.is_broadcast;
  $: isDM = !isBroadcast && evt.to !== 'team-lead';
  $: isPlayerDM = isDM && evt.to !== 'clerk' && evt.source !== 'clerk';
  $: truncated = variant !== 'public' && !isPlayerDM && evt.content.length > 200;
  $: color = agentColor($gameData, evt.source);
  $: toColor = agentColor($gameData, evt.to);
</script>

{#if variant === 'public'}
  <div class="chat-msg" style="border-left-color: {color}">
    <div class="sender" style="color: {color}">
      {evt.source}
      {#if $gameData}
        {@const model = $gameData.players.find(p => p.name === evt.source)?.model}
        {#if model}<span class="badge">{model}</span>{/if}
      {/if}
      <span class="ts">{shortTime(evt.timestamp)}</span>
    </div>
    <div
      class="body evt-msg-text"
      class:truncated={truncated && !expanded}
      on:click={() => truncated && (expanded = !expanded)}
    >{@html renderMarkdown(evt.content)}</div>
  </div>
{:else if incoming}
  <div class="evt evt-msg-in" style="border-left-color: {color}">
    <div class="evt-msg-sender" style="color: {color}">
      {evt.source}
      {#if isDM}<span class="dm-label">DM</span>{/if}
      <span class="ts">{shortTime(evt.timestamp)}</span>
    </div>
    <div
      class="evt-msg-text"
      class:truncated={truncated && !expanded}
      on:click={() => truncated && (expanded = !expanded)}
    >{@html renderMarkdown(evt.content)}</div>
  </div>
{:else}
  <div class="evt evt-msg-out" class:dm={isDM}>
    <div class="evt-msg-meta">
      {#if isDM}
        <span class="dm-label">DM</span> → <span style="color: {toColor}">{evt.to}</span>
      {:else if evt.to === 'team-lead'}
        → <span style="color: var(--clerk)">clerk</span>
      {:else}
        → broadcast
      {/if}
      · {shortTime(evt.timestamp)}
    </div>
    <div
      class="evt-msg-text"
      class:truncated={truncated && !expanded}
      on:click={() => truncated && (expanded = !expanded)}
    >{@html renderMarkdown(evt.content)}</div>
  </div>
{/if}

<style>
  .chat-msg {
    border-radius: 5px; padding: 7px 10px;
    border-left: 3px solid var(--border);
    background: var(--bg-panel);
    animation: fadeIn 0.2s ease-out;
  }
  .sender {
    font-weight: 600; font-size: 11px; margin-bottom: 2px;
    display: flex; align-items: center; gap: 5px;
  }
  .badge {
    font-family: var(--font-mono); font-size: 9px; font-weight: 400;
    padding: 0px 4px; border-radius: 2px;
    background: var(--bg-panel); color: var(--text-muted);
  }
  .ts {
    font-family: var(--font-mono); font-size: 9px;
    font-weight: 300; color: var(--text-muted);
  }
  .body {
    font-size: 12px; line-height: 1.5;
    color: var(--text);
  }

  .evt { border-radius: 4px; padding: 6px 8px; animation: fadeIn 0.2s ease-out; }

  .evt-msg-out {
    background: var(--bg-panel); padding: 5px 8px;
    margin-left: 20px; border-radius: 6px 2px 6px 6px;
    border-right: 2px solid var(--text-muted);
  }
  .evt-msg-out.dm { border-right-color: var(--against); }

  .evt-msg-in {
    background: var(--bg-panel); padding: 5px 8px;
    margin-right: 20px; border-radius: 2px 6px 6px 6px;
    border-left: 2px solid var(--border);
  }
  .evt-msg-sender {
    font-size: 10px; font-weight: 600; margin-bottom: 1px;
  }

  .evt-msg-meta {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--text-muted); margin-bottom: 2px; text-align: right;
  }
  .dm-label { color: var(--against); font-weight: 500; }

  .evt-msg-text {
    font-size: 12px; line-height: 1.4; color: var(--text);
  }
  .evt-msg-text.truncated {
    max-height: 10.8em; overflow: hidden; cursor: pointer;
    position: relative;
  }
  .evt-msg-text.truncated::after {
    content: '...';
    position: absolute; bottom: 0; right: 0;
    padding-left: 16px;
    background: linear-gradient(to right, transparent, var(--bg-panel) 40%);
    color: var(--text-muted);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(3px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
