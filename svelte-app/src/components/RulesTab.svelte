<!--
  Rules tab: shows game_rules.md reconstructed at the current playback position.
  The last applied edit is shown as a diff.
-->
<script>
  import { marked } from 'marked';
  import { currentRules } from '../stores/game.js';

  $: content = $currentRules.content;
  $: lastEdit = $currentRules.lastEdit;

  // Split content into: before-diff, added, after-diff
  // If there's a lastEdit, highlight what was added
  $: diffParts = (() => {
    if (!lastEdit || !content) return { before: content, added: '', after: '' };

    if (lastEdit.tool === 'Write') {
      // Full file write — show all as "new"
      return { before: '', added: content, after: '' };
    }

    // Edit: the new_string replaced old_string. The added portion is new_string minus old_string.
    const newStr = lastEdit.new_string || '';
    const oldStr = lastEdit.old_string || '';

    // Find where new_string appears in current content
    const idx = content.indexOf(newStr);
    if (idx === -1) return { before: content, added: '', after: '' };

    // The "added" part is what's in new_string but not in old_string
    // Simple approach: if new_string starts with old_string, the diff is the remainder
    let addedText = '';
    if (newStr.startsWith(oldStr)) {
      addedText = newStr.slice(oldStr.length);
    } else if (newStr.endsWith(oldStr)) {
      addedText = newStr.slice(0, newStr.length - oldStr.length);
    } else {
      // Full replacement — show entire new_string as the diff
      addedText = newStr;
    }

    const addIdx = content.indexOf(addedText);
    if (addIdx === -1) return { before: content, added: '', after: '' };

    return {
      before: content.slice(0, addIdx),
      added: addedText,
      after: content.slice(addIdx + addedText.length),
    };
  })();
</script>

<div class="rules-tab">
  {#if !content}
    <div class="empty">No rules data yet — advance playback past the initial file read.</div>
  {:else}
    <div class="rules-content">
      {#if diffParts.added}
        <div class="rules-text">{@html marked(diffParts.before)}</div>
        <div class="rules-diff">{@html marked(diffParts.added)}</div>
        <div class="rules-text">{@html marked(diffParts.after)}</div>
      {:else}
        <div class="rules-text">{@html marked(content)}</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .rules-tab {
    flex: 1; padding: 20px 28px; overflow-y: auto; max-width: 850px;
  }
  .empty {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--text-muted); padding: 40px; text-align: center;
  }
  .rules-content {
    font-size: 13px; line-height: 1.6; color: var(--text);
  }
  .rules-text :global(h1) {
    font-family: var(--font-display); font-size: 22px;
    font-weight: 500; margin: 20px 0 12px; color: var(--text);
  }
  .rules-text :global(h2) {
    font-family: var(--font-display); font-size: 17px;
    font-weight: 500; margin: 16px 0 8px; color: var(--text-dim);
  }
  .rules-text :global(h3) {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--accent); margin: 12px 0 4px;
  }
  .rules-diff {
    background: #0d1a0d; border-left: 3px solid var(--for);
    padding: 8px 12px; margin: 4px 0; border-radius: 4px;
    animation: diffFlash 2s ease-out;
  }
  .rules-diff :global(h3) {
    font-family: var(--font-mono); font-size: 13px;
    color: var(--for); margin: 12px 0 4px;
  }
  @keyframes diffFlash {
    0% { background: #1a3a1a; }
    100% { background: #0d1a0d; }
  }
</style>
