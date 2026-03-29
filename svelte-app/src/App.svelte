<script>
  import { gameData, currentIdx, loadGame } from './stores/game.js';
  import GameIndex from './components/GameIndex.svelte';
  import ReplayView from './components/ReplayView.svelte';

  let currentGame = null; // null = index, string = game path

  // Check URL params on load
  const params = new URLSearchParams(window.location.search);
  const urlGame = params.get('game');
  if (urlGame) {
    selectGame(urlGame);
  }

  function selectGame(path) {
    currentGame = path;
    loadGame(path);
  }

  function goBack() {
    currentGame = null;
    gameData.set(null);
    currentIdx.set(-1);
    // Clear URL param
    window.history.replaceState({}, '', window.location.pathname);
  }
</script>

{#if currentGame && $gameData}
  <ReplayView onBack={goBack} />
{:else if currentGame}
  <div class="loading">Loading game...</div>
{:else}
  <GameIndex onSelect={selectGame} />
{/if}

<style>
  .loading {
    display: flex; align-items: center; justify-content: center;
    height: 100%;
    font-family: var(--font-mono); font-size: 14px;
    color: var(--text-muted);
  }
</style>
