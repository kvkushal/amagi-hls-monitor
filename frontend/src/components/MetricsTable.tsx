import React from 'react'
import { useStreamStore } from '../store/useStreamStore'

export const MetricsTable: React.FC = () => {
    const { metrics } = useStreamStore()

    // Get latest metrics (latest 50)
    const displayMetrics = metrics.slice(-50).reverse()

    if (displayMetrics.length === 0) {
        return (
            <div className="bg-elecard-card p-4 rounded-lg border border-elecard-border">
                <h3 className="text-lg font-semibold text-gray-200 mb-4">Media rendition</h3>
                <div className="text-center py-8 text-gray-400">
                    No metrics data available
                </div>
            </div>
        )
    }

    return (
        <div className="bg-elecard-card rounded-lg border border-elecard-border overflow-hidden">
            <div className="px-4 py-3 border-b border-elecard-border">
                <h3 className="text-lg font-semibold text-gray-200">Media rendition</h3>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-elecard-border">
                    <thead className="bg-elecard-darker">
                        <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                URI
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Resolution
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Bandwidth
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                File
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Actual bitrate
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Download speed
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Segment duration
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                TTFB
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Download time
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Segment size, B
                            </th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Segment size, MB
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-elecard-border">
                        {displayMetrics.map((metric, idx) => (
                            <tr key={idx} className="hover:bg-elecard-darker transition-colors">
                                <td className="px-3 py-2 text-sm text-gray-300">
                                    <div className="flex items-center gap-2">
                                        {/* Thumbnail preview */}
                                        <div className="w-8 h-5 bg-gradient-to-br from-blue-900 to-purple-900 rounded flex-shrink-0" />
                                        <div className="truncate max-w-[200px]" title={metric.uri}>
                                            {metric.filename || metric.uri.split('/').pop()}
                                        </div>
                                    </div>
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300">
                                    {metric.resolution || '-'}
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300">
                                    {metric.bandwidth ? `${(metric.bandwidth / 1000000).toFixed(2)} Mbps` : '-'}
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 truncate max-w-[150px]" title={metric.filename}>
                                    {metric.filename}
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.actual_bitrate.toFixed(2)} Mbps
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.download_speed.toFixed(2)} Mbps
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.segment_duration.toFixed(1)} s
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.ttfb.toFixed(1)} ms
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.download_time.toFixed(1)} ms
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.segment_size_bytes.toLocaleString()}
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-300 text-right font-mono">
                                    {metric.segment_size_mb.toFixed(3)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
