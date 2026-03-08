const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function uploadDocuments(files: File[]): Promise<any> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getDocuments(): Promise<any> {
  return apiFetch('/api/documents');
}

export async function getDashboardSummary(): Promise<any> {
  return apiFetch('/api/dashboard/summary');
}

export async function getCashFlow(): Promise<any> {
  return apiFetch('/api/dashboard/cashflow');
}

export async function getConsolidatedPortfolio(): Promise<any> {
  return apiFetch('/api/portfolio/consolidated');
}

export async function getPortfolioByBroker(): Promise<any> {
  return apiFetch('/api/portfolio/by-broker');
}

export async function getTransactions(params?: {
  page?: number;
  limit?: number;
  search?: string;
  institution?: string;
  type?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
}): Promise<any> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return apiFetch(`/api/transactions${query ? `?${query}` : ''}`);
}

export async function getAccounts(): Promise<any> {
  return apiFetch('/api/accounts');
}

export async function getPersons(): Promise<any> {
  return apiFetch('/api/persons');
}

export async function getSettings(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings`);
  return res.json();
}

export async function saveSettings(settings: Record<string, string>): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings }),
  });
  return res.json();
}

export async function testGmailConnection(email?: string, password?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings/gmail/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return res.json();
}

export async function searchGmail(params: {
  email?: string;
  password?: string;
  keywords?: string[];
  date_from?: string;
  date_to?: string;
  max_results?: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings/gmail/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function importFromGmail(filePaths: string[]): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings/gmail/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_paths: filePaths }),
  });
  return res.json();
}
