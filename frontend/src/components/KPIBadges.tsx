import React from 'react'

export const KPIBadges: React.FC = () => {
    // Mock KPI data - in real app this would come from stream data
    const kpiData = {
        task: 4,
        bs: 45,  // Broadcast Service errors
        mlt15: 3,
        mls15: 2,
        alarms: [7, 22],  // Multiple alarm counts
        kpi15: 0
    }

    return (
        <div className="flex items-center gap-2">
            {/* Task */}
            <div
                className="badge bg-gray-600 text-white cursor-help"
                title="Active tasks"
            >
                <span className="font-semibold mr-1">Tsk</span>
                <span>{kpiData.task} / {kpiData.bs}</span>
            </div>

            {/* BS (Broadcast Service) - Red for errors */}
            <div
                className="badge badge-red cursor-help"
                title="Broadcast Service errors"
            >
                <span className="font-semibold mr-1">BS</span>
                <span>{kpiData.bs}</span>
            </div>

            {/* MLT.15 */}
            <div
                className="badge bg-orange-500 text-white cursor-help"
                title="Multi-Language Track warnings"
            >
                <span className="font-semibold">MLT.15</span>
            </div>

            {/* MLS.15 */}
            <div
                className="badge bg-orange-500 text-white cursor-help"
                title="Multi-Language Subtitle warnings"
            >
                <span className="font-semibold">MLS.15</span>
            </div>

            {/* Alarms */}
            <div
                className="badge bg-orange-500 text-white cursor-help"
                title="Active alarms"
            >
                <span className="font-semibold mr-1">Alarms</span>
                {kpiData.alarms.map((count, idx) => (
                    <React.Fragment key={idx}>
                        <span className="bg-orange-600 px-1 rounded">{count}</span>
                        {idx < kpiData.alarms.length - 1 && <span className="mx-0.5">/</span>}
                    </React.Fragment>
                ))}
                <span className="ml-1 bg-red-600 px-1 rounded">{kpiData.alarms.reduce((a, b) => a + b, 0)}</span>
            </div>

            {/* KPI.15 */}
            <div
                className="badge badge-gray cursor-help"
                title="KPI errors"
            >
                <span className="font-semibold mr-1">KPI.15</span>
                <span>{kpiData.kpi15}</span>
            </div>
        </div>
    )
}
