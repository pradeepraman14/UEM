import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import AppShell from '@/components/Layout/AppShell'
import LoginPage from '@/pages/Login/LoginPage'
import DashboardPage from '@/pages/Dashboard/DashboardPage'
import DeviceListPage from '@/pages/Devices/DeviceListPage'
import DeviceDetailPage from '@/pages/Devices/DeviceDetailPage'
import InventoryPage from '@/pages/Inventory/InventoryPage'
import SoftwarePage from '@/pages/Software/SoftwarePage'
import PatchesPage from '@/pages/Patches/PatchesPage'
import PoliciesPage from '@/pages/Policies/PoliciesPage'
import CompliancePage from '@/pages/Compliance/CompliancePage'
import BitLockerPage from '@/pages/BitLocker/BitLockerPage'
import RemoteToolsPage from '@/pages/RemoteTools/RemoteToolsPage'
import AlertsPage from '@/pages/Alerts/AlertsPage'
import ReportsPage from '@/pages/Reports/ReportsPage'
import UsersPage from '@/pages/Users/UsersPage'
import GroupsPage from '@/pages/Groups/GroupsPage'
import SettingsPage from '@/pages/Settings/SettingsPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="devices" element={<DeviceListPage />} />
          <Route path="devices/:id" element={<DeviceDetailPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="software" element={<SoftwarePage />} />
          <Route path="patches" element={<PatchesPage />} />
          <Route path="policies" element={<PoliciesPage />} />
          <Route path="compliance" element={<CompliancePage />} />
          <Route path="bitlocker" element={<BitLockerPage />} />
          <Route path="remote-tools" element={<RemoteToolsPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
