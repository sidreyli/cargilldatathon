const API_BASE = '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ─── Portfolio & Vessels ───────────────────────────────────

export const api = {
  getVessels: () => fetchJson<any[]>('/vessels'),
  getCargoes: () => fetchJson<any[]>('/cargoes'),
  getPortfolio: (useMLDelays: boolean = false) =>
    fetchJson<any>(`/portfolio/optimize?use_ml_delays=${useMLDelays}`),
  getAllVoyages: (useMLDelays: boolean = false) =>
    fetchJson<any[]>(`/portfolio/all-voyages?use_ml_delays=${useMLDelays}`),

  // Voyage
  calculateVoyage: (params: {
    vessel_name: string;
    cargo_name: string;
    use_eco_speed?: boolean;
    extra_port_delay?: number;
    bunker_adjustment?: number;
  }) => fetchJson<any>('/voyage/calculate', {
    method: 'POST',
    body: JSON.stringify(params),
  }),

  compareVoyages: (pairs: any[]) => fetchJson<any>('/voyage/compare', {
    method: 'POST',
    body: JSON.stringify({ pairs }),
  }),

  // Scenarios
  getBunkerSensitivity: () => fetchJson<any[]>('/scenario/bunker'),
  getDelaySensitivity: () => fetchJson<any[]>('/scenario/port-delay'),
  getChinaDelaySensitivity: () => fetchJson<any[]>('/scenario/china-port-delay'),
  getTippingPoints: () => fetchJson<any>('/scenario/tipping-points'),

  // ML
  getPortDelays: () => fetchJson<any[]>('/ml/port-delays'),
  getModelInfo: () => fetchJson<any>('/ml/model-info'),

  // Chat (non-streaming)
  chatSync: (message: string, history: any[] = []) =>
    fetchJson<{ response: string }>('/chat/sync', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    }),
};

// ─── SSE Chat Stream ───────────────────────────────────────

export async function* streamChat(
  message: string,
  history: any[] = [],
): AsyncGenerator<string, void, unknown> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });

  if (!res.ok || !res.body) {
    throw new Error('Chat stream failed');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.content) yield parsed.content;
        } catch {
          // Ignore parse errors
        }
      }
    }
  }
}
