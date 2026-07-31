// 坐席工作台 API 客户端（T062）：令牌持久化 + 注入 Authorization 头。
const TOKEN_KEY = "ai_cs_agent_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`/api/v1${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    let code = String(res.status);
    try {
      code = (await res.json())?.detail?.code || code;
    } catch {
      /* ignore */
    }
    throw new Error(code);
  }
  return res.json();
}

export async function login(username: string, password: string) {
  const data = await api<{ token: string; agent: any; tenant: any }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.token);
  return data;
}
