#!/usr/bin/env python3
"""
GTFOBins MCP Server
A simple MCP server that provides access to GTFOBins data
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging
import sys

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import AnyUrl
import mcp.server.stdio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GTFOBinsServer:
    def __init__(self):
        self.server = Server("gtfobins-server")
        self.gtfobins_path = Path("/app/gtfobins-data")
        self.binaries_data = {}
        self.load_gtfobins_data()
        
    def load_gtfobins_data(self):
        """Load GTFOBins data from the cloned repository"""
        binaries_dir = self.gtfobins_path / "_gtfobins"
        
        if not binaries_dir.exists():
            logger.error(f"GTFOBins directory not found: {binaries_dir}")
            print(f"ERROR: GTFOBins directory not found: {binaries_dir}", file=sys.stderr)
            return
            
        for md_file in binaries_dir.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse YAML frontmatter and markdown content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        yaml_content = parts[1]
                        markdown_content = parts[2].strip()
                        
                        try:
                            metadata = yaml.safe_load(yaml_content)
                            binary_name = md_file.stem
                            
                            self.binaries_data[binary_name] = {
                                'metadata': metadata,
                                'content': markdown_content,
                                'functions': metadata.get('functions', {}) if metadata else {}
                            }
                        except yaml.YAMLError as e:
                            logger.warning(f"Error parsing YAML in {md_file}: {e}")
                            print(f"YAML Error in {md_file}: {e}", file=sys.stderr)
            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")
                print(f"Error loading {md_file}: {e}", file=sys.stderr)
                
        logger.info(f"Loaded {len(self.binaries_data)} GTFOBins entries")
        print(f"Loaded {len(self.binaries_data)} GTFOBins entries", file=sys.stderr)

    def setup_handlers(self):
        """Set up MCP server handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available GTFOBins resources"""
            resources = []
            for binary_name in self.binaries_data.keys():
                resources.append(Resource(
                    uri=AnyUrl(f"gtfobins://{binary_name}"),
                    name=f"GTFOBins: {binary_name}",
                    description=f"GTFOBins entry for {binary_name}",
                    mimeType="text/plain"
                ))
            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str:
            """Read a specific GTFOBins resource"""
            if not str(uri).startswith("gtfobins://"):
                raise ValueError(f"Unsupported URI scheme: {uri}")
                
            binary_name = str(uri).replace("gtfobins://", "")
            
            if binary_name not in self.binaries_data:
                raise ValueError(f"Binary not found: {binary_name}")
                
            data = self.binaries_data[binary_name]
            
            # Format the response
            result = f"# {binary_name}\n\n"
            
            if data['metadata']:
                result += "## Metadata\n"
                for key, value in data['metadata'].items():
                    if key != 'functions':
                        result += f"- **{key}**: {value}\n"
                result += "\n"
            
            if data['functions']:
                result += "## Available Functions\n"
                for func_name, func_data in data['functions'].items():
                    result += f"### {func_name.title()}\n"
                    if isinstance(func_data, list):
                        for item in func_data:
                            if isinstance(item, dict) and 'code' in item:
                                result += f"```bash\n{item['code']}\n```\n"
                                if 'description' in item:
                                    result += f"*{item['description']}*\n"
                            result += "\n"
                    result += "\n"
            
            result += "## Full Content\n"
            result += data['content']
            
            return result

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="search_gtfobins",
                    description="Search GTFOBins database for binaries and techniques",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for binary name or technique"
                            },
                            "function_type": {
                                "type": "string",
                                "description": "Filter by function type (shell, file-upload, file-download, etc.)",
                                "enum": ["shell", "file-upload", "file-download", "file-write", 
                                        "file-read", "library-load", "suid", "sudo", "capabilities"]
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_binary_details",
                    description="Get detailed information about a specific binary",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "binary": {
                                "type": "string",
                                "description": "Name of the binary to get details for"
                            }
                        },
                        "required": ["binary"]
                    }
                ),
                Tool(
                    name="list_binaries_by_function",
                    description="List all binaries that support a specific function",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "function": {
                                "type": "string",
                                "description": "Function type to search for",
                                "enum": ["shell", "file-upload", "file-download", "file-write", 
                                        "file-read", "library-load", "suid", "sudo", "capabilities"]
                            }
                        },
                        "required": ["function"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            if name == "search_gtfobins":
                query = arguments.get("query", "").lower()
                function_type = arguments.get("function_type")
                
                results = []
                for binary_name, data in self.binaries_data.items():
                    # Search in binary name
                    if query in binary_name.lower():
                        match_reason = f"Binary name matches '{query}'"
                        
                        # Check function type filter
                        if function_type and function_type not in data.get('functions', {}):
                            continue
                            
                        functions = list(data.get('functions', {}).keys())
                        results.append({
                            'binary': binary_name,
                            'match_reason': match_reason,
                            'available_functions': functions
                        })
                
                response = f"Found {len(results)} matches for '{query}'"
                if function_type:
                    response += f" with function '{function_type}'"
                response += ":\n\n"
                
                for result in results[:20]:  # Limit to 20 results
                    response += f"**{result['binary']}**\n"
                    response += f"- Match: {result['match_reason']}\n"
                    response += f"- Functions: {', '.join(result['available_functions'])}\n\n"
                
                return [TextContent(type="text", text=response)]
            
            elif name == "get_binary_details":
                binary = arguments.get("binary", "")
                
                if binary not in self.binaries_data:
                    return [TextContent(type="text", text=f"Binary '{binary}' not found in GTFOBins database.")]
                
                data = self.binaries_data[binary]
                response = f"# {binary}\n\n"
                
                if data['functions']:
                    response += "## Available Functions\n"
                    for func_name, func_data in data['functions'].items():
                        response += f"### {func_name.title()}\n"
                        if isinstance(func_data, list):
                            for item in func_data:
                                if isinstance(item, dict) and 'code' in item:
                                    response += f"```bash\n{item['code']}\n```\n"
                                    if 'description' in item:
                                        response += f"*{item['description']}*\n"
                        response += "\n"
                
                return [TextContent(type="text", text=response)]
            
            elif name == "list_binaries_by_function":
                function = arguments.get("function", "")
                
                matching_binaries = []
                for binary_name, data in self.binaries_data.items():
                    if function in data.get('functions', {}):
                        matching_binaries.append(binary_name)
                
                response = f"Binaries supporting '{function}' function ({len(matching_binaries)} found):\n\n"
                for binary in sorted(matching_binaries):
                    response += f"- {binary}\n"
                
                return [TextContent(type="text", text=response)]
            
            else:
                raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main function to run the MCP server"""
    try:
        print("Starting GTFOBins MCP Server...", file=sys.stderr)
        server_instance = GTFOBinsServer()
        server_instance.setup_handlers()
        
        print("Server handlers set up, starting stdio server...", file=sys.stderr)
        
        # Run the server using stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            print("STDIO server started, running MCP server...", file=sys.stderr)
            await server_instance.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="gtfobins-server",
                    server_version="1.0.0",
                    capabilities=server_instance.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    except Exception as e:
        print(f"Error in main: {e}", file=sys.stderr)
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
