<!--
  Game Log tab: shows game_log.md reconstructed at the current playback position.
  Rendered as markdown, no diff highlighting.
-->
<script>
  import { marked } from 'marked';
  import { currentGameLog } from '../stores/game.svelte.js';

  let content = $derived(currentGameLog().content);
</script>

<div class="gamelog-tab">
  {#if !content}
    <div class="empty">No game log data yet — advance playback past the initial file read.</div>
  {:else}
    <div class="gamelog-content">{@html marked(content)}</div>
  {/if}
</div>

<style>
  .gamelog-tab {
    flex: 1; padding: 20px 28px; overflow-y: auto; max-width: 850px;
  }
  .empty {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--text-muted); padding: 40px; text-align: center;
  }
  .gamelog-content {
    font-size: 13px; line-height: 1.6; color: var(--text);
  }
  .gamelog-content :global(h1) {
    font-family: var(--font-display); font-size: 22px;
    font-weight: 500; margin: 20px 0 12px; color: var(--text);
  }
  .gamelog-content :global(h2) {
    font-family: var(--font-display); font-size: 17px;
    font-weight: 500; margin: 16px 0 8px; color: var(--text-dim);
  }
  .gamelog-content :global(h3) {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--accent); margin: 12px 0 4px;
  }
</style>
