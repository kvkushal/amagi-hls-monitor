import React from 'react'
import { useStreamStore } from '../store/useStreamStore'
import { streamApi } from '../services/api'
import { TimelineControls } from './TimelineControls'
import { TimelineThumbnails } from './TimelineThumbnails'
import { KPIBadges } from './KPIBadges'
import { LoudnessChart } from './LoudnessChart'
import { MetricsTable } from './MetricsTable'
import { EventList } from './EventList'
import { useWebSocket } from '../hooks/useWebSocket'
import { HealthTab } from './HealthTab'
import { VideoMetricsPanel } from './VideoMetricsPanel'
import { AudioMetricsPanel } from './AudioMetricsPanel'
import { AlertsPanel } from './AlertsPanel'

export const StreamDetailsPanel: React.FC = () => {
    const { selectedStreamId, streams, wsConnected } = useStreamStore()
    const [activeTab, setActiveTab] = React.useState<'overview' | 'health'>('overview')
    const [showExportMenu, setShowExportMenu] = React.useState(false)

    // Connect to WebSocket for selected stream
    useWebSocket(selectedStreamId)

    const {
        timeRange,
        setLoudnessData,
        setMetrics,
        setEvents
    } = useStreamStore()

    // Fetch data when stream or time range changes
    React.useEffect(() => {
        if (!selectedStreamId) return

        const fetchData = async () => {
            try {
                // Fetch loudness
                const loudnessRes = await streamApi.getLoudness(selectedStreamId, timeRange)
                setLoudnessData(loudnessRes.data.loudness_data)

                // Fetch recent segments/metrics
                const segmentsRes = await streamApi.getSegments(selectedStreamId, 100)
                setMetrics(segmentsRes.data)

                // Fetch events
                const eventsRes = await streamApi.getEvents(selectedStreamId, { limit: 100 })
                setEvents(eventsRes.data.events)

            } catch (error) {
                console.error('Error fetching stream data:', error)
            }
        }

        fetchData()
    }, [selectedStreamId, timeRange, setLoudnessData, setMetrics, setEvents])

    // Find selected stream
    const selectedStream = streams.find(s => s.id === selectedStreamId)

    if (!selectedStream) {
        return (
            <div className="flex-1 flex items-center justify-center bg-elecard-bg">
                <div className="text-center">
                    <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <h2 className="text-xl font-semibold text-gray-400 mb-2">No Stream Selected</h2>
                    <p className="text-gray-500">Select a stream to view details</p>
                </div>
            </div>
        )
    }

    return (
        <div className="h-screen flex flex-col bg-elecard-bg overflow-hidden">
            {/* Header */}
            <div className="bg-elecard-darker border-b border-elecard-border px-4 py-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => useStreamStore.getState().selectStream(null)}
                            className="p-1 hover:bg-elecard-card rounded text-gray-400 hover:text-white transition-colors"
                            title="Back to Dashboard"
                        >
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                        </button>
                        <h1 className="text-xl font-bold text-gray-200">{selectedStream.name}</h1>
                        <div className={`badge ${wsConnected ? 'badge-green' : 'badge-gray'}`}>
                            {wsConnected ? 'Connected' : 'Disconnected'}
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <KPIBadges />

                        {/* Export Dropdown */}
                        <div className="relative">
                            <button
                                onClick={() => setShowExportMenu(!showExportMenu)}
                                className="px-3 py-1.5 bg-elecard-card hover:bg-elecard-border text-gray-300 rounded flex items-center gap-2 text-sm"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Export
                            </button>

                            {showExportMenu && (
                                <div className="absolute right-0 mt-1 bg-elecard-card border border-elecard-border rounded-lg shadow-xl z-50 min-w-[160px]">
                                    <a
                                        href={streamApi.getExportMetricsUrl(selectedStreamId!)}
                                        className="block px-4 py-2 text-sm text-gray-300 hover:bg-elecard-border"
                                        onClick={() => setShowExportMenu(false)}
                                    >
                                        📊 Metrics CSV
                                    </a>
                                    <a
                                        href={streamApi.getExportAlertsUrl(selectedStreamId!)}
                                        className="block px-4 py-2 text-sm text-gray-300 hover:bg-elecard-border"
                                        onClick={() => setShowExportMenu(false)}
                                    >
                                        ⚠️ Alerts CSV
                                    </a>
                                    <a
                                        href={streamApi.getExportLoudnessUrl(selectedStreamId!)}
                                        className="block px-4 py-2 text-sm text-gray-300 hover:bg-elecard-border"
                                        onClick={() => setShowExportMenu(false)}
                                    >
                                        🔊 Loudness CSV
                                    </a>
                                    <a
                                        href={streamApi.getExportScte35Url(selectedStreamId!)}
                                        className="block px-4 py-2 text-sm text-gray-300 hover:bg-elecard-border"
                                        onClick={() => setShowExportMenu(false)}
                                    >
                                        📺 SCTE-35 CSV
                                    </a>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="bg-elecard-card border-b border-elecard-border px-4">
                <div className="flex gap-6">
                    <button
                        className={`py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'overview'
                            ? 'border-blue-500 text-blue-400'
                            : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        onClick={() => setActiveTab('overview')}
                    >
                        Overview
                    </button>
                    <button
                        className={`py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'health'
                            ? 'border-blue-500 text-blue-400'
                            : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        onClick={() => setActiveTab('health')}
                    >
                        Health & Analysis
                    </button>
                </div>
            </div>

            {/* Timeline Controls (only for overview) */}
            {activeTab === 'overview' && <TimelineControls />}

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto">
                {activeTab === 'overview' ? (
                    <div className="max-w-[1920px] mx-auto">
                        {/* Probe Info Section */}
                        <div className="bg-elecard-card m-4 p-4 rounded-lg border border-elecard-border">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div>
                                    <div className="text-xs text-gray-500 uppercase mb-1">Probe</div>
                                    <div className="text-sm text-gray-300">{selectedStream.name}</div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 uppercase mb-1">Version</div>
                                    <div className="text-sm text-gray-300">{selectedStream.version || '2.1.9'}</div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 uppercase mb-1">Start</div>
                                    <div className="text-sm text-gray-300">
                                        {new Date(selectedStream.start_time).toLocaleString()}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 uppercase mb-1">Status</div>
                                    <div className={`text-sm font-semibold ${selectedStream.status?.toLowerCase() === 'online' ? 'text-green-400' :
                                        selectedStream.status?.toLowerCase() === 'error' ? 'text-red-400' :
                                            selectedStream.status?.toLowerCase() === 'starting' ? 'text-yellow-400' :
                                                'text-gray-400'
                                        }`}>{selectedStream.status}</div>
                                </div>
                                <div className="col-span-2">
                                    <div className="text-xs text-gray-500 uppercase mb-1">Media service URL</div>
                                    <div className="text-sm text-blue-400 truncate" title={selectedStream.manifest_url}>
                                        {selectedStream.manifest_url}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 uppercase mb-1">Tags</div>
                                    <div className="flex gap-1">
                                        {selectedStream.tags?.length > 0 ? (
                                            selectedStream.tags.map((tag, idx) => (
                                                <span key={idx} className="badge badge-gray text-xs">
                                                    {tag}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-sm text-gray-500">-</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Video & Audio Metrics Grid */}
                        <div className="m-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <VideoMetricsPanel streamId={selectedStreamId!} timeRange={timeRange} />
                            <AudioMetricsPanel streamId={selectedStreamId!} timeRange={timeRange} />
                        </div>

                        {/* Alerts Panel */}
                        <div className="m-4">
                            <AlertsPanel streamId={selectedStreamId!} />
                        </div>

                        {/* Loudness Chart */}
                        <div className="m-4">
                            <LoudnessChart />
                        </div>

                        {/* Thumbnails */}
                        <div className="m-4">
                            <TimelineThumbnails />
                        </div>

                        {/* Metrics Table */}
                        <div className="m-4">
                            <MetricsTable />
                        </div>

                        {/* Event List */}
                        <div className="m-4">
                            <EventList />
                        </div>
                    </div>
                ) : (
                    <HealthTab />
                )}
            </div>
        </div >
    )
}
