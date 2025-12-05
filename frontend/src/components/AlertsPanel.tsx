import React, { useEffect, useState } from 'react'
import { streamApi } from '../services/api'
import { format } from 'date-fns'

interface AlertsPanelProps {
    streamId: string
}

interface Alert {
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

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ streamId }) => {
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)
    const [showResolved, setShowResolved] = useState(false)
    const [activeCount, setActiveCount] = useState(0)

    useEffect(() => {
        loadAlerts()
        const interval = setInterval(loadAlerts, 10000) // Refresh every 10 seconds
        return () => clearInterval(interval)
    }, [streamId, showResolved])

    const loadAlerts = async () => {
        try {
            const response = await streamApi.getAlerts(streamId, showResolved)
            setAlerts(response.data.alerts || [])
            setActiveCount(response.data.active_count || 0)
        } catch (error) {
            console.error('Error loading alerts:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleAcknowledge = async (alertId: string) => {
        try {
            await streamApi.acknowledgeAlert(streamId, alertId)
            loadAlerts()
        } catch (error) {
            console.error('Error acknowledging alert:', error)
        }
    }

    const getSeverityStyle = (severity: string) => {
        switch (severity) {
            case 'critical':
                return 'bg-red-500/20 border-red-500/50 text-red-400'
            case 'error':
                return 'bg-orange-500/20 border-orange-500/50 text-orange-400'
            case 'warning':
                return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
            default:
                return 'bg-blue-500/20 border-blue-500/50 text-blue-400'
        }
    }

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case 'critical':
            case 'error':
                return (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                )
            case 'warning':
                return (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                )
            default:
                return (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                )
        }
    }

    const formatAlertType = (type: string) => {
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }

    return (
        <div className="bg-elecard-card rounded-lg border border-elecard-border">
            {/* Header */}
            <div className="px-4 py-3 border-b border-elecard-border flex items-center justify-between">
                <h3 className="text-white font-semibold flex items-center gap-2">
                    <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                    Alerts
                    {activeCount > 0 && (
                        <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                            {activeCount}
                        </span>
                    )}
                </h3>

                <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={showResolved}
                        onChange={(e) => setShowResolved(e.target.checked)}
                        className="rounded border-gray-600 bg-gray-700"
                    />
                    Show resolved
                </label>
            </div>

            {/* Alerts List */}
            <div className="max-h-96 overflow-y-auto">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">
                        Loading alerts...
                    </div>
                ) : alerts.length === 0 ? (
                    <div className="p-8 text-center">
                        <div className="text-green-400 mb-2">
                            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="text-gray-400">No active alerts</div>
                        <div className="text-gray-600 text-sm">Stream is healthy</div>
                    </div>
                ) : (
                    <div className="divide-y divide-elecard-border">
                        {alerts.map((alert) => (
                            <div
                                key={alert.alert_id}
                                className={`p-4 ${alert.resolved ? 'opacity-50' : ''}`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className={`p-2 rounded-lg ${getSeverityStyle(alert.severity)}`}>
                                        {getSeverityIcon(alert.severity)}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`text-sm font-medium ${getSeverityStyle(alert.severity).split(' ').pop()}`}>
                                                {formatAlertType(alert.alert_type)}
                                            </span>
                                            {alert.acknowledged && (
                                                <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded">
                                                    Acknowledged
                                                </span>
                                            )}
                                            {alert.resolved && (
                                                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                                                    Resolved
                                                </span>
                                            )}
                                        </div>

                                        <div className="text-gray-300 text-sm mb-2">
                                            {alert.message}
                                        </div>

                                        <div className="flex items-center gap-4 text-xs text-gray-500">
                                            <span>
                                                {format(new Date(alert.timestamp), 'MMM d, HH:mm:ss')}
                                            </span>
                                            {Object.keys(alert.metadata).length > 0 && (
                                                <span className="text-gray-600">
                                                    {Object.entries(alert.metadata).map(([k, v]) => `${k}: ${v}`).join(', ')}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {!alert.resolved && !alert.acknowledged && (
                                        <button
                                            onClick={() => handleAcknowledge(alert.alert_id)}
                                            className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
                                        >
                                            Acknowledge
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
