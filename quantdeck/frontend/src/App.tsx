import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import {
  BacktestPage,
  ConfigPage,
  ControlPage,
  LivePage,
  ResearchPage,
} from "./pages";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/config" replace />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/control" element={<ControlPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
