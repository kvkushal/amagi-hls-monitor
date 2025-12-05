import React, { useEffect, useState } from 'react'
import './index.css'
import { useStreamStore } from './store/useStreamStore'
import { streamApi } from './services/api'
import { StreamDetailsPanel } from './components/StreamDetailsPanel'
import { StreamCard } from './components/StreamCard'

function App() {
    const { setStreams, selectStream, streams, selectedStreamId } = useStreamStore()
    const [showAddModal, setShowAddModal] = useState(false)
    const [newStreamUrl, setNewStreamUrl] = useState('')
    const [newStreamName, setNewStreamName] = useState('')

    // Fetch streams on mount
    useEffect(() => {
        const fetchStreams = async () => {
            try {
                const response = await streamApi.getStreams()
                if (Array.isArray(response.data)) {
                    setStreams(response.data)
                } else {
                    console.error('Invalid streams response:', response.data)
                    setStreams([])
                }
            } catch (error) {
                console.error('Error fetching streams:', error)
            }
        }

        fetchStreams()
        const interval = setInterval(fetchStreams, 1000)
        return () => clearInterval(interval)
    }, [setStreams])

    const [isAddingStream, setIsAddingStream] = useState(false)

    const handleAddStream = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsAddingStream(true)
        try {
            await streamApi.createStream({
                id: `stream_${Date.now()}`,
                name: newStreamName,
                manifest_url: newStreamUrl,
                enabled: true,
                tags: []
            })
            setNewStreamUrl('')
            setNewStreamName('')
            setShowAddModal(false)
            // Refresh streams
            const response = await streamApi.getStreams()
            setStreams(response.data)
        } catch (error: any) {
            console.error('Error adding stream:', error)
            // Close modal anyway - stream may have been added
            setShowAddModal(false)
            setNewStreamUrl('')
            setNewStreamName('')
        } finally {
            setIsAddingStream(false)
        }
    }

    const handleDeleteStream = async (streamId: string) => {
        try {
            await streamApi.deleteStream(streamId)
            // Refresh streams
            const response = await streamApi.getStreams()
            setStreams(response.data)
        } catch (error) {
            alert('Error deleting stream: ' + error)
        }
    }

    // If stream is selected, show detail view
    if (selectedStreamId) {
        return <StreamDetailsPanel />
    }

    // Show grid view
    return (
        <div className="min-h-screen bg-elecard-bg flex flex-col">
            {/* Elecard Boro Header */}
            <header className="bg-elecard-darker border-b border-elecard-border">
                <div className="px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-3">
                            <h1 className="text-xl font-bold text-white">HLS Monitoring System</h1>
                        </div>

                    </div>

                    <div className="flex items-center gap-4">
                        {/* Removed unused buttons */}
                    </div>
                </div>

                {/* Sub-header with stream count and add button */}
                <div className="px-6 py-2 border-t border-elecard-border flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                            </svg>
                        </span>
                        <span>{streams.length} streams</span>
                    </div>

                    <button
                        onClick={() => setShowAddModal(true)}
                        className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium"
                    >
                        ↓ + Add Stream
                    </button>
                </div>
            </header>

            {/* Main Grid Content */}
            <main className="flex-1 p-6 overflow-auto">
                {streams.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <div className="w-24 h-24 bg-elecard-card rounded-full flex items-center justify-center mb-4">
                            <svg className="w-12 h-12 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-semibold text-gray-300 mb-2">No Streams Configured</h2>
                        <p className="text-gray-500 mb-6">Add your first HLS stream to begin monitoring</p>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium"
                        >
                            Add Stream
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {streams.map((stream) => (
                            <StreamCard
                                key={stream.id}
                                stream={stream}
                                onClick={() => selectStream(stream.id)}
                                onDelete={handleDeleteStream}
                            />
                        ))}
                    </div>
                )}
            </main>

            {/* Add Stream Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-elecard-card border border-elecard-border rounded-lg p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold text-white mb-4">Add New Stream</h2>
                        <form onSubmit={handleAddStream}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Stream Name
                                </label>
                                <input
                                    type="text"
                                    value={newStreamName}
                                    onChange={(e) => setNewStreamName(e.target.value)}
                                    className="w-full px-3 py-2 bg-elecard-darker border border-elecard-border rounded text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="My Stream"
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Manifest URL
                                </label>
                                <input
                                    type="url"
                                    value={newStreamUrl}
                                    onChange={(e) => setNewStreamUrl(e.target.value)}
                                    className="w-full px-3 py-2 bg-elecard-darker border border-elecard-border rounded text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="https://example.com/playlist.m3u8"
                                    required
                                />
                            </div>
                            <div className="flex gap-2 justify-end">
                                <button
                                    type="button"
                                    onClick={() => setShowAddModal(false)}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={isAddingStream}
                                    className={`px-4 py-2 rounded text-white ${isAddingStream ? 'bg-blue-800 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                                >
                                    {isAddingStream ? 'Adding...' : 'Add Stream'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
