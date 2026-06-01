import { useEffect, useState } from "react";
import {
  type ConnectionStatus,
  type ExchangeOut,
  deleteExchange,
  listExchanges,
  putExchange,
  testExchange,
} from "../api/config";

export function ExchangeCredentials() {
  const [items, setItems] = useState<ExchangeOut[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [testnet, setTestnet] = useState(false);
  const [status, setStatus] = useState<Record<string, ConnectionStatus>>({});

  const refresh = () => listExchanges().then(setItems).catch(() => setItems([]));
  useEffect(() => { refresh(); }, []);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await putExchange("binance", { api_key: apiKey, api_secret: apiSecret, testnet });
    setApiKey(""); setApiSecret("");
    await refresh();
  };

  const onTest = async (name: string) => {
    const s = await testExchange(name);
    setStatus((prev) => ({ ...prev, [name]: s }));
  };

  return (
    <section>
      <h2>交易所凭证（Binance）</h2>
      <table>
        <tbody>
          {items.map((it) => (
            <tr key={it.name}>
              <td>{it.name}</td>
              <td>{it.api_key}</td>
              <td>{it.testnet ? "testnet" : "mainnet"}</td>
              <td><button onClick={() => onTest(it.name)}>测试连接</button></td>
              <td>{status[it.name] ? (status[it.name].ok ? "✅ " : "❌ ") + status[it.name].message : ""}</td>
              <td><button onClick={async () => { await deleteExchange(it.name); await refresh(); }}>删除</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={onSave}>
        <div>
          <label htmlFor="ak">API Key</label>
          <input id="ak" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </div>
        <div>
          <label htmlFor="as">API Secret</label>
          <input id="as" type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} />
        </div>
        <label>
          <input type="checkbox" checked={testnet} onChange={(e) => setTestnet(e.target.checked)} /> testnet
        </label>
        <button type="submit">保存</button>
      </form>
    </section>
  );
}
