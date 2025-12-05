import React from 'react'
import { useStreamStore, TimeRange } from '../store/useStreamStore'
import clsx from 'clsx'

export const TimelineControls: React.FC = () => {
    const {
        timeRange,
        setTimeRange,
    } = useStreamStore()

    const timeRanges: TimeRange[] = ['3min', '30min', '3h', '8h', '2d', '4d']

    return (
        <div className="flex items-center gap-2 bg-elecard-card px-4 py-2 border-b border-elecard-border">
            {/* Time Range Buttons */}
            <div className="flex gap-1">
                {timeRanges.map((range) => (
                    <button
                        key={range}
                        onClick={() => setTimeRange(range)}
                        className={clsx(
                            'px-3 py-1 rounded text-sm font-medium transition-all',
                            timeRange === range
                                ? 'bg-orange-500 text-white'
                                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        )}
                    >
                        {range}
                    </button>
                ))}
            </div>
        </div>
    )
}
