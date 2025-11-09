#!/bin/bash
# Docling MCP curl Examples - Basic Usage
# This script demonstrates basic usage of the Docling MCP service using curl

# Configuration
MCP_SERVER_URL="http://localhost:3020"
MCP_GATEWAY_URL="http://localhost:2091"
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if server is running
check_server() {
    log "Checking if Docling MCP server is running..."
    
    if curl -s -f -m 5 "${MCP_SERVER_URL}/health" > /dev/null; then
        success "Docling MCP server is running"
        return 0
    else
        error "Docling MCP server is not accessible at ${MCP_SERVER_URL}"
        error "Please start the server first with: docker-compose -f docker-compose.mcp-pro.yml up docling-mcp"
        return 1
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} "${MCP_SERVER_URL}/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Health check passed"
        echo "Response: $body" | jq . 2>/dev/null || echo "Response: $body"
    else
        error "Health check failed (HTTP $http_code)"
        echo "Response: $body"
    fi
}

# Test SSE connection
test_sse() {
    log "Testing Server-Sent Events connection..."
    
    timeout 5 curl -s -N -H "Accept: text/event-stream" "${MCP_SERVER_URL}/mcp" | while read -r line; do
        if [[ $line == data:* ]]; then
            data=${line#data: }
            success "Received SSE data: $data"
        fi
    done
    
    warning "SSE connection test completed (timeout after 5 seconds)"
}

# List tools via MCP gateway
list_tools_gateway() {
    log "Listing available tools via MCP gateway..."
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/list" \
        -H "Content-Type: application/json" \
        -d '{}')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Tools listed successfully"
        echo "Available tools:" | jq . 2>/dev/null || echo "$body"
    else
        error "Failed to list tools (HTTP $http_code)"
        echo "Response: $body"
    fi
}

# Call health check tool via gateway
health_check_tool() {
    log "Calling health_check tool via MCP gateway..."
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "health_check",
            "arguments": {}
        }')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Health check tool called successfully"
        echo "Result:" | jq . 2>/dev/null || echo "$body"
    else
        error "Failed to call health check tool (HTTP $http_code)"
        echo "Response: $body"
    fi
}

# Call get_config tool via gateway
get_config_tool() {
    log "Calling get_config tool via MCP gateway..."
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "get_config",
            "arguments": {}
        }')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Get config tool called successfully"
        echo "Configuration:" | jq . 2>/dev/null || echo "$body"
    else
        error "Failed to call get config tool (HTTP $http_code)"
        echo "Response: $body"
    fi
}

# Simulate document conversion (requires actual files)
simulate_conversion() {
    log "Simulating document conversion..."
    
    # Create a sample document content
    sample_doc="Sample document content for testing conversion.\nThis is a test document with multiple lines.\nIt contains various formatting elements."
    
    echo "$sample_doc" > /tmp/sample_document.txt
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"convert_document\",
            \"arguments\": {
                \"file_path\": \"/tmp/sample_document.txt\",
                \"output_format\": \"markdown\"
            }
        }")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Document conversion simulated successfully"
        echo "Result:" | jq . 2>/dev/null || echo "$body"
    else
        warning "Document conversion failed (expected - no actual Docling processing)"
        echo "Response: $body"
    fi
    
    # Clean up
    rm -f /tmp/sample_document.txt
}

# Batch processing simulation
simulate_batch_processing() {
    log "Simulating batch document processing..."
    
    # Create sample documents
    mkdir -p /tmp/test_docs
    echo "Document 1 content" > /tmp/test_docs/doc1.txt
    echo "Document 2 content" > /tmp/test_docs/doc2.txt
    echo "Document 3 content" > /tmp/test_docs/doc3.txt
    
    response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "process_documents_batch",
            "arguments": {
                "file_paths": ["/tmp/test_docs/doc1.txt", "/tmp/test_docs/doc2.txt", "/tmp/test_docs/doc3.txt"],
                "output_format": "markdown"
            }
        }')
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        success "Batch processing simulated successfully"
        echo "Result:" | jq . 2>/dev/null || echo "$body"
    else
        warning "Batch processing failed (expected - no actual Docling processing)"
        echo "Response: $body"
    fi
    
    # Clean up
    rm -rf /tmp/test_docs
}

# Test with different HTTP methods
test_http_methods() {
    log "Testing different HTTP methods..."
    
    # GET request to health endpoint
    log "Testing GET /health"
    curl -s -X GET "${MCP_SERVER_URL}/health" | jq . 2>/dev/null || echo "GET /health response"
    
    # OPTIONS request for CORS
    log "Testing OPTIONS /mcp (CORS preflight)"
    curl -s -X OPTIONS "${MCP_SERVER_URL}/mcp" \
        -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: GET" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -i
    
    # HEAD request
    log "Testing HEAD /health"
    curl -s -I "${MCP_SERVER_URL}/health"
}

# Performance test
performance_test() {
    log "Running performance test..."
    
    local iterations=10
    local total_time=0
    local success_count=0
    
    for i in $(seq 1 $iterations); do
        start_time=$(date +%s%3N)
        
        response=$(curl -s -w "\n%{http_code}" -m ${TIMEOUT} "${MCP_SERVER_URL}/health")
        http_code=$(echo "$response" | tail -n1)
        
        end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))
        
        if [ "$http_code" = "200" ]; then
            success_count=$((success_count + 1))
            total_time=$((total_time + response_time))
            echo "Request $i: ${response_time}ms"
        else
            echo "Request $i: Failed (HTTP $http_code)"
        fi
    done
    
    if [ $success_count -gt 0 ]; then
        avg_time=$((total_time / success_count))
        success "Performance test completed:"
        echo "  Total requests: $iterations"
        echo "  Successful requests: $success_count"
        echo "  Average response time: ${avg_time}ms"
        echo "  Success rate: $((success_count * 100 / iterations))%"
    else
        error "All requests failed"
    fi
}

# Error handling test
error_handling_test() {
    log "Testing error handling..."
    
    # Test with invalid endpoint
    log "Testing invalid endpoint..."
    curl -s -w "\n%{http_code}" -m ${TIMEOUT} "${MCP_SERVER_URL}/invalid_endpoint" || echo "Expected error for invalid endpoint"
    
    # Test with invalid tool name
    log "Testing invalid tool name..."
    curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "invalid_tool_name",
            "arguments": {}
        }'
    
    # Test with missing required parameters
    log "Testing missing required parameters..."
    curl -s -w "\n%{http_code}" -m ${TIMEOUT} \
        -X POST "${MCP_GATEWAY_URL}/tools/call" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "convert_document",
            "arguments": {}
        }'
}

# Main execution
main() {
    log "Starting Docling MCP curl examples..."
    
    # Check server availability
    if ! check_server; then
        exit 1
    fi
    
    # Run all tests
    health_check
    echo
    
    test_sse
    echo
    
    list_tools_gateway
    echo
    
    health_check_tool
    echo
    
    get_config_tool
    echo
    
    simulate_conversion
    echo
    
    simulate_batch_processing
    echo
    
    test_http_methods
    echo
    
    performance_test
    echo
    
    error_handling_test
    echo
    
    success "All curl examples completed!"
}

# Run main function
main "$@"