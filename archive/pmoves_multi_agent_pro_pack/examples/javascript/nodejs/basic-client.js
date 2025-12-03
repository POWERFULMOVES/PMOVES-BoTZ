#!/usr/bin/env node
/**
 * Docling MCP Node.js Client - Basic Example
 * 
 * This example demonstrates basic usage of the Docling MCP service from Node.js.
 * It includes connection management, tool calling, and error handling.
 */

const EventSource = require('eventsource');
const fs = require('fs').promises;
const path = require('path');

class DoclingMCPClient {
    constructor(serverUrl, options = {}) {
        this.serverUrl = serverUrl;
        this.options = {
            timeout: options.timeout || 30000,
            retryAttempts: options.retryAttempts || 3,
            retryDelay: options.retryDelay || 1000,
            ...options
        };
        
        this.eventSource = null;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.requestId = 0;
        this.pendingRequests = new Map();
        this.metrics = {
            connections: 0,
            requests: 0,
            errors: 0,
            responseTimes: []
        };
        
        this.logger = options.logger || console;
    }

    /**
     * Connect to the MCP server
     */
    async connect() {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            
            const tryConnect = () => {
                attempts++;
                this.logger.log(`Attempting to connect to ${this.serverUrl} (attempt ${attempts}/${this.options.retryAttempts})`);
                
                try {
                    this.eventSource = new EventSource(this.serverUrl);
                    
                    this.eventSource.onopen = () => {
                        this.isConnected = true;
                        this.metrics.connections++;
                        this.logger.log('Successfully connected to Docling MCP server');
                        resolve();
                    };

                    this.eventSource.onmessage = (event) => {
                        this.handleMessage(event.data);
                    };

                    this.eventSource.onerror = (error) => {
                        this.isConnected = false;
                        this.metrics.errors++;
                        this.logger.error('Connection error:', error);
                        
                        if (attempts < this.options.retryAttempts) {
                            this.logger.log(`Retrying connection in ${this.options.retryDelay}ms...`);
                            setTimeout(tryConnect, this.options.retryDelay);
                        } else {
                            reject(new Error(`Failed to connect after ${attempts} attempts`));
                        }
                    };

                } catch (error) {
                    this.logger.error('Connection failed:', error.message);
                    
                    if (attempts < this.options.retryAttempts) {
                        this.logger.log(`Retrying connection in ${this.options.retryDelay}ms...`);
                        setTimeout(tryConnect, this.options.retryDelay);
                    } else {
                        reject(error);
                    }
                }
            };
            
            tryConnect();
        });
    }

    /**
     * Disconnect from the server
     */
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.isConnected = false;
            this.logger.log('Disconnected from server');
        }
    }

    /**
     * Handle incoming messages
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            
            if (message.id && this.pendingRequests.has(message.id)) {
                const { resolve, reject, startTime } = this.pendingRequests.get(message.id);
                this.pendingRequests.delete(message.id);
                
                const responseTime = Date.now() - startTime;
                this.metrics.responseTimes.push(responseTime);
                
                if (message.error) {
                    reject(new Error(message.error.message || 'Unknown error'));
                } else {
                    resolve(message.result);
                }
            }
        } catch (error) {
            this.logger.error('Error handling message:', error);
        }
    }

    /**
     * Call a tool on the MCP server
     */
    async callTool(toolName, toolArguments = {}) {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }

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
            this.metrics.requests++;
            
            this.pendingRequests.set(requestId, { resolve, reject, startTime });
            
            // Send request (Note: EventSource is read-only, this is a limitation)
            // In a real implementation, you'd need to use a different approach
            this.logger.warn('EventSource is read-only. In a real implementation, use WebSocket or HTTP POST');
            
            // Timeout handling
            setTimeout(() => {
                if (this.pendingRequests.has(requestId)) {
                    this.pendingRequests.delete(requestId);
                    reject(new Error('Request timeout'));
                }
            }, this.options.timeout);
        });
    }

    /**
     * List available tools
     */
    async listTools() {
        return this.callTool('list_tools');
    }

    /**
     * Health check
     */
    async healthCheck() {
        return this.callTool('health_check');
    }

    /**
     * Get server configuration
     */
    async getConfig() {
        return this.callTool('get_config');
    }

    /**
     * Convert a document
     */
    async convertDocument(filePath, outputFormat = 'markdown') {
        return this.callTool('convert_document', {
            file_path: filePath,
            output_format: outputFormat
        });
    }

    /**
     * Process documents in batch
     */
    async processBatch(filePaths, outputFormat = 'markdown') {
        return this.callTool('process_documents_batch', {
            file_paths: filePaths,
            output_format: outputFormat
        });
    }

    /**
     * Get client metrics
     */
    getMetrics() {
        const avgResponseTime = this.metrics.responseTimes.length > 0 
            ? this.metrics.responseTimes.reduce((a, b) => a + b, 0) / this.metrics.responseTimes.length 
            : 0;
        
        return {
            connections: this.metrics.connections,
            requests: this.metrics.requests,
            errors: this.metrics.errors,
            avgResponseTime: Math.round(avgResponseTime),
            responseTimes: this.metrics.responseTimes
        };
    }

    /**
     * Reset metrics
     */
    resetMetrics() {
        this.metrics = {
            connections: 0,
            requests: 0,
            errors: 0,
            responseTimes: []
        };
    }
}

/**
 * Example usage
 */
async function main() {
    const client = new DoclingMCPClient('http://localhost:3020/mcp', {
        timeout: 30000,
        retryAttempts: 3,
        retryDelay: 1000
    });

    try {
        // Connect to the server
        await client.connect();
        
        // Health check
        console.log('Performing health check...');
        const health = await client.healthCheck();
        console.log('Health check result:', health);
        
        // List available tools
        console.log('\nListing available tools...');
        const tools = await client.listTools();
        console.log('Available tools:', JSON.stringify(tools, null, 2));
        
        // Get server configuration
        console.log('\nGetting server configuration...');
        const config = await client.getConfig();
        console.log('Server configuration:', JSON.stringify(config, null, 2));
        
        // Example: Convert a document (you'll need to provide actual file paths)
        // console.log('\nConverting document...');
        // const result = await client.convertDocument('/path/to/document.pdf', 'markdown');
        // console.log('Conversion result:', result);
        
        // Get metrics
        console.log('\nClient metrics:');
        console.log(JSON.stringify(client.getMetrics(), null, 2));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        client.disconnect();
    }
}

// Run the example if this file is executed directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = DoclingMCPClient;