import React from 'react'
import { useStreamStore } from '../store/useStreamStore'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export const HealthTab: React.FC = () => {
    const { streams, selectedStreamId, metrics } = useStreamStore()
    const stream = streams.find(s => s.id === selectedStreamId)

    if (!stream || !stream.health) {
        return <div className="p-4 text-gray-400">No health data available</div>
    }

    const { health } = stream

    // Get health score
    const healthScore = health.health_score?.score ?? 100
    const healthColor = health.health_score?.color ?? 'green'

    // Calculate availability from metrics if available
    const calculateAvailabilityTrend = () => {
        const streamMetrics = metrics.filter(m => m.filename.startsWith(`${selectedStreamId}_`))
        if (streamMetrics.length < 5) {
            // Not enough data, generate placeholder
            const data = []
            const now = new Date()
            for (let i = 24; i >= 0; i--) {
                data.push({
                    time: new Date(now.getTime() - i * 3600 * 1000).getHours() + ':00',
                    value: health.uptime_percentage
                })
            }
            return data
        }

        // Group by hour and calculate success rate
        const hourlyData = new Map()
        streamMetrics.forEach(m => {
            const hour = new Date(m.timestamp).getHours()
            if (!hourlyData.has(hour)) {
                hourlyData.set(hour, { total: 0, success: 0 })
            }
            hourlyData.get(hour).total++
            if (m.download_speed > 0) {
                hourlyData.get(hour).success++
            }
        })

        const result: { time: string; value: number }[] = []
        hourlyData.forEach((data, hour) => {
            result.push({
                time: `${hour}:00`,
                value: (data.success / data.total) * 100
            })
        })

        return result.length > 0 ? result : [{ time: 'Now', value: health.uptime_percentage }]
    }

    const getHealthColorClass = () => {
        if (healthColor === 'green' || healthScore >= 80) return 'text-green-500'
        if (healthColor === 'yellow' || healthScore >= 50) return 'text-yellow-500'
        return 'text-red-500'
    }

    const getHealthBgClass = () => {
        if (healthColor === 'green' || healthScore >= 80) return 'from-green-500/20'
        if (healthColor === 'yellow' || healthScore >= 50) return 'from-yellow-500/20'
        return 'from-red-500/20'
    }

    // Get active alerts
    const activeAlerts = health.active_alerts || []

    return (
        <div className="p-4 space-y-6">
            {/* Health Score Hero */}
            <div className={`bg-gradient-to-br ${getHealthBgClass()} to-elecard-card rounded-lg border border-elecard-border p-6`}>
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-gray-400 text-sm mb-2">Overall Health Score</h2>
                        <div className="flex items-baseline gap-2">
                            <span className={`text-5xl font-bold ${getHealthColorClass()}`}>
                                {healthScore}
                            </span>
                            <span className="text-2xl text-gray-500">/ 100</span>
                        </div>
                        <div className="text-gray-500 text-sm mt-2">
                            Last updated: {new Date(health.last_updated).toLocaleTimeString()}
                        </div>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                        <div className={`px-4 py-2 rounded-full font-semibold ${healthColor === 'green' ? 'bg-green-500/20 text-green-400' :
                            healthColor === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-red-500/20 text-red-400'
                            }`}>
                            {healthColor === 'green' ? '✓ Healthy' : healthColor === 'yellow' ? '⚠ Degraded' : '✕ Critical'}
                        </div>
                        {activeAlerts.length > 0 && (
                            <div className="text-red-400 text-sm">
                                {activeAlerts.length} active {activeAlerts.length === 1 ? 'alert' : 'alerts'}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-elecard-card p-4 rounded border border-elecard-border">
                    <div className="text-gray-500 text-sm mb-1">Service Availability</div>
                    <div className="text-2xl font-bold text-green-500">
                        {health.uptime_percentage.toFixed(2)}%
                    </div>
                    <div className="text-xs text-gray-600 mt-2">Last 24 hours</div>
                </div>
                <div className="bg-elecard-card p-4 rounded border border-elecard-border">
                    <div className="text-gray-500 text-sm mb-1">Error Rate (1h)</div>
                    <div className={`text-2xl font-bold ${health.error_rate_last_hour > 0 ? 'text-red-500' : 'text-gray-300'}`}>
                        {health.error_rate_last_hour.toFixed(2)}%
                    </div>
                </div>
                <div className="bg-elecard-card p-4 rounded border border-elecard-border">
                    <div className="text-gray-500 text-sm mb-1">Active Alerts</div>
                    <div className={`text-2xl font-bold ${activeAlerts.length > 0 ? 'text-red-500' : 'text-gray-300'}`}>
                        {activeAlerts.length}
                    </div>
                </div>
                <div className="bg-elecard-card p-4 rounded border border-elecard-border">
                    <div className="text-gray-500 text-sm mb-1">Status</div>
                    <div className={`text-2xl font-bold uppercase ${health.status === 'online' ? 'text-green-500' : 'text-red-500'}`}>
                        {health.status}
                    </div>
                </div>
            </div>

            {/* Availability Trend */}
            <div className="bg-elecard-card rounded border border-elecard-border overflow-hidden p-4">
                <h3 className="font-semibold text-gray-200 mb-4">Availability Trend</h3>
                <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={calculateAvailabilityTrend()}>
                            <defs>
                                <linearGradient id="colorUptime" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <XAxis dataKey="time" stroke="#6B7280" fontSize={10} />
                            <YAxis domain={[90, 100]} stroke="#6B7280" fontSize={10} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                                itemStyle={{ color: '#10B981' }}
                                formatter={(value: number) => [`${value.toFixed(2)}%`, 'Availability']}
                            />
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke="#10B981"
                                fillOpacity={1}
                                fill="url(#colorUptime)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* TR 101 290 Metrics */}
            <div className="bg-elecard-card rounded border border-elecard-border overflow-hidden">
                <div className="px-4 py-3 bg-elecard-darker border-b border-elecard-border">
                    <h3 className="font-semibold text-gray-200">TR 101 290 Analysis</h3>
                </div>
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <MetricItem
                        label="Sync Byte Errors"
                        value={health.tr101290_metrics.sync_byte_errors}
                        isError={health.tr101290_metrics.sync_byte_errors > 0}
                    />
                    <MetricItem
                        label="Continuity Errors"
                        value={health.tr101290_metrics.continuity_errors}
                        isError={health.tr101290_metrics.continuity_errors > 0}
                    />
                    <MetricItem
                        label="Transport Errors"
                        value={health.tr101290_metrics.transport_errors}
                        isError={health.tr101290_metrics.transport_errors > 0}
                    />
                    <MetricItem
                        label="PID Errors"
                        value={health.tr101290_metrics.pid_errors}
                        isError={health.tr101290_metrics.pid_errors > 0}
                    />
                    <MetricItem
                        label="PCR Errors"
                        value={health.tr101290_metrics.pcr_errors}
                        isError={health.tr101290_metrics.pcr_errors > 0}
                    />
                </div>
            </div>

            {/* Manifest Errors */}
            <div className="bg-elecard-card rounded border border-elecard-border overflow-hidden">
                <div className="px-4 py-3 bg-elecard-darker border-b border-elecard-border">
                    <h3 className="font-semibold text-gray-200">Manifest Analysis</h3>
                </div>
                <div className="p-4">
                    {health.manifest_errors.length === 0 ? (
                        <div className="text-gray-500 text-sm flex items-center gap-2">
                            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            No manifest errors detected.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {health.manifest_errors.map((error: any, idx: number) => (
                                <div key={idx} className="flex items-start gap-3 p-2 bg-red-900/20 rounded border border-red-900/50">
                                    <span className="text-red-500 mt-0.5">⚠</span>
                                    <div>
                                        <div className="text-red-400 font-medium text-sm">{error.error_type}</div>
                                        <div className="text-gray-400 text-xs">{error.message}</div>
                                        <div className="text-gray-500 text-[10px] mt-1">{new Date(error.timestamp).toLocaleString()}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div >
    )
}

const MetricItem = ({ label, value, isError }: { label: string, value: number, isError: boolean }) => (
    <div className="flex items-center justify-between p-3 bg-elecard-bg rounded border border-elecard-border">
        <span className="text-gray-400 text-sm">{label}</span>
        <span className={`font-mono font-bold ${isError ? 'text-red-500' : 'text-green-500'}`}>
            {value}
        </span>
    </div>
)

