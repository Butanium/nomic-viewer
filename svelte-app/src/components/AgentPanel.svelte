<!--
  A single agent's column in the replay view.
  Shows their events (thinking, messages, tool calls) and incoming messages.
-->
<script>
  import { game, agentFeeds, agentStatuses } from '../stores/game.svelte.js';
  import { agentColor } from '../lib/utils.js';
  import ChatMessage from './ChatMessage.svelte';
  import AgentEvent from './AgentEvent.svelte';

  let { name, model = '' } = $props();

  import { tick } from 'svelte';

  let feedEl = $state(null);
  let shouldScroll = $state(true);

  let color = $derived(agentColor(game.data, name));
  let isActive = $derived((agentStatuses()[name] || 'idle') !== 'idle');

  function onScroll() {
    if (feedEl) {
      shouldScroll = feedEl.scrollHeight - feedEl.scrollTop - feedEl.clientHeight < 60;
    }
  }

  $effect(() => {
    agentFeeds();
    if (feedEl && shouldScroll) {
      tick().then(() => { if (feedEl) feedEl.scrollTop = feedEl.scrollHeight; });
    }
  });
</script>

<div class="agent-col">
  <div class="agent-col-header">
    <div class="agent-identity">
      <div class="agent-dot" class:active={isActive} style="background: {color}"></div>
      <span class="agent-name-label" style="color: {color}">{name}</span>
      <span class="agent-model">{model}</span>
    </div>
    <div class="agent-status" style="color: {isActive ? 'var(--for)' : 'var(--text-muted)'}">{agentStatuses()[name] || 'idle'}</div>
  </div>
  <div class="agent-col-body" bind:this={feedEl} onscroll={onScroll}>
    {#each (agentFeeds()[name] || []) as evt, i (i + ':' + evt.timestamp + evt.type)}
      {#if evt.type === 'message'}
        <ChatMessage {evt} variant="agent" />
      {:else if evt.type === 'received_message'}
        <ChatMessage evt={{...evt, source: evt.from, _incoming: true}} variant="agent" />
      {:else}
        <AgentEvent {evt} />
      {/if}
    {/each}
  </div>
</div>

<style>
  .agent-col {
    flex: 1; display: flex; flex-direction: column;
    border-right: 1px solid var(--border-subtle);
    min-width: 0;
  }
  .agent-col:last-child { border-right: none; }
  .agent-col-header {
    padding: 7px 10px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex; align-items: center;
    justify-content: space-between;
    flex-shrink: 0; background: var(--bg-raised);
  }
  .agent-identity { display: flex; align-items: center; gap: 6px; }
  .agent-dot {
    width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  }
  .agent-dot.active { animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .agent-name-label { font-weight: 600; font-size: 11px; }
  .agent-model {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--text-muted); padding: 1px 4px;
    background: var(--bg); border-radius: 2px;
  }
  .agent-status { font-family: var(--font-mono); font-size: 10px; }
  .agent-col-body {
    flex: 1; overflow-y: auto; padding: 8px;
    display: flex; flex-direction: column; gap: 5px;
  }
</style>
