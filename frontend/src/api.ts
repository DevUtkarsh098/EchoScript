import axios from 'axios'
import { bearerToken } from './auth'
import type { Capabilities, Job } from './types'

export const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const client = axios.create({ baseURL: apiBase, timeout: 20000 })
client.interceptors.request.use(config => {
  const token = bearerToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const api = {
  jobs: async () => (await client.get<Job[]>('/api/jobs')).data,
  job: async (id: string) => (await client.get<Job>(`/api/jobs/${id}`)).data,
  capabilities: async () => (await client.get<Capabilities>('/api/capabilities')).data,
  start: async (id: string) => (await client.post<Job>(`/api/jobs/${id}/start`)).data,
  completeUpload: async (id: string) => (await client.post<Job>(`/api/jobs/${id}/upload-complete`)).data,
  video: async (id: string) => (await client.post<Job>(`/api/jobs/${id}/video`)).data,
  create: async (file: File, language: string) => (await client.post('/api/jobs', { filename: file.name, content_type: file.type || mimeFromName(file.name), size_bytes: file.size, language, generate_video: false })).data as { job: Job; upload_url: string; upload_method: string; upload_headers: Record<string, string> },
}
function mimeFromName(name: string) { const extension = name.split('.').pop()?.toLowerCase(); return extension === 'wav' ? 'audio/wav' : extension === 'm4a' ? 'audio/mp4' : 'audio/mpeg' }
export function absoluteAsset(path?: string) { return path ? `${apiBase}${path}` : undefined }
export async function getAsset(path: string) { return (await client.get<Blob>(path, { responseType: 'blob' })).data }
export async function downloadAsset(path: string, filename: string) {
  const objectUrl = URL.createObjectURL(await getAsset(path))
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}
export function uploadFile(url: string, file: File, headers: Record<string, string>, onProgress: (value: number) => void, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('PUT', url)
    Object.entries(headers).forEach(([key, value]) => request.setRequestHeader(key, value))
    const token = bearerToken()
    const apiOrigin = new URL(apiBase || window.location.origin, window.location.origin).origin
    const uploadOrigin = new URL(url, window.location.origin).origin
    if (token && uploadOrigin === apiOrigin) request.setRequestHeader('Authorization', `Bearer ${token}`)
    request.upload.onprogress = event => event.lengthComputable && onProgress(Math.round((event.loaded / event.total) * 100))
    request.onload = () => request.status >= 200 && request.status < 300 ? resolve() : reject(new Error('Upload failed'))
    request.onerror = () => reject(new Error('Network error while uploading'))
    signal.addEventListener('abort', () => { request.abort(); reject(new DOMException('Upload cancelled', 'AbortError')) })
    request.send(file)
  })
}
