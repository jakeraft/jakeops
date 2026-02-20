import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { AppLayout } from "./components/app-layout"
import { DeliveryList } from "./pages/deliveries/list"
import { DeliveryShow } from "./pages/deliveries/show"
import { TranscriptViewer } from "./pages/deliveries/transcript"
import { SourceList } from "./pages/sources/list"
import { WorkerStatusPage } from "./pages/worker/status"
import { DeliveryBoard } from "./pages/deliveries/board"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/deliveries" replace />} />
          <Route path="deliveries" element={<DeliveryList />} />
          <Route path="deliveries/:id" element={<DeliveryShow />} />
          <Route path="deliveries/:id/runs/:runId/transcript" element={<TranscriptViewer />} />
          <Route path="sources" element={<SourceList />} />
          <Route path="worker" element={<WorkerStatusPage />} />
          <Route path="board" element={<DeliveryBoard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
