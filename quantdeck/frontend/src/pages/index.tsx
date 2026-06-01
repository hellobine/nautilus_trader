import { UnlockGate } from "../components/UnlockGate";
import { ExchangeCredentials } from "../components/ExchangeCredentials";
import { CatalogBrowser } from "../components/CatalogBrowser";
import { DownloadPanel } from "../components/DownloadPanel";
import type { WsClient, WsHandler } from "../api/ws";

function Placeholder({ title }: { title: string }) {
  return (
    <section>
      <h1>{title}</h1>
      <p>该模块将在后续计划中实现。</p>
    </section>
  );
}

export function ConfigPage({
  wsFactory,
}: {
  wsFactory?: (path: string, onMessage: WsHandler) => WsClient;
}) {
  return (
    <UnlockGate>
      <h1>连接与配置管理</h1>
      <ExchangeCredentials />
      <CatalogBrowser />
      <DownloadPanel wsFactory={wsFactory} />
    </UnlockGate>
  );
}
export const BacktestPage = () => <Placeholder title="回测分析" />;
export const ResearchPage = () => <Placeholder title="数据研究" />;
export const LivePage = () => <Placeholder title="实盘监控" />;
export const ControlPage = () => <Placeholder title="策略控制" />;
