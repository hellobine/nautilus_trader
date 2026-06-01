import { Link, Outlet } from "react-router-dom";
import { useHealth } from "../api/useHealth";

const NAV = [
  { to: "/config", label: "连接配置" },
  { to: "/backtest", label: "回测分析" },
  { to: "/research", label: "数据研究" },
  { to: "/live", label: "实盘监控" },
  { to: "/control", label: "策略控制" },
];

export function Layout() {
  const { health } = useHealth();
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav style={{ width: 180, padding: 16, borderRight: "1px solid #ddd" }}>
        <h2>QuantDeck</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {NAV.map((n) => (
            <li key={n.to} style={{ margin: "8px 0" }}>
              <Link to={n.to}>{n.label}</Link>
            </li>
          ))}
        </ul>
        <div style={{ marginTop: 24, fontSize: 12 }}>
          后端：{health ? `已连接 (nautilus ${health.nautilus.version})` : "连接中…"}
        </div>
      </nav>
      <main style={{ flex: 1, padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
