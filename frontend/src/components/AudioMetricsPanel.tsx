import React, { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { streamApi } from '../services/api'
import { format } from 'date-fns'

interface AudioMetricsPanelProps {
    streamId: string
    timeRange: string
}

interface AudioDataPoint {
    timestamp: string
    momentary_lufs: number | null
    shortterm_lufs: number | null
    integrated_lufs: number | null
    rms_db: number | null
    is_approximation: boolean
}

export const AudioMetricsPanel: React.FC<AudioMetricsPanelProps> = ({ streamId, timeRange }) => {
    const [data, setData] = useState<AudioDataPoint[]>([])
    const [loading, setLoading] = useState(true)
    const [showMomentary, setShowMomentary] = useState(true)
    const [showShortterm, setShowShortterm] = useState(true)
    const [showRMS, setShowRMS] = useState(true)  // Enable RMS by default

    useEffect(() => {
        loadData()
        // Auto-refresh every 5 seconds
        const interval = setInterval(loadData, 5000)
        return () => clearInterval(interval)
    }, [streamId, timeRange])

    const loadData = async () => {
        try {
            const response = await streamApi.getAudioMetrics(streamId, timeRange)
            setData(response.data.history || [])
        } catch (error) {
            console.error('Error loading audio metrics:', error)
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

    // Calculate stats - handle null values properly
    const calcAvg = (values: (number | null)[]) => {
        const validValues = values.filter(v => v !== null && v !== undefined) as number[]
        if (validValues.length === 0) return null
        return validValues.reduce((sum, v) => sum + v, 0) / validValues.length
    }

    const avgMomentary = calcAvg(data.map(d => d.momentary_lufs))
    const avgShortterm = calcAvg(data.map(d => d.shortterm_lufs))
    const avgRMS = calcAvg(data.map(d => d.rms_db))

    const formatAvg = (val: number | null) => val !== null ? val.toFixed(1) : '-'

    // Check loudness health - use RMS if LUFS not available
    const getLoudnessStatus = () => {
        if (data.length === 0) return { status: 'unknown', color: 'gray' }

        const recent = data.slice(-10)

        // Try momentary LUFS first
        const validLufs = recent.filter(d => d.momentary_lufs !== null)
        if (validLufs.length > 0) {
            const avgRecent = validLufs.reduce((sum, d) => sum + (d.momentary_lufs || 0), 0) / validLufs.length
            if (avgRecent > -14) return { status: 'Too Loud', color: 'red' }
            if (avgRecent < -27) return { status: 'Too Quiet', color: 'yellow' }
            return { status: 'Normal', color: 'green' }
        }

        // Fallback to RMS (approximate: RMS dB is roughly LUFS + ~10-14dB)
        const validRms = recent.filter(d => d.rms_db !== null)
        if (validRms.length > 0) {
            const avgRms = validRms.reduce((sum, d) => sum + (d.rms_db || 0), 0) / validRms.length
            // RMS thresholds adjusted for approximate LUFS equivalence
            if (avgRms > -4) return { status: 'Too Loud', color: 'red' }
            if (avgRms < -17) return { status: 'Too Quiet', color: 'yellow' }
            return { status: 'Normal (RMS)', color: 'green' }
        }

        return { status: 'No Data', color: 'gray' }
    }

    const loudnessStatus = getLoudnessStatus()

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
                    <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                    Audio Metrics
                    <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${loudnessStatus.color === 'green' ? 'bg-green-500/20 text-green-400' :
                        loudnessStatus.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                            loudnessStatus.color === 'red' ? 'bg-red-500/20 text-red-400' :
                                'bg-gray-500/20 text-gray-400'
                        }`}>
                        {loudnessStatus.status}
                    </span>
                </h3>

                {/* Toggle buttons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowMomentary(!showMomentary)}
                        className={`px-2 py-1 text-xs rounded ${showMomentary ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        Momentary
                    </button>
                    <button
                        onClick={() => setShowShortterm(!showShortterm)}
                        className={`px-2 py-1 text-xs rounded ${showShortterm ? 'bg-pink-500/20 text-pink-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        Short-term
                    </button>
                    <button
                        onClick={() => setShowRMS(!showRMS)}
                        className={`px-2 py-1 text-xs rounded ${showRMS ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-700 text-gray-400'}`}
                    >
                        RMS
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-4 gap-4 p-4 border-b border-elecard-border">
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Momentary LUFS</div>
                    <div className="text-xl font-bold text-purple-400">{formatAvg(avgMomentary)}</div>
                </div>
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Short-term LUFS</div>
                    <div className="text-xl font-bold text-pink-400">{formatAvg(avgShortterm)}</div>
                </div>
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">RMS dB</div>
                    <div className="text-xl font-bold text-cyan-400">{formatAvg(avgRMS)}</div>
                </div>
                <div className="bg-elecard-darker rounded-lg p-3 text-center">
                    <div className="text-gray-400 text-xs">Target</div>
                    <div className="text-xl font-bold text-gray-300">-23 LUFS</div>
                </div>
            </div>

            {/* Chart */}
            <div className="p-4">
                {data.length === 0 ? (
                    <div className="h-48 flex items-center justify-center text-gray-500">
                        No audio metrics data available
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
                                domain={[-60, 0]}
                                tickFormatter={(value) => `${value}`}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1F2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px'
                                }}
                                labelFormatter={(label) => formatTime(label as string)}
                                formatter={(value: number) => [`${value?.toFixed(1)} LUFS`, '']}
                            />
                            <Legend />

                            {/* Target line */}
                            <Line
                                type="monotone"
                                dataKey={() => -23}
                                name="Target (-23 LUFS)"
                                stroke="#6B7280"
                                strokeWidth={1}
                                strokeDasharray="5 5"
                                dot={false}
                            />

                            {showMomentary && (
                                <Line
                                    type="monotone"
                                    dataKey="momentary_lufs"
                                    name="Momentary"
                                    stroke="#A855F7"
                                    strokeWidth={2}
                                    dot={false}
                                    connectNulls
                                />
                            )}
                            {showShortterm && (
                                <Line
                                    type="monotone"
                                    dataKey="shortterm_lufs"
                                    name="Short-term"
                                    stroke="#EC4899"
                                    strokeWidth={2}
                                    dot={false}
                                    connectNulls
                                />
                            )}
                            {showRMS && (
                                <Line
                                    type="monotone"
                                    dataKey="rms_db"
                                    name="RMS"
                                    stroke="#06B6D4"
                                    strokeWidth={2}
                                    dot={false}
                                    connectNulls
                                />
                            )}
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Info banner for approximated data */}
            {data.some(d => d.is_approximation) && (
                <div className="px-4 pb-4">
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-3 py-2 text-xs text-yellow-400 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Some loudness values are approximated from RMS (ebur128 not available)
                    </div>
                </div>
            )}
        </div>
    )
}
