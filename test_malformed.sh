#!/bin/bash

IMAGE_NAME="gtfobins-mcp-server"

# Check if image exists
if ! docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo "Error: Image $IMAGE_NAME not found. Please build or pull the image."
    exit 1
fi

# MCP Protocol requires initialization first
send_mcp_sequence() {
    local test_name="$1"
    local test_request="$2"
    local container_name="ella_test_$(date +%s)_$$"
    
    echo "==============================================="
    echo "Test Case: $test_name"
    echo "Request: $test_request"
    echo "==============================================="
    
    # Create a complete MCP conversation
    {
        # 1. Initialize the server first
        echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}, "id": 1}'
        sleep 0.5
        
        # 2. Send initialized notification
        echo '{"jsonrpc": "2.0", "method": "notifications/initialized"}'
        sleep 0.5
        
        # 3. Send your test request
        echo "$test_request"
        sleep 2
        
    } | docker run --rm --name gtfobins-test -i $IMAGE_NAME python /app/server.py
    
    echo ""
}

run_tests(){
    echo "==============================================="
    echo "TESTING APPLICATION-LEVEL VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: search_gtfobins VALIDATION"
    send_mcp_sequence "search_gtfobins - missing query" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {}}, "id": 3}'
    send_mcp_sequence "search_gtfobins - empty query" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": ""}}, "id": 4}'
    send_mcp_sequence "search_gtfobins - non-string query" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": 123}}, "id": 5}'
    send_mcp_sequence "search_gtfobins - invalid query" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": "ellaella"}}, "id": 7}'
    send_mcp_sequence "search_gtfobins - invalid function_type" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": "bash", "function_type": "invalid_function"}}, "id": 6}'
    send_mcp_sequence "search_gtfobins - non-string function_type" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": "bash", "function_type": 123}}, "id": 7}'
    echo "TESTING COMPLETE: search_gtfobins VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: get_binary_details VALIDATION"
    send_mcp_sequence "get_binary_details - missing binary" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {}}, "id": 8}'
    send_mcp_sequence "get_binary_details - empty binary" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {"binary": ""}}, "id": 9}'
    send_mcp_sequence "get_binary_details - whitespace only binary" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {"binary": "   "}}, "id": 10}'
    send_mcp_sequence "get_binary_details - non-string binary" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {"binary": 123}}, "id": 11}'
    send_mcp_sequence "get_binary_details - non-existent binary" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {"binary": "nonexistent_binary_xyz"}}, "id": 12}'
    echo "TESTING COMPLETE: get_binary_details VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: list_binaries_by_function VALIDATION"
    send_mcp_sequence "list_binaries_by_function - missing function" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_binaries_by_function", "arguments": {}}, "id": 13}'
    send_mcp_sequence "list_binaries_by_function - empty function" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_binaries_by_function", "arguments": {"function": ""}}, "id": 14}'
    send_mcp_sequence "list_binaries_by_function - invalid function" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_binaries_by_function", "arguments": {"function": "invalid_function_type"}}, "id": 15}'
    send_mcp_sequence "list_binaries_by_function - non-string function" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_binaries_by_function", "arguments": {"function": 123}}, "id": 16}'
    echo "TESTING COMPLETE: list_binaries_by_function VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: GENERAL TOOL VALIDATION"
    send_mcp_sequence "unknown tool" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "nonexistent_tool", "arguments": {}}, "id": 17}'
    send_mcp_sequence "empty tool name" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "", "arguments": {}}, "id": 18}'
    send_mcp_sequence "whitespace tool name" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "   ", "arguments": {}}, "id": 18}'
    send_mcp_sequence "non-string tool name" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": 123, "arguments": {}}, "id": 19}'
    send_mcp_sequence "non-object arguments" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": "not an object"}, "id": 20}'
    echo "TESTING COMPLETE: GENERAL TOOL VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: RESOURCE VALIDATION"
    send_mcp_sequence "empty URI" '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": ""}, "id": 21}'
    send_mcp_sequence "invalid URI" '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "file://ella"}, "id": 21}'
    send_mcp_sequence "empty binary" '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "gtfobins://"}, "id": 22}'
    send_mcp_sequence "whitespace binary" '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "gtfobins://   "}, "id": 22}'
    send_mcp_sequence "non-existant binary" '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "gtfobins://i_dont_exist"}, "id": 22}'
    echo "TESTING COMPLETE: RESOURCE VALIDATION"
    echo "==============================================="
    echo ""

    echo "TESTING: VALID REQUESTS (SHOULD WORK)"
    send_mcp_sequence "Valid tools/list" '{"jsonrpc": "2.0", "method": "tools/list", "id": 21}'
    send_mcp_sequence "Valid search_gtfobins" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": "curl"}}, "id": 23}'
    send_mcp_sequence "Valid search_gtfobins with function_type" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_gtfobins", "arguments": {"query": "curl", "function_type": "sudo"}}, "id": 24}'
    send_mcp_sequence "Valid get_binary_details" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_binary_details", "arguments": {"binary": "curl"}}, "id": 25}'
    send_mcp_sequence "Valid list_binaries_by_function" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_binaries_by_function", "arguments": {"function": "shell"}}, "id": 26}'
    send_mcp_sequence "Valid get_server_status" '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_server_status", "arguments": {}}, "id": 27}'
    echo "TESTING COMPLETE: VALID REQUESTS"
    echo "==============================================="
    echo ""

    echo ""
    echo "==============================================="
    echo "TESTING COMPLETE"
    echo "==============================================="
    echo ""
}

run_tests > test_cases.txt 2>&1
