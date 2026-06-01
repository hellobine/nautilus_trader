import { useEffect, useState } from "react";
import { type DownloadJob, createDownload, listDownloads } from "../api/config";
import { createWsClient, type WsClient, type WsHandler } from "../api/ws";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

type WsFactory = (path: string, onMessage: WsHandler) => WsClient;

export function DownloadPanel({ wsFactory = createWsClient }: { wsFactory?: WsFactory }) {
  const [market, setMarket] = useState<"spot" | "futures">("spot");
  const [symbol, setSymbol] = useState("");
  const [intervals, setIntervals] = useState<string[]>(["1m"]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [jobs, setJobs] = useState<Record<string, DownloadJob>>({});

  useEffect(() => {
    listDownloads().then((list) => {
      const snapshot = Object.fromEntries(list.map((j) => [j.id, j]));
      // 合并：已有（含 ws 实时更新过的）任务优先，避免快照覆盖更新
      setJobs((prev) => ({ ...snapshot, ...prev }));
    }).catch(() => {});
    const client = wsFactory("/ws", (msg) => {
      const m = msg as { type?: string; job?: DownloadJob };
      if (m.type === "download_progress" && m.job) {
        setJobs((prev) => ({ ...prev, [m.job!.id]: m.job! }));
      }
    });
    return () => client.close();
    // 仅在挂载时拉取快照并订阅一次（wsFactory 可能为内联引用，不纳入依赖以免重复订阅）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleInterval = (itv: string) =>
    setIntervals((prev) => (prev.includes(itv) ? prev.filter((x) => x !== itv) : [...prev, itv]));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const job = await createDownload({ market, symbol, intervals, start, end });
    setJobs((prev) => ({ ...prev, [job.id]: job }));
  };

  return (
    <section>
      <h2>下载历史数据</h2>
      <form onSubmit={onSubmit}>
        <label htmlFor="mkt">市场</label>
        <select id="mkt" value={market} onChange={(e) => setMarket(e.target.value as "spot" | "futures")}>
          <option value="spot">现货</option>
          <option value="futures">合约(USDⓈ-M)</option>
        </select>
        <label htmlFor="sym">品种</label>
        <input id="sym" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <fieldset>
          <legend>周期</legend>
          {INTERVALS.map((itv) => (
            <label key={itv}>
              <input type="checkbox" checked={intervals.includes(itv)} onChange={() => toggleInterval(itv)} /> {itv}
            </label>
          ))}
        </fieldset>
        <label htmlFor="start">开始</label>
        <input id="start" value={start} onChange={(e) => setStart(e.target.value)} />
        <label htmlFor="end">结束</label>
        <input id="end" value={end} onChange={(e) => setEnd(e.target.value)} />
        <button type="submit">开始下载</button>
      </form>
      <table>
        <thead><tr><th>任务</th><th>状态</th><th>进度</th></tr></thead>
        <tbody>
          {Object.values(jobs).map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.status}</td>
              <td>{`${j.done} / ${j.total}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
