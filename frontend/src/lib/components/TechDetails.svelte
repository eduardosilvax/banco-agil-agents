<script lang="ts">
  import type { ResponseMeta } from '$lib/types';

  interface Props { meta: ResponseMeta; }
  let { meta }: Props = $props();

  let open = $state(false);

  function agentLabel(route: string): string {
    const map: Record<string, string> = {
      triage: 'Triagem',
      credit: 'Crédito',
      credit_interview: 'Entrevista de Crédito',
      exchange: 'Câmbio',
    };
    return map[route] || route;
  }
</script>

<div class="tech-details">
  <button class="toggle" onclick={() => (open = !open)}>
    <svg class="chevron" class:open width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M3 4.5L6 7.5L9 4.5"/>
    </svg>
    <span>Detalhes técnicos</span>
  </button>

  {#if open}
    <div class="details">
      <div class="row">
        <span class="label">Compliance</span>
        <span class="value" class:ok={meta.compliance_approved} class:blocked={!meta.compliance_approved}>
          {meta.compliance_approved ? '✓ Aprovado' : `✗ Bloqueado (${meta.compliance_reason})`}
        </span>
      </div>
      <div class="row">
        <span class="label">Agente</span>
        <span class="value">{agentLabel(meta.route)}</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .tech-details { margin-top: 0.5rem; }

  .toggle {
    display: flex; align-items: center; gap: 0.35rem;
    background: none; border: none; cursor: pointer; padding: 0.2rem 0;
    font-size: 0.72rem; color: var(--text-4); font-family: inherit;
    transition: color 180ms;
  }
  .toggle:hover { color: var(--text-2); }

  .chevron { transition: transform 180ms; }
  .chevron.open { transform: rotate(180deg); }

  .details {
    margin-top: 0.3rem; padding: 0.5rem 0.65rem;
    background: var(--surface-dark, rgba(0,0,0,0.05));
    border-radius: 6px; font-size: 0.75rem;
    display: flex; flex-direction: column; gap: 0.25rem;
  }

  .row { display: flex; justify-content: space-between; gap: 1rem; }
  .label { color: #a1a1aa; font-weight: 500; }
  .value { color: #e4e4e7; }
  .value.ok { color: #22c55e; }
  .value.blocked { color: #ef4444; }
</style>
