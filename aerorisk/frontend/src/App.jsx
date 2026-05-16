import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import FleetReadiness from './pages/FleetReadiness'
import CriticalParts from './pages/CriticalParts'
import SupplierRisk from './pages/SupplierRisk'
import MaintenanceRisk from './pages/MaintenanceRisk'
import AIRecommendations from './pages/AIRecommendations'
import ExecutiveSummary from './pages/ExecutiveSummary'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<FleetReadiness />} />
          <Route path="/parts" element={<CriticalParts />} />
          <Route path="/suppliers" element={<SupplierRisk />} />
          <Route path="/maintenance" element={<MaintenanceRisk />} />
          <Route path="/recommendations" element={<AIRecommendations />} />
          <Route path="/executive" element={<ExecutiveSummary />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
