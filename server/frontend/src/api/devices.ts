import { apiClient } from './client'
import type { Device, DeviceListResponse } from '@/types'

export interface ListDevicesParams {
  page?: number
  page_size?: number
  status?: string
  compliance_status?: string
  is_online?: boolean
  search?: string
}

export const devicesApi = {
  list: (params?: ListDevicesParams) =>
    apiClient.get<DeviceListResponse>('/devices', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Device>(`/devices/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Device>) =>
    apiClient.patch<Device>(`/devices/${id}`, data).then((r) => r.data),

  retire: (id: string) =>
    apiClient.post(`/devices/${id}/retire`).then((r) => r.data),

  wipe: (id: string) =>
    apiClient.post(`/devices/${id}/wipe`).then((r) => r.data),

  status: (id: string) =>
    apiClient.get(`/devices/${id}/status`).then((r) => r.data),

  generateToken: () =>
    apiClient.post('/devices/generate-token').then((r) => r.data),

  getHardware: (id: string) =>
    apiClient.get(`/devices/${id}/inventory/hardware`).then((r) => r.data),

  getSoftware: (id: string, search?: string) =>
    apiClient.get(`/devices/${id}/inventory/software`, { params: { search } }).then((r) => r.data),

  getNetwork: (id: string) =>
    apiClient.get(`/devices/${id}/inventory/network`).then((r) => r.data),

  getPatches: (id: string) =>
    apiClient.get(`/devices/${id}/patches`).then((r) => r.data),

  getCompliance: (id: string) =>
    apiClient.get(`/compliance/devices/${id}`).then((r) => r.data),

  getBitLocker: (id: string) =>
    apiClient.get(`/bitlocker/${id}`).then((r) => r.data),
}
