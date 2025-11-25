import { useState, useEffect } from 'react'
import axios from 'axios'
import io from 'socket.io-client'

const API_URL = 'http://localhost:5000'

function App() {
  const [streams, setStreams] = useState([])
  const [newStreamUrl, setNewStreamUrl] = useState('')
  const [newStreamName, setNewStreamName] = useState('')
  const [socket, setSocket] = useState(null)
  const [liveMetrics, setLiveMetrics] = useState({})

  // Connect to WebSocket
  useEffect(() => {
    const newSocket = io(API_URL)
    setSocket(newSocket)

    newSocket.on('metrics', (data) => {
      console.log('Received metrics:', data)
      setLiveMetrics(prev => ({
        ...prev,
        [data.url]: data
      }))
    })

    newSocket.on('error', (data) => {
      console.error('Stream error:', data)
    })

    return () => newSocket.close()
  }, [])

  // Fetch streams on load
  useEffect(() => {
    fetchStreams()
  }, [])

  const fetchStreams = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/streams`)
      setStreams(response.data.streams)
    } catch (error) {
      console.error('Error fetching streams:', error)
    }
  }

  const addStream = async (e) => {
    e.preventDefault()
    if (!newStreamUrl) return

    try {
      await axios.post(`${API_URL}/api/streams`, {
        url: newStreamUrl,
        name: newStreamName || newStreamUrl
      })
      setNewStreamUrl('')
      setNewStreamName('')
      fetchStreams()
    } catch (error) {
      alert('Error adding stream: ' + error.response?.data?.error)
    }
  }

  const deleteStream = async (id) => {
    try {
      await axios.delete(`${API_URL}/api/streams/${id}`)
      fetchStreams()
    } catch (error) {
      console.error('Error deleting stream:', error)
    }
  }

  const getStreamStatus = (stream) => {
    const metrics = liveMetrics[stream.url]
    if (!metrics) return 'waiting'
    if (metrics.status === 'ok') return 'healthy'
    return 'error'
  }

  const formatBitrate = (bitrate) => {
    if (!bitrate) return 'N/A'
    return (bitrate / 1000000).toFixed(2) + ' Mbps'
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>🎥 HLS Stream Monitor</h1>
      
      {/* Add Stream Form */}
      <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
        <h2>Add New Stream</h2>
        <form onSubmit={addStream} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Stream URL (e.g., https://...m3u8)"
            value={newStreamUrl}
            onChange={(e) => setNewStreamUrl(e.target.value)}
            style={{ flex: '2', padding: '10px', fontSize: '14px' }}
            required
          />
          <input
            type="text"
            placeholder="Stream Name (optional)"
            value={newStreamName}
            onChange={(e) => setNewStreamName(e.target.value)}
            style={{ flex: '1', padding: '10px', fontSize: '14px' }}
          />
          <button type="submit" style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Add Stream
          </button>
        </form>
      </div>

      {/* Stream List */}
      <h2>Active Streams ({streams.length})</h2>
      
      {streams.length === 0 ? (
        <p>No streams yet. Add one above!</p>
      ) : (
        <div style={{ display: 'grid', gap: '20px' }}>
          {streams.map(stream => {
            const status = getStreamStatus(stream)
            const metrics = liveMetrics[stream.url]
            
            return (
              <div key={stream._id} style={{
                border: '2px solid #ddd',
                borderRadius: '8px',
                padding: '20px',
                background: 'white',
                borderColor: status === 'healthy' ? '#28a745' : status === 'error' ? '#dc3545' : '#ffc107'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '15px' }}>
                  <div>
                    <h3 style={{ margin: '0 0 5px 0' }}>{stream.name}</h3>
                    <p style={{ margin: 0, fontSize: '12px', color: '#666', wordBreak: 'break-all' }}>{stream.url}</p>
                  </div>
                  <button 
                    onClick={() => deleteStream(stream._id)}
                    style={{ padding: '5px 15px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Delete
                  </button>
                </div>

                {/* Metrics */}
                {metrics ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '15px' }}>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Status</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: metrics.status === 'ok' ? '#28a745' : '#dc3545' }}>
                        {metrics.status === 'ok' ? '✓ Healthy' : '✗ Error'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Latency</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{metrics.metrics.latency}ms</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Bitrate</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatBitrate(metrics.metrics.bitrate)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Variants</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{metrics.metrics.variantCount}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Segment Duration</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{metrics.metrics.segmentDuration}s</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Last Updated</div>
                      <div style={{ fontSize: '14px' }}>{new Date(metrics.timestamp).toLocaleTimeString()}</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ color: '#666', fontStyle: 'italic' }}>Waiting for metrics...</div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default App