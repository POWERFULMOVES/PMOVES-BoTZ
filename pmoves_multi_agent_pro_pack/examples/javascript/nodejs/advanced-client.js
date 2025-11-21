#!/usr/bin/env node
/**
 * Docling MCP Node.js Client - Advanced Example
 * 
 * This example demonstrates advanced features including:
 * - Connection pooling and management
 * - Error handling and retry logic
 * - Concurrent processing
 * - Streaming support
 * - Performance monitoring
 */

const EventSource = require('eventsource');
const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const { EventEmitter } = require('events');

class ConnectionPool {
    constructor(maxConnections = 10) {
        this.maxConnections = maxConnections;
        this.connections = [];
        this.available = [];
        this.waiting = [];
    }

    async acquire() {
        return new Promise((resolve) => {
            if (this.available.length > 0) {
                resolve(this.available.pop());
            } else if (this.connections.length < this.maxConnections) {
                const connection = this.createConnection();
                this.connections.push(connection);
                resolve(connection);
            } else {
                this.waiting.push(resolve);
            }
        });
    }

    release(connection) {
        const waiting = this.waiting.shift();
        if (waiting) {
            waiting(connection);
        } else {
            this.available.push(connection);
        }
    }

    createConnection() {
        // Connection implementation would go here
        return { id: Date.now(), active: true };
    }

    async closeAll() {
        this.connections = [];
        this.available = [];
        this.waiting = [];
    }
}

class RetryManager {
    constructor(maxAttempts = 3, baseDelay = 1000, maxDelay = 30000) {
        this.maxAttempts = maxAttempts;
        this.baseDelay = baseDelay;
        this.maxDelay = maxDelay;
    }

    async execute(operation, context = '') {
        let lastError;
        
        for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error;
                
                if (attempt === this.maxAttempts) {
                    throw new Error(`Max attempts reached${context ? ` for ${context}` : ''}: ${error.message}`);
                }
                
                const delay = Math.min(
                    this.baseDelay * Math.pow(2, attempt - 1),
                    this.maxDelay
                );
                
                console.log(`Attempt ${attempt} failed${context ? ` for ${context}` : ''}, retrying in ${delay}ms: ${error.message}`);
                await this.sleep(delay);
            }
        }
        
        throw lastError;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            requests: 0,
            errors: 0,
            responseTimes: [],
            throughput: [],
            startTime: Date.now()
        };
        this.eventEmitter = new EventEmitter();
    }

    recordRequest(responseTime, success = true) {
        this.metrics.requests++;
        
        if (success) {
            this.metrics.responseTimes.push(responseTime);
        } else {
            this.metrics.errors++;
        }
        
        this.eventEmitter.emit('metric', {
            type: success ? 'request' : 'error',
            responseTime,
            timestamp: Date.now()
        });
    }

    getStats() {
        const responseTimes = this.metrics.responseTimes;
        const avgResponseTime = responseTimes.length > 0 
            ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length 
            : 0;
        
        const p95ResponseTime = this.calculatePercentile(responseTimes, 0.95);
        const p99ResponseTime = this.calculatePercentile(responseTimes, 0.99);
        
        const uptime = Date.now() - this.metrics.startTime;
        const throughput = this.metrics.requests / (uptime / 1000);
        
        return {
            totalRequests: this.metrics.requests,
            totalErrors: this.metrics.errors,
            errorRate: this.metrics.requests > 0 ? (this.metrics.errors / this.metrics.requests) * 100 : 0,
            avgResponseTime: Math.round(avgResponseTime),
            p95ResponseTime: Math.round(p95ResponseTime),
            p99ResponseTime: Math.round(p99ResponseTime),
            throughput: Math.round(throughput * 100) / 100,
            uptime: Math.round(uptime / 1000)
        };
    }

    calculatePercentile(arr, percentile) {
        if (arr.length === 0) return 0;
        const sorted = arr.slice().sort((a, b) => a - b);
        const index = Math.ceil(sorted.length * percentile) - 1;
        return sorted[Math.max(0, index)];
    }

    reset() {
        this.metrics = {
            requests: 0,
            errors: 0,
            responseTimes: [],
            throughput: [],
            startTime: Date.now()
        };
    }
}

class DoclingMCPAdvancedClient extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.options = {
            serverUrl: options.serverUrl || 'http://localhost:3020/mcp',
            gatewayUrl: options.gatewayUrl || 'http://localhost:2091',
            timeout: options.timeout || 30000,
            maxConnections: options.maxConnections || 10,
            retryAttempts: options.retryAttempts || 3,
            retryDelay: options.retryDelay || 1000,
            enableMetrics: options.enableMetrics !== false,
            ...options
        };
        
        this.connectionPool = new ConnectionPool(this.options.maxConnections);
        this.retryManager = new RetryManager(
            this.options.retryAttempts,
            this.options.retryDelay
        );
        this.performanceMonitor = new PerformanceMonitor();
        
        this.isConnected = false;
        this.eventSource = null;
        this.requestId = 0;
        this.pendingRequests = new Map();
        
        // Setup metrics monitoring
        if (this.options.enableMetrics) {
            this.performanceMonitor.eventEmitter.on('metric', (metric) => {
                this.emit('metric', metric);
            });
        }
    }

    async connect() {
        return this.retryManager.execute(async () => {
            this.emit('connecting', { url: this.options.serverUrl });
            
            try {
                // Test connection with health check first
                await this.healthCheck();
                
                // Setup SSE connection
                this.eventSource = new EventSource(this.options.serverUrl);
                
                this.eventSource.onopen = () => {
                    this.isConnected = true;
                    this.emit('connected', { url: this.options.serverUrl });
                };

                this.eventSource.onmessage = (event) => {
                    this.handleMessage(event.data);
                };

                this.eventSource.onerror = (error) => {
                    this.isConnected = false;
                    this.emit('error', { type: 'connection', error });
                };

                // Wait for connection to be established
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Connection timeout'));
                    }, this.options.timeout);

                    this.once('connected', () => {
                        clearTimeout(timeout);
                        resolve();
                    });

                    this.once('error', (error) => {
                        clearTimeout(timeout);
                        reject(error);
                    });
                });

            } catch (error) {
                this.emit('error', { type: 'connection', error });
                throw error;
            }
        }, 'connection');
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            this.isConnected = false;
            this.emit('disconnected');
        }
    }

    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            
            if (message.id && this.pendingRequests.has(message.id)) {
                const { resolve, reject, startTime } = this.pendingRequests.get(message.id);
                this.pendingRequests.delete(message.id);
                
                const responseTime = Date.now() - startTime;
                
                if (message.error) {
                    this.performanceMonitor.recordRequest(responseTime, false);
                    reject(new Error(message.error.message || 'Unknown error'));
                } else {
                    this.performanceMonitor.recordRequest(responseTime, true);
                    resolve(message.result);
                }
            }
        } catch (error) {
            this.emit('error', { type: 'message_handling', error });
        }
    }

    async callTool(toolName, toolArguments = {}) {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }

        return this.retryManager.execute(async () => {
            const requestId = ++this.requestId;
            const request = {
                jsonrpc: '2.0',
                id: requestId,
                method: 'tools/call',
                params: {
                    name: toolName,
                    arguments: toolArguments
                }
            };

            return new Promise((resolve, reject) => {
                const startTime = Date.now();
                
                this.pendingRequests.set(requestId, { resolve, reject, startTime });
                
                // Note: EventSource is read-only, so we use HTTP POST for actual requests
                this.sendHttpRequest(request)
                    .then(result => {
                        this.pendingRequests.delete(requestId);
                        const responseTime = Date.now() - startTime;
                        this.performanceMonitor.recordRequest(responseTime, true);
                        resolve(result);
                    })
                    .catch(error => {
                        this.pendingRequests.delete(requestId);
                        const responseTime = Date.now() - startTime;
                        this.performanceMonitor.recordRequest(responseTime, false);
                        reject(error);
                    });
                
                // Timeout handling
                setTimeout(() => {
                    if (this.pendingRequests.has(requestId)) {
                        this.pendingRequests.delete(requestId);
                        reject(new Error('Request timeout'));
                    }
                }, this.options.timeout);
            });
        }, `tool call: ${toolName}`);
    }

    async sendHttpRequest(request) {
        try {
            const response = await axios.post(
                `${this.options.gatewayUrl}/tools/call`,
                request,
                {
                    timeout: this.options.timeout,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            return response.data;
        } catch (error) {
            if (error.response) {
                throw new Error(`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}`);
            } else if (error.request) {
                throw new Error('No response received from server');
            } else {
                throw new Error(`Request error: ${error.message}`);
            }
        }
    }

    // Tool-specific methods
    async healthCheck() {
        const response = await axios.get(`${this.options.serverUrl}/health`, {
            timeout: this.options.timeout
        });
        return response.data;
    }

    async listTools() {
        return this.callTool('list_tools');
    }

    async getConfig() {
        return this.callTool('get_config');
    }

    async convertDocument(filePath, outputFormat = 'markdown') {
        return this.callTool('convert_document', {
            file_path: filePath,
            output_format: outputFormat
        });
    }

    async processBatch(filePaths, outputFormat = 'markdown') {
        return this.callTool('process_documents_batch', {
            file_paths: filePaths,
            output_format: outputFormat
        });
    }

    // Advanced features
    async convertDocumentsConcurrently(filePaths, outputFormat = 'markdown', maxConcurrency = 5) {
        const results = [];
        const chunks = this.chunkArray(filePaths, maxConcurrency);
        
        for (const chunk of chunks) {
            const promises = chunk.map(filePath => 
                this.convertDocument(filePath, outputFormat)
                    .catch(error => ({ error: error.message, filePath }))
            );
            
            const chunkResults = await Promise.all(promises);
            results.push(...chunkResults);
        }
        
        return results;
    }

    async processBatchWithProgress(filePaths, outputFormat = 'markdown') {
        const results = [];
        const total = filePaths.length;
        
        for (let i = 0; i < filePaths.length; i++) {
            const filePath = filePaths[i];
            const progress = ((i + 1) / total) * 100;
            
            this.emit('progress', {
                current: i + 1,
                total,
                percentage: Math.round(progress),
                file: filePath
            });
            
            try {
                const result = await this.convertDocument(filePath, outputFormat);
                results.push({ success: true, filePath, result });
            } catch (error) {
                results.push({ success: false, filePath, error: error.message });
            }
        }
        
        return results;
    }

    chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }

    getMetrics() {
        return this.performanceMonitor.getStats();
    }

    resetMetrics() {
        this.performanceMonitor.reset();
    }
}

// Example usage
async function main() {
    const client = new DoclingMCPAdvancedClient({
        serverUrl: 'http://localhost:3020/mcp',
        gatewayUrl: 'http://localhost:2091',
        timeout: 30000,
        maxConnections: 10,
        retryAttempts: 3,
        enableMetrics: true
    });

    // Setup event listeners
    client.on('connecting', (data) => {
        console.log('Connecting to:', data.url);
    });

    client.on('connected', (data) => {
        console.log('Connected to:', data.url);
    });

    client.on('disconnected', () => {
        console.log('Disconnected from server');
    });

    client.on('error', (error) => {
        console.error('Client error:', error);
    });

    client.on('progress', (data) => {
        console.log(`Progress: ${data.percentage}% (${data.current}/${data.total}) - ${data.file}`);
    });

    client.on('metric', (metric) => {
        console.log('Metric:', metric);
    });

    try {
        // Connect to server
        await client.connect();
        
        // Health check
        console.log('\n=== Health Check ===');
        const health = await client.healthCheck();
        console.log('Health:', JSON.stringify(health, null, 2));
        
        // List tools
        console.log('\n=== Available Tools ===');
        const tools = await client.listTools();
        console.log('Tools:', JSON.stringify(tools, null, 2));
        
        // Get configuration
        console.log('\n=== Server Configuration ===');
        const config = await client.getConfig();
        console.log('Config:', JSON.stringify(config, null, 2));
        
        // Simulate concurrent document processing
        console.log('\n=== Concurrent Document Processing ===');
        const testFiles = [
            '/tmp/test1.pdf',
            '/tmp/test2.docx',
            '/tmp/test3.pptx',
            '/tmp/test4.xlsx',
            '/tmp/test5.html'
        ];
        
        // Note: These files don't exist, so they'll fail, but it demonstrates the pattern
        const results = await client.convertDocumentsConcurrently(testFiles, 'markdown', 3);
        console.log('Concurrent results:', results);
        
        // Show metrics
        console.log('\n=== Performance Metrics ===');
        const metrics = client.getMetrics();
        console.log('Metrics:', JSON.stringify(metrics, null, 2));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await client.disconnect();
    }
}

// Run the example
if (require.main === module) {
    main().catch(console.error);
}

module.exports = DoclingMCPAdvancedClient;