import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useStreamStore } from '../store/useStreamStore'
import { format } from 'date-fns'

export const LoudnessChart: React.FC = () => {
    const { loudnessData, adMarkers } = useStreamStore()
    const [showMomentary, setShowMomentary] = React.useState(true)
    const [showShortTerm, setShowShortTerm] = React.useState(true)

    // Format data for Recharts
    const chartData = loudnessData.map((d) => ({
        timestamp: new Date(d.timestamp).getTime(),
        momentary: d.momentary_lufs,
        shortterm: d.shortterm_lufs,
        formattedTime: format(new Date(d.timestamp), 'HH:mm:ss')
    }))

    return (
        <div className="bg-elecard-card p-4 rounded-lg border border-elecard-border">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-200">Loudness (LUFS)</h3>

                <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showMomentary}
                            onChange={(e) => setShowMomentary(e.target.checked)}
                            className="form-checkbox text-purple-600"
                        />
                        <span className="text-sm text-gray-300">Momentary Loudness</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showShortTerm}
                            onChange={(e) => setShowShortTerm(e.target.checked)}
                            className="form-checkbox text-blue-600"
                        />
                        <span className="text-sm text-gray-300">Short-Term Loudness</span>
                    </label>
                </div>
            </div>

            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#3a4a5a" />
                        <XAxis
                            dataKey="formattedTime"
                            stroke="#9ca3af"
                            style={{ fontSize: '12px' }}
                        />
                        <YAxis
                            stroke="#9ca3af"
                            style={{ fontSize: '12px' }}
                            domain={[-50, 10]}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#2c3e50',
                                border: '1px solid #3a4a5a',
                                borderRadius: '4px',
                                color: '#e2e8f0'
                            }}
                        />
                        <Legend />

                        {showMomentary && (
                            <Line
                                type="monotone"
                                dataKey="momentary"
                                stroke="#a855f7"
                                name="Momentary LUFS"
                                dot={false}
                                strokeWidth={2}
                            />
                        )}

                        {showShortTerm && (
                            <Line
                                type="monotone"
                                dataKey="shortterm"
                                stroke="#3b82f6"
                                name="Short-term LUFS"
                                dot={false}
                                strokeWidth={2}
                            />
                        )}
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Ad Insertion Markers */}
            {adMarkers.length > 0 && (
                <div className="mt-4 pt-4 border-t border-elecard-border">
                    <h4 className="text-sm font-medium text-gray-300 mb-2">Ads insertion</h4>
                    <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1">
                            <div className="w-3 h-3 bg-green-500 rounded-sm" />
                            <span className="text-gray-400">Ad Insertion</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <div className="w-3 h-3 bg-blue-500 rounded-sm" />
                            <span className="text-gray-400">Splice Null</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <div className="w-3 h-3 bg-purple-500 rounded-sm" />
                            <span className="text-gray-400">Bandwidth Reservation</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
