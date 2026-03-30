<script>
  import { onMount } from 'svelte';
  import { game, loadGame, resetGame } from './stores/game.svelte.js';
  import GameIndex from './components/GameIndex.svelte';
  import ReplayView from './components/ReplayView.svelte';

  let currentGame = $state(null);

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
    resetGame();
    window.location.hash = '';
  }

  function readHash() {
    const hash = window.location.hash.replace('#/', '').replace('#', '').split('?')[0];
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

{#if currentGame && game.data}
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
