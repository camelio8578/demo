import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LeadList from './pages/LeadList'
import LeadDetailPage from './pages/LeadDetail'
import CaseList from './pages/CaseList'
import CaseDetailPage from './pages/CaseDetail'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/leads" replace />} />
        <Route path="/leads" element={<LeadList />} />
        <Route path="/leads/:id" element={<LeadDetailPage />} />
        <Route path="/cases" element={<CaseList />} />
        <Route path="/cases/:id" element={<CaseDetailPage />} />
      </Route>
    </Routes>
  )
}
