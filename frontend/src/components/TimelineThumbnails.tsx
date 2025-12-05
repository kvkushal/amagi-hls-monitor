import React, { useState, useRef } from 'react'
import { useStreamStore, ThumbnailDensity } from '../store/useStreamStore'
import clsx from 'clsx'
import { format } from 'date-fns'

export const TimelineThumbnails: React.FC = () => {
    const { thumbnailDensity, setThumbnailDensity, metrics, thumbnails } = useStreamStore()
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
    const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 })
    const containerRef = useRef<HTMLDivElement>(null)

    const densities: ThumbnailDensity[] = [100, 75, 50, 25]

    // Use real metrics for thumbnails
    // Sort metrics by timestamp (oldest first) for timeline
    const sortedMetrics = [...metrics].sort((a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    const timelineThumbnails = sortedMetrics.map((metric, i) => ({
        index: i,
        timestamp: new Date(metric.timestamp),
        hasError: false, // We could check metric status if available
        path: metric.sequence_number !== undefined ? thumbnails[metric.sequence_number] : undefined,
        sequence: metric.sequence_number
    }))

    const handleThumbnailHover = (index: number, event: React.MouseEvent) => {
        setHoveredIndex(index)

        const rect = event.currentTarget.getBoundingClientRect()
        setPreviewPosition({
            x: rect.left + rect.width / 2,
            y: rect.top
        })
    }

    const handleThumbnailClick = (index: number) => {
        console.log('Navigate to thumbnail', index)
        // Would navigate to specific time
    }

    // Calculate thumbnail spacing based on density
    const getSpacing = () => {
        switch (thumbnailDensity) {
            case 100: return 0
            case 75: return 2
            case 50: return 4
            case 25: return 8
            default: return 4
        }
    }

    const spacing = getSpacing()

    return (
        <div className="bg-elecard-card border-b border-elecard-border">
            {/* Density Controls */}
            <div className="px-4 py-3 border-b border-elecard-border">
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-300">Thumbnails</span>
                    <div className="flex gap-2">
                        {densities.map((density) => (
                            <label key={density} className="flex items-center gap-1 cursor-pointer">
                                <input
                                    type="radio"
                                    name="density"
                                    value={density}
                                    checked={thumbnailDensity === density}
                                    onChange={() => setThumbnailDensity(density)}
                                    className="form-radio text-blue-600"
                                />
                                <span className="text-sm text-gray-400">{density}%</span>
                            </label>
                        ))}
                    </div>
                </div>
            </div>

            {/* Thumbnail Strip */}
            <div
                ref={containerRef}
                className="px-4 py-4 overflow-x-auto"
                style={{ scrollbarWidth: 'thin' }}
            >
                <div className="flex gap-0.5" style={{ gap: `${spacing}px` }}>
                    {timelineThumbnails.map((thumb) => (
                        <div
                            key={thumb.index}
                            className="relative flex-shrink-0 cursor-pointer"
                            onMouseEnter={(e) => handleThumbnailHover(thumb.index, e)}
                            onMouseLeave={() => setHoveredIndex(null)}
                            onClick={() => handleThumbnailClick(thumb.index)}
                        >
                            {/* Thumbnail */}
                            <div
                                className={clsx(
                                    'w-16 h-9 rounded overflow-hidden border-2 transition-all',
                                    hoveredIndex === thumb.index
                                        ? 'border-white scale-105'
                                        : 'border-transparent'
                                )}
                            >
                                {thumb.path ? (
                                    <img
                                        src={thumb.path}
                                        alt={`Thumbnail ${thumb.sequence}`}
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                            // Fallback to error placeholder on load failure
                                            e.currentTarget.style.display = 'none'
                                            e.currentTarget.parentElement?.classList.add('bg-gray-600')
                                        }}
                                    />
                                ) : (
                                    // Placeholder if no thumbnail yet
                                    <div className="w-full h-full bg-gradient-to-br from-blue-900 to-purple-900" />
                                )}
                            </div>

                            {/* Timestamp Label */}
                            <div className="text-[9px] text-gray-400 text-center mt-0.5 font-mono">
                                {format(thumb.timestamp, 'HH:mm:ss')}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Hover Preview Tooltip */}
            {hoveredIndex !== null && timelineThumbnails[hoveredIndex] && (
                <div
                    className="timeline-preview"
                    style={{
                        left: `${previewPosition.x}px`,
                        top: `${previewPosition.y}px`,
                    }}
                >
                    {timelineThumbnails[hoveredIndex].path ? (
                        <img
                            src={timelineThumbnails[hoveredIndex].path}
                            alt="Preview"
                            width="160"
                            height="90"
                            className="bg-gray-800"
                        />
                    ) : (
                        <div className="w-40 h-[90px] bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                            No Preview
                        </div>
                    )}
                    <div className="timeline-preview-timestamp">
                        {format(timelineThumbnails[hoveredIndex].timestamp, 'HH:mm:ss')}
                    </div>
                </div>
            )}
        </div>
    )
}
