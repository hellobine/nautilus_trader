import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface LockStatus {
  unlocked: boolean;
  initialized: boolean;
}
export interface ExchangeOut {
  name: string;
  api_key: string;
  testnet: boolean;
}
export interface ConnectionStatus {
  ok: boolean;
  message: string;
  latency_ms: number;
}
export interface CatalogEntry {
  instrument_id: string;
  bar_type: string;
  start: string | null;
  end: string | null;
  count: number;
}
export interface DownloadRequest {
  market: "spot" | "futures";
  symbol: string;
  intervals: string[];
  start: string;
  end: string;
}
export interface DownloadJob {
  id: string;
  request: DownloadRequest;
  status: "pending" | "running" | "done" | "error" | "cancelled";
  done: number;
  total: number;
  message: string;
  created_at: string;
}

export const getLockStatus = () => apiGet<LockStatus>("/api/lock-status");
export const unlock = (passphrase: string) => apiPost<{ unlocked: boolean }>("/api/unlock", { passphrase });
export const listExchanges = () => apiGet<ExchangeOut[]>("/api/exchanges");
export const putExchange = (name: string, body: { api_key: string; api_secret: string; testnet: boolean }) =>
  apiPut<{ ok: boolean }>(`/api/exchanges/${name}`, body);
export const deleteExchange = (name: string) => apiDelete<{ ok: boolean }>(`/api/exchanges/${name}`);
export const testExchange = (name: string) => apiPost<ConnectionStatus>(`/api/exchanges/${name}/test`);
export const listCatalog = () => apiGet<CatalogEntry[]>("/api/catalog");
export const createDownload = (req: DownloadRequest) => apiPost<DownloadJob>("/api/downloads", req);
export const listDownloads = () => apiGet<DownloadJob[]>("/api/downloads");
