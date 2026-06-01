import { useEffect, useState } from "react";
import { getLockStatus, unlock } from "../api/config";

export function UnlockGate({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => getLockStatus().then((s) => setUnlocked(s.unlocked)).catch(() => setUnlocked(false));
  useEffect(() => { refresh(); }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await unlock(pw);
      await refresh();
    } catch (err) {
      setError(String((err as { message?: string })?.message ?? "解锁失败"));
    }
  };

  if (unlocked === null) return <p>加载中…</p>;
  if (unlocked) return <>{children}</>;

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: 320 }}>
      <h2>解锁凭证库</h2>
      <label htmlFor="pw">主口令</label>
      <input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      <button type="submit">解锁</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </form>
  );
}
