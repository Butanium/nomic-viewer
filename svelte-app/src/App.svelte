<script>
  import { onMount } from 'svelte';
  import { gameData, currentIdx, loadGame } from './stores/game.js';
  import GameIndex from './components/GameIndex.svelte';
  import ReplayView from './components/ReplayView.svelte';

  let currentGame = null; // null = index, string = game id

  function gameIdToPath(id) {
    return `data/${id}.json`;
  }

  function selectGame(gameId) {
    currentGame = gameId;
    window.location.hash = `/${gameId}`;
    loadGame(gameIdToPath(gameId));
  }

  function goBack() {
    currentGame = null;
    gameData.set(null);
    currentIdx.set(-1);
    window.location.hash = '';
  }

  // Read hash on load and on hash change
  function readHash() {
    const hash = window.location.hash.replace('#/', '').replace('#', '');
    if (hash && hash.startsWith('game-')) {
      currentGame = hash;
      loadGame(gameIdToPath(hash));
    } else {
      currentGame = null;
    }
  }

  onMount(() => {
    readHash();
    window.addEventListener('hashchange', readHash);
    return () => window.removeEventListener('hashchange', readHash);
  });
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
