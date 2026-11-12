import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppNav } from './components/AppNav'
import { Header } from './components/Header'
import { useShipCrewData } from './hooks/useShipCrewData'
import { InsightsPage } from './pages/InsightsPage'
import { MissionPage } from './pages/MissionPage'
import { SetupPage } from './pages/SetupPage'
import './App.css'

export default function App() {
  const data = useShipCrewData()

  return (
    <BrowserRouter>
      <div className="page">
        <Header
          demoMode={data.health?.demo_mode}
          activeProvider={data.health?.active_provider}
          activeAuth={data.health?.active_auth}
          model={data.health?.model}
        />
        <AppNav />
        {data.error ? <p className="error banner">{data.error}</p> : null}
        {data.notice ? <p className="notice banner">{data.notice}</p> : null}

        <Routes>
          <Route path="/" element={<MissionPage data={data} />} />
          <Route path="/missions/:missionId" element={<MissionPage data={data} />} />
          <Route path="/setup" element={<SetupPage data={data} />} />
          <Route path="/insights" element={<InsightsPage data={data} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
