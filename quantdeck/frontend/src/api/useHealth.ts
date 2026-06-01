import { useEffect, useState } from "react";
import { apiGet } from "./client";

export interface Health {
  status: string;
  nautilus: { available: boolean; version: string | null; error: string | null };
}

export function useHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Health>("/api/health")
      .then(setHealth)
      .catch((e) => setError(String(e?.message ?? e)));
  }, []);

  return { health, error };
}
