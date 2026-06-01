import { useEffect, useState } from "react";
import { type CatalogEntry, listCatalog } from "../api/config";

export function CatalogBrowser() {
  const [entries, setEntries] = useState<CatalogEntry[]>([]);
  useEffect(() => { listCatalog().then(setEntries).catch(() => setEntries([])); }, []);

  return (
    <section>
      <h2>数据目录</h2>
      {entries.length === 0 ? (
        <p>暂无数据</p>
      ) : (
        <table>
          <thead>
            <tr><th>Bar 类型</th><th>起</th><th>止</th><th>数量</th></tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.bar_type}>
                <td>{e.bar_type}</td>
                <td>{e.start ?? "-"}</td>
                <td>{e.end ?? "-"}</td>
                <td>{e.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
