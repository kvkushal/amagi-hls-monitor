const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
const http = require('http');
const socketIo = require('socket.io');
require('dotenv').config();

const Stream = require('./models/Stream');
const HLSMonitor = require('./monitor');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.BACKEND_PORT || 5000;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://mongo:27017/hls_monitor';

// Middleware
app.use(cors());
app.use(express.json());

// Store active monitors
const activeMonitors = new Map();

// Connect to MongoDB
mongoose.connect(MONGO_URI)
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// Routes
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    message: 'Backend is running',
    mongodb: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
    activeStreams: activeMonitors.size
  });
});

// Get all streams
app.get('/api/streams', async (req, res) => {
  try {
    const streams = await Stream.find().sort({ createdAt: -1 });
    res.json({ streams });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Add a new stream
app.post('/api/streams', async (req, res) => {
  try {
    const { url, name } = req.body;

    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    // Check if stream already exists
    let stream = await Stream.findOne({ url });
    
    if (stream) {
      return res.status(400).json({ error: 'Stream already exists' });
    }

    // Create new stream
    stream = new Stream({
      url,
      name: name || url,
      status: 'active'
    });

    await stream.save();

    // Start monitoring
    const monitor = new HLSMonitor(url, io);
    activeMonitors.set(url, monitor);
    await monitor.start();

    res.json({ 
      message: 'Stream added successfully', 
      stream 
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get stream details
app.get('/api/streams/:id', async (req, res) => {
  try {
    const stream = await Stream.findById(req.params.id);
    
    if (!stream) {
      return res.status(404).json({ error: 'Stream not found' });
    }

    // Get live metrics from monitor
    const monitor = activeMonitors.get(stream.url);
    const liveData = monitor ? monitor.getMetrics() : null;

    res.json({ 
      stream,
      liveMetrics: liveData
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Delete a stream
app.delete('/api/streams/:id', async (req, res) => {
  try {
    const stream = await Stream.findById(req.params.id);
    
    if (!stream) {
      return res.status(404).json({ error: 'Stream not found' });
    }

    // Stop monitoring
    const monitor = activeMonitors.get(stream.url);
    if (monitor) {
      monitor.stop();
      activeMonitors.delete(stream.url);
    }

    await Stream.findByIdAndDelete(req.params.id);

    res.json({ message: 'Stream deleted successfully' });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// WebSocket connection
io.on('connection', (socket) => {
  console.log(' Client connected:', socket.id);

  socket.on('disconnect', () => {
    console.log(' Client disconnected:', socket.id);
  });
});

// Start server
server.listen(PORT, '0.0.0.0', () => {
  console.log(` Backend running on port ${PORT}`);
});