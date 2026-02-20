import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { AppLayout } from "./components/app-layout"
import { DeliveryList } from "./pages/deliveries/list"
import { DeliveryShow } from "./pages/deliveries/show"
import { TranscriptViewer } from "./pages/deliveries/transcript"

function Placeholder({ name }: { name: string }) {
  return <div className="text-lg">{name}</div>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/deliveries" replace />} />
          <Route path="deliveries" element={<DeliveryList />} />
          <Route path="deliveries/:id" element={<DeliveryShow />} />
          <Route path="deliveries/:id/runs/:runId/transcript" element={<TranscriptViewer />} />
          <Route path="sources" element={<Placeholder name="Sources" />} />
          <Route path="worker" element={<Placeholder name="Worker" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
