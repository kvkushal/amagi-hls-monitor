import { create } from 'zustand'

export interface HealthScore {
    score: number
    color: 'green' | 'yellow' | 'red'
    factors: Record<string, number>
}

export interface AlertData {
    alert_id: string
    stream_id: string
    alert_type: string
    severity: string
    message: string
    timestamp: string
    metadata: Record<string, any>
    acknowledged: boolean
    resolved: boolean
    resolved_at: string | null
}

export interface StreamData {
    id: string
    name: string
    status: string
    manifest_url: string
    tags: string[]
    version: string
    start_time: string
    thumbnail_url?: string
    health?: {
        status: string
        uptime_percentage: number
        error_rate_last_hour: number
        active_alarms: any[]
        active_alerts: AlertData[]
        health_score?: HealthScore
        tr101290_metrics: {
            sync_byte_errors: number
            continuity_errors: number
            transport_errors: number
            pid_errors: number
            pcr_errors: number
            last_updated: string
        }
        manifest_errors: any[]
        audio_metrics?: {
            bitrate_kbps?: number
            sample_rate?: number
            channels?: number
            codec?: string
            packet_loss_percent: number
            jitter_ms: number
            loudness_lufs?: number
        }
        video_metrics?: {
            bitrate_kbps?: number
            resolution?: string
            frame_rate?: number
            codec?: string
            scte35_detected: boolean
            scte35_count: number
        }
        last_updated: string
    }
    current_metrics?: SegmentMetrics
}

export interface SegmentMetrics {
    uri: string
    filename: string
    resolution?: string
    bandwidth?: number
    actual_bitrate: number
    download_speed: number
    segment_duration: number
    ttfb: number
    download_time: number
    segment_size_bytes: number
    segment_size_mb: number
    timestamp: string
    sequence_number?: number
}

export interface LoudnessData {
    timestamp: string
    momentary_lufs?: number
    shortterm_lufs?: number
    integrated_lufs?: number
    rms_db?: number
    is_approximation: boolean
}

export interface AdMarker {
    timestamp: string
    type: 'ad_insertion' | 'splice_null' | 'bandwidth_reservation'
    duration?: number
    metadata: Record<string, any>
}

export interface SpriteMap {
    sprite_id: string
    sprite_url: string
    grid_width: number
    grid_height: number
    thumbnail_width: number
    thumbnail_height: number
    thumbnails: Array<{
        timestamp: string
        x: number
        y: number
        w: number
        h: number
        index: number
    }>
}

export interface StreamEvent {
    event_id?: string
    stream_id: string
    event_type: string
    timestamp: string
    message: string
    metadata?: Record<string, any>
    severity?: string
}

export type TimeRange = '3min' | '30min' | '3h' | '8h' | '2d' | '4d'
export type ThumbnailDensity = 25 | 50 | 75 | 100

interface StreamStore {
    // Streams
    streams: StreamData[]
    selectedStreamId: string | null

    // Metrics
    metrics: SegmentMetrics[]
    loudnessData: LoudnessData[]
    adMarkers: AdMarker[]

    // Sprites
    sprites: SpriteMap[]
    currentSprite: SpriteMap | null

    // Events 
    events: StreamEvent[]

    // UI State
    timeRange: TimeRange
    thumbnailDensity: ThumbnailDensity
    isPlaying: boolean
    currentTime: string
    tabSyncEnabled: boolean

    // WebSocket
    wsConnected: boolean

    // Thumbnails
    thumbnails: Record<number, string>
    addThumbnail: (sequence: number, path: string) => void

    // Actions
    setStreams: (streams: StreamData[]) => void
    selectStream: (streamId: string | null) => void
    setMetrics: (metrics: SegmentMetrics[]) => void
    addMetric: (metric: SegmentMetrics) => void
    setLoudnessData: (data: LoudnessData[]) => void
    addLoudnessData: (data: LoudnessData) => void
    setAdMarkers: (markers: AdMarker[]) => void
    addAdMarker: (marker: AdMarker) => void
    setSprites: (sprites: SpriteMap[]) => void
    addSprite: (sprite: SpriteMap) => void
    setCurrentSprite: (sprite: SpriteMap | null) => void
    setEvents: (events: StreamEvent[]) => void
    addEvent: (event: StreamEvent) => void
    setTimeRange: (range: TimeRange) => void
    setThumbnailDensity: (density: ThumbnailDensity) => void
    setIsPlaying: (playing: boolean) => void
    setCurrentTime: (time: string) => void
    setTabSyncEnabled: (enabled: boolean) => void
    setWsConnected: (connected: boolean) => void
}

export const useStreamStore = create<StreamStore>((set) => ({
    // Initial state
    streams: [],
    selectedStreamId: null,
    metrics: [],
    loudnessData: [],
    adMarkers: [],
    sprites: [],
    currentSprite: null,
    events: [],
    timeRange: '3min',
    thumbnailDensity: 25,
    isPlaying: false,
    currentTime: '00:00',
    tabSyncEnabled: false,
    wsConnected: false,

    // Thumbnails
    thumbnails: {},
    addThumbnail: (sequence, path) => set((state) => ({
        thumbnails: { ...state.thumbnails, [sequence]: path }
    })),

    // Actions
    setStreams: (streams) => set({ streams }),
    selectStream: (streamId) => set({ selectedStreamId: streamId }),

    setMetrics: (metrics) => set({ metrics }),
    addMetric: (metric) => set((state) => ({
        metrics: [...state.metrics, metric]
    })),

    setLoudnessData: (data) => set({ loudnessData: data }),
    addLoudnessData: (data) => set((state) => ({
        loudnessData: [...state.loudnessData, data]
    })),

    setAdMarkers: (markers) => set({ adMarkers: markers }),
    addAdMarker: (marker) => set((state) => ({
        adMarkers: [...state.adMarkers, marker]
    })),

    setSprites: (sprites) => set({ sprites }),
    addSprite: (sprite) => set((state) => ({
        sprites: [...state.sprites, sprite]
    })),
    setCurrentSprite: (sprite) => set({ currentSprite: sprite }),

    setEvents: (events) => set({ events }),
    addEvent: (event) => set((state) => ({
        events: [...state.events, event]
    })),

    setTimeRange: (range) => set({ timeRange: range }),
    setThumbnailDensity: (density) => set({ thumbnailDensity: density }),
    setIsPlaying: (playing) => set({ isPlaying: playing }),
    setCurrentTime: (time) => set({ currentTime: time }),
    setTabSyncEnabled: (enabled) => set({ tabSyncEnabled: enabled }),
    setWsConnected: (connected) => set({ wsConnected: connected }),
}))
