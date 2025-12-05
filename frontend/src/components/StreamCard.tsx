import React, { useState } from 'react'
import { useStreamStore } from '../store/useStreamStore'

interface StreamCardProps {
    stream: any
    onClick: () => void
    onDelete?: (streamId: string) => void
}

export const StreamCard: React.FC<StreamCardProps> = ({ stream, onClick, onDelete }) => {
    const { metrics } = useStreamStore()
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

    // Get latest metric for this stream from real-time store
    const latestMetric = metrics
        .filter(m => m.filename.startsWith(`${stream.id}_`))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]

    const currentMetrics = latestMetric || stream.current_metrics

    const thumbnailUrl = currentMetrics?.sequence_number !== undefined
        ? `/data/thumbnails/${stream.id}_${currentMetrics.sequence_number}.jpg`
        : null

    const getHealthScore = () => {
        if (stream.health?.health_score?.score !== undefined) {
            return stream.health.health_score.score
        }
        return 100
    }

    const getHealthColor = () => {
        const score = getHealthScore()
        if (score >= 80) return 'green'
        if (score >= 50) return 'yellow'
        return 'red'
    }

    const getStatusColor = (status: string) => {
        const healthColor = getHealthColor()
        if (healthColor === 'red') return 'bg-red-500'
        if (healthColor === 'yellow') return 'bg-yellow-500'

        switch (status?.toLowerCase()) {
            case 'online': return 'bg-green-500'
            case 'error': return 'bg-red-500'
            case 'starting': return 'bg-yellow-500'
            default: return 'bg-gray-500'
        }
    }

    const alertCount = stream.health?.active_alerts?.length || 0

    const handleDeleteClick = (e: React.MouseEvent) => {
        e.stopPropagation()
        setShowDeleteConfirm(true)
    }

    const handleConfirmDelete = (e: React.MouseEvent) => {
        e.stopPropagation()
        if (onDelete) {
            onDelete(stream.id)
        }
        setShowDeleteConfirm(false)
    }

    const handleCancelDelete = (e: React.MouseEvent) => {
        e.stopPropagation()
        setShowDeleteConfirm(false)
    }

    return (
        <div
            className="bg-elecard-card rounded-lg border border-elecard-border overflow-hidden cursor-pointer hover:border-blue-500 transition-all relative"
            onClick={onClick}
        >
            {/* Delete Confirmation Overlay */}
            {showDeleteConfirm && (
                <div className="absolute inset-0 bg-black/80 z-10 flex flex-col items-center justify-center p-4" onClick={e => e.stopPropagation()}>
                    <div className="text-white text-center mb-4">
                        <p className="font-semibold">Delete "{stream.name}"?</p>
                        <p className="text-sm text-gray-400">This action cannot be undone.</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleCancelDelete}
                            className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded text-sm"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleConfirmDelete}
                            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm"
                        >
                            Delete
                        </button>
                    </div>
                </div>
            )}

            {/* Card Header */}
            <div className="px-4 py-3 border-b border-elecard-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(stream.status)} ring-2 ring-opacity-30 ${getHealthColor() === 'red' ? 'ring-red-500 animate-pulse' : getHealthColor() === 'yellow' ? 'ring-yellow-500' : 'ring-green-500'}`}></div>
                    <h3 className="text-white font-semibold truncate max-w-[120px]" title={stream.name}>{stream.name}</h3>
                </div>
                <div className="flex items-center gap-2 text-xs">
                    {alertCount > 0 && (
                        <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-[10px] font-medium">
                            {alertCount} {alertCount === 1 ? 'alert' : 'alerts'}
                        </span>
                    )}
                    <span className="text-gray-500">{getHealthScore()}%</span>
                    {/* Delete button */}
                    <button
                        onClick={handleDeleteClick}
                        className="p-1 hover:bg-red-500/20 rounded transition-colors group"
                        title="Delete stream"
                    >
                        <svg className="w-4 h-4 text-gray-500 group-hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Thumbnail */}
            <div className="aspect-video bg-elecard-darker relative group">
                {thumbnailUrl ? (
                    <img
                        key={thumbnailUrl}
                        src={thumbnailUrl}
                        alt={stream.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                            e.currentTarget.style.display = 'none'
                            e.currentTarget.parentElement?.classList.add('flex', 'items-center', 'justify-center')
                        }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center">
                        <svg className="w-12 h-12 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 2h6v4H7V5zm8 8v2h1v-2h-1zm-2-2H7v4h6v-4zm2 0h1V9h-1v2zm1-4V5h-1v2h1zM5 5v2H4V5h1zm0 4H4v2h1V9zm-1 4h1v2H4v-2z" clipRule="evenodd" />
                        </svg>
                    </div>
                )}
                {/* Play overlay */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                    <svg className="w-12 h-12 text-white opacity-0 group-hover:opacity-80 transition-opacity" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                    </svg>
                </div>
            </div>

            {/* Metrics Footer */}
            <div className="px-4 py-2 border-t border-elecard-border bg-elecard-darker">
                <div className="grid grid-cols-4 gap-2 text-center">
                    <div>
                        <div className="text-[10px] text-gray-500 uppercase">Bitrate</div>
                        <div className="text-sm font-mono text-gray-300">
                            {currentMetrics?.actual_bitrate
                                ? `${(currentMetrics.actual_bitrate / 1_000_000).toFixed(1)}M`
                                : '—'}
                        </div>
                    </div>
                    <div>
                        <div className="text-[10px] text-gray-500 uppercase">Download</div>
                        <div className="text-sm font-mono text-gray-300">
                            {currentMetrics?.download_speed
                                ? `${currentMetrics.download_speed.toFixed(1)}x`
                                : '—'}
                        </div>
                    </div>
                    <div>
                        <div className="text-[10px] text-gray-500 uppercase">TTFB</div>
                        <div className="text-sm font-mono text-gray-300">
                            {currentMetrics?.ttfb
                                ? `${Math.round(currentMetrics.ttfb)}ms`
                                : '—'}
                        </div>
                    </div>
                    <div>
                        <div className="text-[10px] text-gray-500 uppercase">Seg</div>
                        <div className="text-sm font-mono text-gray-300">
                            {currentMetrics?.sequence_number ?? '—'}
                        </div>
                    </div>
                </div>
            </div>

            {/* Health Bar */}
            <div className="h-1 bg-elecard-darker">
                <div
                    className={`h-full transition-all ${getHealthColor() === 'green' ? 'bg-green-500' :
                        getHealthColor() === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                    style={{ width: `${getHealthScore()}%` }}
                />
            </div>
        </div>
    )
}
