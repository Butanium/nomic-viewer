<!--
  Public chat panel showing all broadcast messages.
-->
<script>
  import { tick } from 'svelte';
  import { publicChatEvents } from '../stores/game.svelte.js';
  import ChatMessage from './ChatMessage.svelte';

  let feedEl = $state(null);
  let shouldScroll = $state(true);

  function onScroll() {
    if (feedEl) {
      shouldScroll = feedEl.scrollHeight - feedEl.scrollTop - feedEl.clientHeight < 60;
    }
  }

  $effect(() => {
    publicChatEvents();
    if (feedEl && shouldScroll) {
      tick().then(() => { if (feedEl) feedEl.scrollTop = feedEl.scrollHeight; });
    }
  });
</script>

<div class="public-chat">
  <div class="panel-header">Public Chat</div>
  <div class="feed" bind:this={feedEl} onscroll={onScroll}>
    {#each publicChatEvents() as evt, i (i + ':' + evt.timestamp + evt.source)}
      <ChatMessage {evt} variant="public" />
    {/each}
  </div>
</div>

<style>
  .public-chat {
    width: 320px; min-width: 260px;
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    background: var(--bg);
  }
  .panel-header {
    padding: 8px 14px;
    border-bottom: 1px solid var(--border-subtle);
    font-family: var(--font-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-muted); flex-shrink: 0;
  }
  .feed {
    flex: 1; overflow-y: auto;
    padding: 10px; display: flex;
    flex-direction: column; gap: 6px;
  }
</style>
