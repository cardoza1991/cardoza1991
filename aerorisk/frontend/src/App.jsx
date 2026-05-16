import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import FleetReadiness from './pages/FleetReadiness'
import CriticalParts from './pages/CriticalParts'
import SupplierRisk from './pages/SupplierRisk'
import OperationalImpact from './pages/OperationalImpact'
import MaintenanceRisk from './pages/MaintenanceRisk'
import AIRecommendations from './pages/AIRecommendations'
import ExecutiveSummary from './pages/ExecutiveSummary'
import SharedScenario from './pages/SharedScenario'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public share route — no auth, no sidebar. Looks like a published report. */}
        <Route path="/share/:token" element={<SharedScenario />} />
        {/* App routes inside the dashboard layout. */}
        <Route path="*" element={
          <Layout>
            <Routes>
              <Route path="/" element={<FleetReadiness />} />
              <Route path="/parts" element={<CriticalParts />} />
              <Route path="/suppliers" element={<SupplierRisk />} />
              <Route path="/impact" element={<OperationalImpact />} />
              <Route path="/maintenance" element={<MaintenanceRisk />} />
              <Route path="/recommendations" element={<AIRecommendations />} />
              <Route path="/executive" element={<ExecutiveSummary />} />
            </Routes>
          </Layout>
        } />
      </Routes>
    </BrowserRouter>
  )
}
