import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AuthProvider, useAuth } from './auth/AuthContext'
import FleetReadiness from './pages/FleetReadiness'
import CriticalParts from './pages/CriticalParts'
import SupplierRisk from './pages/SupplierRisk'
import OperationalImpact from './pages/OperationalImpact'
import MaintenanceRisk from './pages/MaintenanceRisk'
import AIRecommendations from './pages/AIRecommendations'
import ExecutiveSummary from './pages/ExecutiveSummary'
import SharedScenario from './pages/SharedScenario'
import BomAnalysis from './pages/BomAnalysis'
import Login from './pages/Login'

function AuthGate({ children }) {
  const { session, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-slate-400 text-sm">
        Loading session…
      </div>
    )
  }
  // require_auth is server-driven. In demo mode the server returns an
  // anonymous session and we let the user straight in.
  if (session?.require_auth && session?.anonymous) {
    return <Login />
  }
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public share route — no auth, no sidebar. Looks like a published report. */}
          <Route path="/share/:token" element={<SharedScenario />} />
          {/* App routes inside the dashboard layout. */}
          <Route path="*" element={
            <AuthGate>
              <Layout>
                <Routes>
                  <Route path="/" element={<FleetReadiness />} />
                  <Route path="/parts" element={<CriticalParts />} />
                  <Route path="/suppliers" element={<SupplierRisk />} />
                  <Route path="/impact" element={<OperationalImpact />} />
                  <Route path="/bom" element={<BomAnalysis />} />
                  <Route path="/maintenance" element={<MaintenanceRisk />} />
                  <Route path="/recommendations" element={<AIRecommendations />} />
                  <Route path="/executive" element={<ExecutiveSummary />} />
                </Routes>
              </Layout>
            </AuthGate>
          } />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
