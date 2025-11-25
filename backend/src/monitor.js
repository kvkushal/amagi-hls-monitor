const axios = require('axios');
const Parser = require('m3u8-parser');

class HLSMonitor {
  constructor(url, io) {
    this.url = url;
    this.io = io;
    this.isRunning = false;
    this.intervalId = null;
    this.metrics = {
      latency: 0,
      bitrate: 0,
      segmentDuration: 0,
      variantCount: 0
    };
    this.errors = [];
  }

  async start() {
    this.isRunning = true;
    console.log(`Starting monitor for: ${this.url}`);
    
    // Check every 10 seconds
    this.intervalId = setInterval(() => {
      this.checkStream();
    }, 10000);

    // Check immediately
    await this.checkStream();
  }

  async checkStream() {
    try {
      const startTime = Date.now();
      
      // Fetch the manifest
      const response = await axios.get(this.url, {
        timeout: 5000,
        headers: {
          'User-Agent': 'HLS-Monitor/1.0'
        }
      });
      
      const latency = Date.now() - startTime;
      
      // Parse the m3u8 manifest
      const parser = new Parser.Parser();
      parser.push(response.data);
      parser.end();
      
      const manifest = parser.manifest;
      
      // Extract metrics
      this.metrics = {
        latency: latency,
        bitrate: this.calculateBitrate(manifest),
        segmentDuration: manifest.targetDuration || 0,
        variantCount: manifest.playlists?.length || 0
      };

      // Emit metrics via WebSocket
      this.io.emit('metrics', {
        url: this.url,
        metrics: this.metrics,
        timestamp: new Date(),
        status: 'ok'
      });

      console.log(`[${this.url}] Latency: ${latency}ms, Variants: ${this.metrics.variantCount}`);

    } catch (error) {
      console.error(`Error monitoring ${this.url}:`, error.message);
      
      const errorData = {
        message: error.message,
        timestamp: new Date(),
        type: error.code || 'UNKNOWN'
      };
      
      this.errors.push(errorData);

      // Emit error via WebSocket
      this.io.emit('error', {
        url: this.url,
        error: errorData
      });
    }
  }

  calculateBitrate(manifest) {
    if (manifest.playlists && manifest.playlists.length > 0) {
      // Get the highest bitrate variant
      const bitrates = manifest.playlists
        .map(p => p.attributes?.BANDWIDTH || 0)
        .filter(b => b > 0);
      
      return bitrates.length > 0 ? Math.max(...bitrates) : 0;
    }
    return 0;
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.isRunning = false;
      console.log(`Stopped monitor for: ${this.url}`);
    }
  }

  getMetrics() {
    return {
      metrics: this.metrics,
      errors: this.errors,
      isRunning: this.isRunning
    };
  }
}

module.exports = HLSMonitor;