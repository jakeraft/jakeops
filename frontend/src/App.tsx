import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { AppLayout } from "./components/app-layout"

function Placeholder({ name }: { name: string }) {
  return <div className="text-lg">{name}</div>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/deliveries" replace />} />
          <Route path="deliveries" element={<Placeholder name="Deliveries" />} />
          <Route path="deliveries/:id" element={<Placeholder name="Delivery Detail" />} />
          <Route path="deliveries/:id/runs/:runId/transcript" element={<Placeholder name="Transcript" />} />
          <Route path="sources" element={<Placeholder name="Sources" />} />
          <Route path="worker" element={<Placeholder name="Worker" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
