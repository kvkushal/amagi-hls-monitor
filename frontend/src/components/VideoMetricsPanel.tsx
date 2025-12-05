import React, { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { streamApi } from '../services/api'
import { format } from 'date-fns'

interface VideoMetricsPanelProps {
    streamId: string
    timeRange: string
}

interface VideoDataPoint {
    timestamp: string
    bitrate_mbps: number
    download_speed_mbps: number
    ttfb_ms: number
    download_time_ms: number
    segment_duration_s: number
    segment_size_mb: number
    resolution: string
}

export const VideoMetricsPanel: React.FC<VideoMetricsPanelProps> = ({ streamId, timeRange }) => {
    const [data, setData] = useState<VideoDataPoint[]>([])
    const [loading, setLoading] = useState(true)
    const [showBitrate, setShowBitrate] = useState(true)
    const [showDownload, setShowDownload] = useState(true)
    const [showTTFB, setShowTTFB] = useState(false)

    useEffect(() => {
        loadData()
    }, [streamId, timeRange])

    const loadData = async () => {
        try {
            setLoading(true)
            const response = await streamApi.getVideoMetrics(streamId, timeRange)
            setData(response.data.history || [])
        } catch (error) {
            console.error('Error loading video metrics:', error)
        } finally {
            setLoading(false)
        }
    }

    const formatTime = (timestamp: string) => {
        try {
            return format(new Date(timestamp), 'HH:mm:ss')
        } catch {
            return timestamp
        }
    }

    // Calculate stats
    const avgBitrate = data.length > 0
        ? (data.reduce((sum, d) => sum + (d.bitrate_mbps || 0), 0) / data.length).toFixed(2)
        : '0'
    const avgTTFB = data.length > 0
        ? Math.round(data.reduce((sum, d) => sum + (d.ttfb_ms || 0), 0) / data.length)
        : 0
    const avgDownload = data.length > 0
        ? (data.reduce((sum, d) => sum + (d.download_speed_mbps || 0), 0) / data.length).toFixed(2)
        : '0'

    if (loading) {
        return (
            <div className="bg-elecard-card rounded-lg p-4 animate-pulse">
                <div className="h-64 bg-elecard-darker rounded"></div>
            </div>
        )
    }

    return (
        <div className="bg-elecard-card rounded-lg border border-elecard-border">
            {/* Header */}
            <div className="px-4 py-3 border-b border-elecard-border flex items-center justify-between">
                <h3 className="text-white font-semibold flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Video Metrics
                </h3>

                {/* Toggle buttons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowBitrate(!showBitrate)}
                        className={`px-2 py-1 text-xs rounded ${showBitrate ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        Bitrate
                    </button>
                    <button
                        onClick={() => setShowDownload(!showDownload)}
                        className={`px-2 py-1 text-xs rounded ${showDownload ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        Download
                    </button>
                    <button
                        onClick={() => setShowTTFB(!showTTFB)}
                        className={`px-2 py-1 text-xs rounded ${showTTFB ? 'bg-orange-500/20 text-orange-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        TTFB
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-3 gap-4 p-4 border-b border-elecard-border">
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Avg Bitrate</div>
                    <div className="text-xl font-bold text-blue-400">{avgBitrate} Mbps</div>
                </div>
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Avg Download</div>
                    <div className="text-xl font-bold text-green-400">{avgDownload} Mbps</div>
                </div>
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Avg TTFB</div>
                    <div className="text-xl font-bold text-orange-400">{avgTTFB} ms</div>
                </div>
            </div>

            {/* Chart */}
            <div className="p-4">
                {data.length === 0 ? (
                    <div className="h-48 flex items-center justify-center text-gray-500">
                        No video metrics data available
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis
                                dataKey="timestamp"
                                tickFormatter={formatTime}
                                stroke="#6B7280"
                                fontSize={10}
                            />
                            <YAxis
                                stroke="#6B7280"
                                fontSize={10}
                                yAxisId="left"
                            />
                            <YAxis
                                stroke="#6B7280"
                                fontSize={10}
                                yAxisId="right"
                                orientation="right"
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1F2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px'
                                }}
                                labelFormatter={(label) => formatTime(label as string)}
                            />
                            <Legend />
                            {showBitrate && (
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="bitrate_mbps"
                                    name="Bitrate (Mbps)"
                                    stroke="#3B82F6"
                                    strokeWidth={2}
                                    dot={false}
                                />
                            )}
                            {showDownload && (
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="download_speed_mbps"
                                    name="Download (Mbps)"
                                    stroke="#10B981"
                                    strokeWidth={2}
                                    dot={false}
                                />
                            )}
                            {showTTFB && (
                                <Line
                                    yAxisId="right"
                                    type="monotone"
                                    dataKey="ttfb_ms"
                                    name="TTFB (ms)"
                                    stroke="#F97316"
                                    strokeWidth={2}
                                    dot={false}
                                />
                            )}
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    )
}
