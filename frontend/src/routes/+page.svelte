<!--
  Chat page — orquestra Header, EmptyState, mensagens e input.

  Fluxo:
    1. Msg do user aparece imediatamente
    2. Bolha "typing" como feedback (<100ms)
    3. API responde → substitui typing pela resposta real
    4. Auto-scroll suave
-->
<script lang="ts">
  import { tick, onMount, onDestroy } from 'svelte';
  import Header from '$lib/components/Header.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import ChatMessage from '$lib/components/ChatMessage.svelte';
  import ChatInput from '$lib/components/ChatInput.svelte';
  import { sendMessage } from '$lib/api';
  import type { ChatMessage as Msg } from '$lib/types';

  let messages: Msg[] = $state([]);
  let threadId: string | null = $state(null);
  let loading = $state(false);
  let scrollEl: HTMLDivElement | undefined = $state();
  let observer: MutationObserver | undefined;

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function scrollToEnd() {
    if (scrollEl) {
      scrollEl.scrollTop = scrollEl.scrollHeight;
    }
  }

  async function scrollBottom() {
    await tick();
    scrollToEnd();
  }

  onMount(() => {
    if (scrollEl) {
      observer = new MutationObserver(() => scrollToEnd());
      observer.observe(scrollEl, { childList: true, subtree: true, characterData: true });
    }
  });

  onDestroy(() => observer?.disconnect());

  function newChat() { messages = []; threadId = null; }

  function sleep(ms: number) {
    return new Promise(r => setTimeout(r, ms));
  }

  async function send(text: string) {
    if (loading) return;

    // 1. User message
    messages = [...messages, { id: uid(), role: 'user', content: text, timestamp: new Date() }];

    // 2. Thinking indicator
    const tid = uid();
    messages = [...messages, { id: tid, role: 'assistant', content: '__THINKING__', timestamp: new Date() }];
    loading = true;
    await scrollBottom();

    try {
      const data = await sendMessage(text, threadId);
      threadId = data.thread_id;

      const parts = data.answers && data.answers.length > 0
        ? data.answers
        : [data.answer || 'Sem resposta.'];

      // First message replaces thinking indicator
      messages = messages.map(m =>
        m.id === tid
          ? { id: tid, role: 'assistant' as const, content: parts[0], timestamp: new Date(), meta: data.meta }
          : m
      );
      await scrollBottom();

      // Remaining messages appear as separate bubbles with a delay
      for (let i = 1; i < parts.length; i++) {
        await sleep(600);
        messages = [...messages, { id: uid(), role: 'assistant' as const, content: parts[i], timestamp: new Date(), meta: data.meta }];
        await scrollBottom();
      }
    } catch (err) {
      messages = messages.map(m =>
        m.id === tid
          ? { id: tid, role: 'assistant' as const, content: `Desculpe, tive um problema ao buscar a resposta. Tente novamente em instantes. ${err instanceof Error ? err.message : ''}`.trim(), timestamp: new Date() }
          : m
      );
    } finally {
      loading = false;
      await scrollBottom();
    }
  }
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
</svelte:head>

<Header onNewChat={newChat} hasMessages={messages.length > 0} />

<main class="chat-area">
  <div class="messages" bind:this={scrollEl}>
    {#if messages.length === 0}
      <EmptyState onSuggestion={send} />
    {:else}
      <div class="messages-inner">
        {#each messages as msg (msg.id)}
          <ChatMessage message={msg} />
        {/each}
      </div>
    {/if}
  </div>

  <ChatInput onSend={send} disabled={loading} />
</main>

<style>
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 880px;
    width: 100%;
    margin: 0 auto;
    min-height: 0;
    overflow: hidden;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  .messages-inner {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1.5rem 1.5rem 1rem;
  }

  @media (max-width: 640px) {
    .messages-inner { padding: 1rem 0.75rem 0.75rem; gap: 1rem; }
  }
</style>
