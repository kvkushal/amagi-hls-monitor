import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

export const streamApi = {
    // Stream management
    getStreams: () => api.get('/streams'),
    getStream: (streamId: string) => api.get(`/streams/${streamId}`),
    createStream: (data: any) => api.post('/streams', data),
    deleteStream: (streamId: string) => api.delete(`/streams/${streamId}`),

    // Metrics
    getMetrics: (streamId: string, range: string) =>
        api.get(`/streams/${streamId}/metrics`, { params: { range } }),

    // Sprites
    getSprites: (streamId: string) => api.get(`/streams/${streamId}/sprites`),

    // Segments
    getSegments: (streamId: string, limit = 100, offset = 0) =>
        api.get(`/streams/${streamId}/segments`, { params: { limit, offset } }),

    // Loudness
    getLoudness: (streamId: string, range: string) =>
        api.get(`/streams/${streamId}/loudness`, { params: { range } }),

    // Events
    getEvents: (streamId: string, params?: any) =>
        api.get(`/streams/${streamId}/events`, { params }),

    // Health
    getHealth: () => api.get('/health'),
    getStreamHealth: (streamId: string) => api.get(`/streams/${streamId}/health`),

    // Alerts
    getAlerts: (streamId: string, includeResolved = false) =>
        api.get(`/streams/${streamId}/alerts`, { params: { include_resolved: includeResolved } }),
    acknowledgeAlert: (streamId: string, alertId: string) =>
        api.post(`/streams/${streamId}/alerts/${alertId}/acknowledge`),

    // Stream Logs
    getStreamLogs: (streamId: string, limit = 500) =>
        api.get(`/streams/${streamId}/logs`, { params: { limit } }),

    // Thumbnails
    getThumbnail: (streamId: string) => api.get(`/streams/${streamId}/thumbnail`),
    getThumbnailUrl: (streamId: string) => `/api/streams/${streamId}/thumbnail/file`,

    // Video Metrics
    getVideoMetrics: (streamId: string, range: string) =>
        api.get(`/streams/${streamId}/video-metrics`, { params: { range } }),

    // Audio Metrics  
    getAudioMetrics: (streamId: string, range: string) =>
        api.get(`/streams/${streamId}/audio-metrics`, { params: { range } }),

    // SCTE-35 Events
    getScte35Events: (streamId: string) =>
        api.get(`/streams/${streamId}/scte35-events`),

    // Export URLs (direct download links)
    getExportMetricsUrl: (streamId: string) => `/api/export/${streamId}/metrics.csv`,
    getExportAlertsUrl: (streamId: string) => `/api/export/${streamId}/alerts.csv`,
    getExportScte35Url: (streamId: string) => `/api/export/${streamId}/scte35.csv`,
    getExportLoudnessUrl: (streamId: string) => `/api/export/${streamId}/loudness.csv`,

    // Webhooks
    getWebhooks: () => api.get('/webhooks'),
    createWebhook: (data: any) => api.post('/webhooks', data),
    updateWebhook: (webhookId: string, data: any) => api.put(`/webhooks/${webhookId}`, data),
    deleteWebhook: (webhookId: string) => api.delete(`/webhooks/${webhookId}`),
    testWebhook: (webhookId: string) => api.post(`/webhooks/${webhookId}/test`),
}

export default api
