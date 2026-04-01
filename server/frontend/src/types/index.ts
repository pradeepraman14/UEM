export interface Device {
  id: string
  device_name: string
  hostname: string
  fqdn?: string
  serial_number?: string
  device_uuid: string
  status: 'pending' | 'active' | 'inactive' | 'quarantined' | 'retired'
  is_online: boolean
  last_seen?: string
  ip_address?: string
  os_version?: string
  os_build?: string
  os_edition?: string
  agent_version?: string
  platform: string
  compliance_status: 'compliant' | 'non_compliant' | 'unknown'
  compliance_score?: number
  assigned_user?: string
  department?: string
  location?: string
  tags?: string[]
  enrolled_at?: string
  created_at: string
}

export interface DeviceListResponse {
  items: Device[]
  total: number
  page: number
  page_size: number
}

export interface User {
  id: string
  email: string
  full_name: string
  role: 'superadmin' | 'admin' | 'helpdesk' | 'readonly'
  is_active: boolean
  last_login?: string
  mfa_enabled: boolean
  created_at: string
}

export interface Policy {
  id: string
  name: string
  description?: string
  policy_type: string
  config: Record<string, unknown>
  priority: number
  is_active: boolean
  version: number
  created_at: string
}

export interface Alert {
  id: string
  device_id?: string
  alert_type: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  message: string
  status: 'open' | 'acknowledged' | 'resolved' | 'suppressed'
  created_at: string
  acknowledged_at?: string
}

export interface Patch {
  id: string
  kb_article_id?: string
  title: string
  patch_type: string
  severity?: 'critical' | 'important' | 'moderate' | 'low'
  release_date?: string
  reboot_required: boolean
  size_bytes?: number
}

export interface Command {
  id: string
  device_id: string
  command_type: string
  payload: Record<string, unknown>
  status: 'pending' | 'sent' | 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled'
  output?: string
  exit_code?: number
  error_message?: string
  sent_at?: string
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface SoftwarePackage {
  id: string
  name: string
  publisher?: string
  version: string
  category?: string
  install_type: string
  file_size_bytes?: number
  reboot_required: boolean
  icon_url?: string
}

export interface ComplianceRule {
  id: string
  name: string
  description?: string
  category: string
  check_type: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  is_active: boolean
  remediation_hint?: string
  auto_remediate: boolean
}

export interface BitLockerDevice {
  device_id: string
  hostname: string
  device_name: string
  device_status: string
  is_enabled: boolean
  os_volume_protected?: boolean
  encryption_method?: string
  encryption_percentage?: number
  recovery_key_escrowed: boolean
  collected_at: string
}

export interface DashboardStats {
  total_devices: number
  online_devices: number
  compliant_devices: number
  non_compliant_devices: number
  open_alerts: number
  critical_alerts: number
  missing_patches: number
  agents_online: number
}

export interface WSMessage {
  type: string
  device_id?: string
  correlation_id?: string
  payload: Record<string, unknown>
}
