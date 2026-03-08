<script lang="ts">
  import type { ChatMessage } from '$lib/types';
  import TechDetails from './TechDetails.svelte';

  interface Props { message: ChatMessage; }
  let { message }: Props = $props();

  const isUser = $derived(message.role === 'user');

  function ts(d: Date) {
    if (typeof d === 'string') d = new Date(d);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  function getAgentName(agentId?: string): string {
    if (!agentId) return '';
    const map: Record<string, string> = {
      'triage': '(Triagem)',
      'credit': '(Crédito)',
      'credit_interview': '(Entrevista de Crédito)',
      'exchange': '(Câmbio)'
    };
    return map[agentId] || '';
  }
</script>

<div class="msg" class:user={isUser} class:bot={!isUser}>
  <div class="avatar" class:avatar-user={isUser} class:avatar-bot={!isUser}>
    {#if isUser}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
      </svg>
    {:else}
      <span class="avatar-logo">BA</span>
    {/if}
  </div>

  <div class="bubble">
    <div class="sender">
      <span class="name">{isUser ? 'Você' : `Banco Ágil ${getAgentName(message.current_agent)}`}</span>
      <span class="time">{ts(message.timestamp)}</span>
    </div>

    <div class="content">
      {#if message.content === '__THINKING__'}
        <div class="typing">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      {:else}
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        {@html renderMarkdown(message.content)}
      {/if}
    </div>

    {#if !isUser && message.meta}
      <TechDetails meta={message.meta} />
    {/if}
  </div>
</div>

<script lang="ts" module>
  function renderMarkdown(text: string): string {
    let html = text
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code class="inline">$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
      .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^---$/gm, '<hr/>')
      .replace(/^\d+\.\s+(.+)$/gm, '<li class="ol">$1</li>')
      .replace(/^[-•] (.+)$/gm, '<li>$1</li>');

    // Agrupar <li> em <ul> e limpar quebras de linha extras dentro da lista
    html = html.replace(/((?:<li[^>]*>.*<\/li>\s*)+)/g, (match) => {
      return '<ul>' + match.replace(/\n/g, '') + '</ul>';
    });

    // Converter \n\n em separador de parágrafo e \n em quebra simples
    html = html.replace(/\n\n+/g, '<div class="para-break"></div>');
    html = html.replace(/\n/g, '<br/>');

    // Limpar <br/> e para-break redundantes ao redor de blocos
    html = html.replace(/<(?:br\s*\/?>|div class="para-break"><\/div>)\s*(<\/?(?:ul|li|h[2-4]|hr|pre))/g, '$1');
    html = html.replace(/(<\/(?:ul|li|h[2-4]|hr|pre)>)\s*<(?:br\s*\/?>|div class="para-break"><\/div>)/g, '$1');

    return html;
  }
</script>

<style>
  .msg { display: flex; gap: 0.75rem; max-width: 85%; animation: fade-up 280ms var(--ease) both; }
  .msg.user  { align-self: flex-end; flex-direction: row-reverse; }
  .msg.bot   { align-self: flex-start; }

  .avatar {
    width: 30px; height: 30px; border-radius: var(--r-sm);
    display: grid; place-items: center; flex-shrink: 0; margin-top: 2px;
  }
  .avatar-user { background: var(--surface-dark); color: var(--brand); }
  .avatar-bot { background: var(--brand); color: #fff; }
  .avatar-logo { font-size: 0.7rem; font-weight: 800; letter-spacing: 0.04em; }

  .bubble { flex: 1; min-width: 0; }

  .sender { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.3rem; }
  .name { font-size: 0.78rem; font-weight: 600; color: var(--text-1); }
  .time { font-size: 0.66rem; color: var(--text-4); }

  .msg.user .sender { flex-direction: row-reverse; }
  .msg.user .name { color: var(--text-2); }

  .content { padding: 0.8rem 1rem; border-radius: var(--r-md); font-size: 0.9rem; line-height: 1.65; color: var(--text-1); }
  .msg.bot .content { background: var(--surface-0); border: 1px solid var(--border-1); border-top-left-radius: 3px; box-shadow: var(--shadow-xs); }
  .msg.user .content { background: var(--surface-dark); color: var(--text-inv); border-top-right-radius: 3px; }

  .typing { display: flex; align-items: center; gap: 4px; padding: 0.4rem 0.2rem; }
  .dot { width: 6px; height: 6px; background: var(--text-3); border-radius: 50%; animation: blink 1.4s infinite both; }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes fade-up { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes blink { 0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1); } }
  
  :global(.content p) { margin: 0 0 0.4rem 0; }
  :global(.content p:last-child) { margin-bottom: 0; }
  :global(.content strong) { font-weight: 600; color: inherit; }
  :global(.content ul) { margin: 0.4rem 0; padding-left: 1.2rem; list-style-position: outside; }
  :global(.content li) { margin-bottom: 0.2rem; }
  :global(.content .para-break) { height: 0.6rem; }
</style>
