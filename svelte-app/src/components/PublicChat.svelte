<!--
  Public chat panel showing all broadcast messages.
-->
<script>
  import { afterUpdate } from 'svelte';
  import { publicChatEvents } from '../stores/game.js';
  import ChatMessage from './ChatMessage.svelte';

  let feedEl;

  afterUpdate(() => {
    if (feedEl) feedEl.scrollTop = feedEl.scrollHeight;
  });
</script>

<div class="public-chat">
  <div class="panel-header">Public Chat</div>
  <div class="feed" bind:this={feedEl}>
    {#each $publicChatEvents as evt (evt.timestamp + evt.source + (evt.tool_use_id || ''))}
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
