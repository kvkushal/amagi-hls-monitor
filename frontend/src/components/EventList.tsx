import React from 'react'
import { useStreamStore } from '../store/useStreamStore'
import { format } from 'date-fns'

export const EventList: React.FC = () => {
    const { events } = useStreamStore()

    // Show latest 50 events
    const displayEvents = events.slice(0, 50)

    return (
        <div className="bg-elecard-card rounded-lg border border-elecard-border">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-elecard-border">
                <h3 className="text-sm font-medium text-gray-300">Stream Events</h3>
                <span className="text-xs text-gray-500">{events.length} events</span>
            </div>

            {/* Event Table */}
            <div className="overflow-auto max-h-80">
                <table className="min-w-full divide-y divide-elecard-border">
                    <thead className="bg-elecard-darker sticky top-0">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Event
                            </th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Time
                            </th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Message
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-elecard-border">
                        {displayEvents.length === 0 ? (
                            <tr>
                                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                                    No events to display
                                </td>
                            </tr>
                        ) : (
                            displayEvents.map((event, idx) => (
                                <tr key={idx} className="hover:bg-elecard-darker transition-colors text-sm">
                                    <td className="px-4 py-2 text-gray-300">
                                        <div className="flex items-center gap-2">
                                            {event.severity === 'error' && (
                                                <span className="w-2 h-2 bg-red-500 rounded-full" />
                                            )}
                                            {event.severity === 'warning' && (
                                                <span className="w-2 h-2 bg-orange-500 rounded-full" />
                                            )}
                                            {event.severity === 'info' && (
                                                <span className="w-2 h-2 bg-blue-500 rounded-full" />
                                            )}
                                            <span className="font-medium">{event.event_type}</span>
                                        </div>
                                    </td>
                                    <td className="px-4 py-2 text-gray-400 font-mono text-xs">
                                        {format(new Date(event.timestamp), 'HH:mm:ss')}
                                    </td>
                                    <td className="px-4 py-2 text-gray-300">
                                        <div className="truncate max-w-md" title={event.message}>
                                            {event.message}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
