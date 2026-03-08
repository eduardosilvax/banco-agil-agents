import type { ChatApiRequest, ChatApiResponse, HealthResponse } from './types';

function headers(): Record<string, string> {
  return { 'Content-Type': 'application/json' };
}

export async function sendMessage(
  message: string,
  threadId: string | null
): Promise<ChatApiResponse> {
  const body: ChatApiRequest = { message, thread_id: threadId };

  const res = await fetch(`/api/v1/chat`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => 'Erro desconhecido');
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return res.json() as Promise<ChatApiResponse>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`/api/v1/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json() as Promise<HealthResponse>;
}
