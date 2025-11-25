const mongoose = require('mongoose');

const streamSchema = new mongoose.Schema({
  url: {
    type: String,
    required: true,
    unique: true
  },
  name: {
    type: String,
    required: true
  },
  status: {
    type: String,
    enum: ['active', 'error', 'stopped'],
    default: 'active'
  },
  metrics: {
    latency: Number,
    bitrate: Number,
    segmentDuration: Number,
    variantCount: Number
  },
  errors: [{
    message: String,
    timestamp: Date,
    type: String
  }],
  lastChecked: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Stream', streamSchema);