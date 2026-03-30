<!--
  Renders a single non-message event in an agent panel:
  thinking, text, tool_call, file_edit.
-->
<script>
  import { shortTime, escapeHtml, renderMarkdown } from '../lib/utils.js';

  export let evt;

  function toolDetail(evt) {
    if (evt.tool === 'commit') return evt.result ? `→ ${evt.result}` : '';
    if (evt.tool === 'roll_dice') return evt.result || '';
    if (evt.tool === 'verify' || evt.tool === 'verify_proposal') return evt.result ? evt.result.slice(0, 80) : '';
    if (evt.tool === 'propose') return 'proposal submitted';
    if (evt.tool === 'contact_supervisor') return 'notified supervisor';
    if (evt.tool === 'agent') return evt.input?.description || evt.input?.name || '';
    if (evt.tool === 'teamcreate') return evt.input?.team_name || '';
    if (evt.tool === 'commit_all') return (evt.input?.message || evt.result || '').slice(0, 80);
    return evt.description || '';
  }

  function fileDiff(evt) {
    if (evt.old_string && evt.new_string) {
      const added = evt.new_string.replace(evt.old_string, '').trim();
      return added ? added.slice(0, 200) : '';
    }
    return evt.content ? evt.content.slice(0, 200) : '';
  }

  $: isNote = evt.type === 'tool_call' && (evt.tool === 'write_note' || evt.tool === 'append_note');
</script>

{#if evt.type === 'thinking'}
  <div class="evt evt-thinking">
    <div class="evt-thinking-label">{shortTime(evt.timestamp)}</div>
    <div class="evt-thinking-text">{evt.content}</div>
  </div>

{:else if evt.type === 'compaction'}
  <div class="evt evt-compaction">
    <span class="compaction-icon">↻</span> context compacted · {shortTime(evt.timestamp)}
  </div>

{:else if evt.type === 'text'}
  <div class="evt evt-text">{@html renderMarkdown(evt.content)}</div>

{:else if isNote}
  <div class="evt evt-note">
    <div class="evt-note-label">
      {evt.tool === 'append_note' ? '📝 appended' : '📝 wrote'} {evt.filename || ''} · {shortTime(evt.timestamp)}
    </div>
    <div class="evt-note-text">{(evt.content || evt.input?.content || '').slice(0, 500)}</div>
  </div>

{:else if evt.type === 'tool_call'}
  <div class="evt evt-tool" class:error={evt.is_error}>
    <span class="tool-name">{evt.tool}</span>
    <span class="tool-detail">{toolDetail(evt)}</span>
  </div>

{:else if evt.type === 'file_edit'}
  <div class="evt evt-file-edit">
    <div class="evt-file-label">{evt.tool} {evt.filename || ''} · {shortTime(evt.timestamp)}</div>
    {#if fileDiff(evt)}
      <div class="evt-file-diff"><span class="added">+ {fileDiff(evt)}</span></div>
    {/if}
  </div>
{/if}

<style>
  .evt { border-radius: 4px; padding: 6px 8px; animation: fadeIn 0.2s ease-out; }

  .evt-thinking { background: #14101c; border: 1px solid #221a30; }
  .evt-thinking-label {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--accent); opacity: 0.6; margin-bottom: 3px;
  }
  .evt-thinking-label::before { content: '◆ '; font-size: 7px; }
  .evt-thinking-text {
    font-size: 12px; line-height: 1.45;
    color: var(--text); opacity: 0.85; font-style: italic;
  }

  .evt-text {
    background: var(--bg-panel);
    font-size: 12px; line-height: 1.45; color: var(--text);
  }

  .evt-compaction {
    font-family: var(--font-mono); font-size: 10px;
    color: var(--opus); text-align: center;
    padding: 6px; border-top: 1px dashed var(--opus);
    border-bottom: 1px dashed var(--opus);
    opacity: 0.7;
  }
  .compaction-icon { font-size: 12px; }

  .evt-tool {
    font-family: var(--font-mono); font-size: 10px;
    padding: 4px 7px; background: var(--bg-panel);
    border-radius: 3px; color: var(--text-dim);
    display: flex; align-items: flex-start; gap: 5px;
  }
  .tool-name { color: var(--accent); font-weight: 500; }
  .tool-detail { color: var(--text-muted); word-break: break-word; }
  .evt-tool.error { border-left: 2px solid var(--against); }
  .evt-tool.error .tool-name { color: var(--against); }

  .evt-note { background: #111514; border: 1px dashed #1e2e2a; border-radius: 4px; }
  .evt-note-label {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--for); opacity: 0.6; margin-bottom: 3px;
  }
  .evt-note-text {
    font-family: var(--font-mono); font-size: 10px;
    line-height: 1.4; color: var(--text); opacity: 0.75;
    white-space: pre-wrap; max-height: 100px; overflow-y: auto;
  }

  .evt-file-edit { background: var(--bg-panel); border-left: 2px solid var(--opus); }
  .evt-file-label {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--opus); margin-bottom: 2px;
  }
  .evt-file-diff {
    font-family: var(--font-mono); font-size: 10px;
    line-height: 1.4; max-height: 80px; overflow-y: auto;
  }
  .added { color: var(--for); }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(3px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
