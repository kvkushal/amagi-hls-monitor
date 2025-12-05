import { useEffect, useRef } from 'react'
import { useStreamStore } from '../store/useStreamStore'

export const useWebSocket = (streamId: string | null) => {
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<number>()

    const {
        setWsConnected,
        addMetric,
        addLoudnessData,
        addAdMarker,
        addEvent,
        addThumbnail,
    } = useStreamStore()

    useEffect(() => {
        if (!streamId) {
            // Disconnect if no stream selected
            if (wsRef.current) {
                wsRef.current.close()
                wsRef.current = null
                setWsConnected(false)
            }
            return
        }

        const connectWebSocket = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const wsUrl = `${protocol}//${window.location.host}/ws/streams/${streamId}`

            console.log('Connecting to WebSocket:', wsUrl)

            const ws = new WebSocket(wsUrl)

            ws.onopen = () => {
                console.log('WebSocket connected')
                setWsConnected(true)
            }

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data)
                    handleMessage(message)
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error)
                }
            }

            ws.onerror = (error) => {
                console.error('WebSocket error:', error)
            }

            ws.onclose = () => {
                console.log('WebSocket disconnected')
                setWsConnected(false)

                // Attempt reconnect after 3 seconds
                reconnectTimeoutRef.current = window.setTimeout(() => {
                    console.log('Attempting to reconnect...')
                    connectWebSocket()
                }, 3000)
            }

            wsRef.current = ws
        }

        connectWebSocket()

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current)
            }
            if (wsRef.current) {
                wsRef.current.close()
                wsRef.current = null
            }
            setWsConnected(false)
        }
    }, [streamId, setWsConnected])

    const handleMessage = (message: any) => {
        const { type, data } = message

        switch (type) {
            case 'segment_downloaded':
                addMetric(data)
                break

            case 'thumbnail_generated':
                addThumbnail(data.sequence, data.thumbnail_path)
                break

            case 'sprite_generated':
                // Fetch new sprite data
                console.log('Sprite generated:', data)
                break

            case 'loudness_data':
                addLoudnessData(data)
                break

            case 'ad_detected':
                addAdMarker(data)
                break

            case 'manifest_updated':
                console.log('Manifest updated:', data)
                break

            case 'error':
                addEvent({
                    stream_id: message.stream_id,
                    event_type: 'error',
                    timestamp: message.timestamp || new Date().toISOString(),
                    message: data.message || 'Unknown error',
                    severity: 'error'
                })
                break

            case 'connected':
            case 'pong':
                // Connection messages
                break

            default:
                console.log('Unknown message type:', type, data)
        }
    }

    return {
        isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    }
}
