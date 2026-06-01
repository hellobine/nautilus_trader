export interface ApiError {
  code: string;
  message: string;
  detail?: unknown;
}

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) {
    let err: ApiError = { code: "http_error", message: resp.statusText };
    try {
      err = await resp.json();
    } catch {
      /* 保留默认错误 */
    }
    throw err;
  }
  return (await resp.json()) as T;
}

async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let err: ApiError = { code: "http_error", message: resp.statusText };
    try {
      const j = await resp.json();
      err = j.detail ?? j;
    } catch {
      /* 保留默认错误 */
    }
    throw err;
  }
  return (await resp.json()) as T;
}

export const apiPost = <T>(path: string, body?: unknown) => send<T>(path, "POST", body);
export const apiPut = <T>(path: string, body?: unknown) => send<T>(path, "PUT", body);
export const apiDelete = <T>(path: string) => send<T>(path, "DELETE");
