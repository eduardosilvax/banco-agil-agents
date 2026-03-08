export interface ChatApiRequest {
  message: string;
  thread_id: string | null;
}

export interface ResponseMeta {
  compliance_approved: boolean;
  compliance_reason: string | null;
  route: string;
  llm_metrics: Record<string, number> | null;
}

export interface ChatApiResponse {
  answer: string;
  answers: string[];
  thread_id: string;
  current_agent: string;
  meta: ResponseMeta | null;
}

export interface HealthResponse {
  status: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  current_agent?: string;
  meta?: ResponseMeta | null;
}
