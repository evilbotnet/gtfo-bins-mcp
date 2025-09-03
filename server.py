#!/usr/bin/env python3
"""
GTFOBins MCP Server
A simple MCP server that provides access to GTFOBins data

Logging added and handling of application level errors... these errors occur within tool implementations and may 
include things such as business logic failures, external API errors, or resource constraints. These are errors that
the MCP library didn't catch during protocol-level validation. In order to allow the  LLM to understand and potentially
recover from the failure, these errors must throw the isError flag set to true.

"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import asyncio
import logging
import sys
import datetime
from multiprocessing import Pool
import psutil
import traceback

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import AnyUrl, ValidationError
import mcp.server.stdio
from mcp.shared.exceptions import McpError, ErrorData

# Set up logging
log_file = '/app/logs/gtfobins.log'
open(log_file, 'w').close() #truncate the log file to zero length

logging.basicConfig(
    filename=log_file,
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    force = True
)
logger = logging.getLogger(__name__)

# Also log to stderr for immediate feedback
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class GTFOBinsServer:
    def __init__(self):
        self.start_time = datetime.datetime.now()

        logger.info("="*50)
        logger.info("Initializing GTFOBinsServer")
        logger.info(f"Start time: {self.start_time}")
        logger.info("="*50)

        self.server = Server("gtfobins-server")
        self.gtfobins_path = Path("/app/gtfobins-data")
        self.binaries_data = {}
        # Counts used for insights
        self.error_count = 0 # Only for application-level errors
        self.request_count = 0
        #self.validation_errors = 0 -- add in later when working with middleware

        try:
            self.load_gtfobins_data()
        except Exception as e:
            logger.error(f"Failed to load GTFOBins data: {e}")
            # Continue running even if data loading fails
            self.binaries_data = {}

    def parse_md_file(self, md_file: Path) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse a single Markdown file (used for multiprocessing)"""
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
                            
                        return binary_name, {
                            'metadata': metadata,
                            'content': markdown_content,
                            'functions': metadata.get('functions', {}) if metadata else {}
                        }
                    except yaml.YAMLError as e:
                        logger.warning(f"Error parsing YAML in {md_file}: {e}")
                        return None, None
            return None, None
        except Exception as e:
            logger.error(f"Error loading {md_file}: {e}")
            return None, None

    def load_gtfobins_data(self):
        """Load GTFOBins data from the cloned repository"""
        
        logger.info("Starting load_gtfobins_data")

        binaries_dir = self.gtfobins_path / "_gtfobins"
        
        if not binaries_dir.exists():
            logger.error(f"GTFOBins directory not found: {binaries_dir}")
            raise McpError(error=ErrorData(code=-32000, message=f"Server error: GTFOBins directory not found: {binaries_dir}"))
        
        self.binaries_data = {}
        md_files = list(binaries_dir.glob("*md"))   
        logger.info(f"Found {len(md_files)} Markdown files")

        if not md_files:
            logger.warning("No markdown files found in GTFOBins directory")
            return
        
        try:
            # Use multiprocessing to parallelize parsing
            with Pool(processes=4) as pool:  # 4 processes for quad-core i5
                results = pool.map(self.parse_md_file, md_files)

            for binary_name, data in results:
                if binary_name and data:
                    self.binaries_data[binary_name] = data
                    
            logger.info(f"Loaded {len(self.binaries_data)} GTFOBins entries")
        except Exception as e:
            logger.warning(f"Multiprocessing failed, falling back to sequential: {e}")
            self.error_count += 1
            # Fallback to sequential processing
            for md_file in md_files:
                try:
                    binary_name, data = self.parse_md_file(md_file)
                    if binary_name and data:
                        self.binaries_data[binary_name] = data
                except Exception as file_error:
                    logger.error(f"Error processing {md_file}: {file_error}")
                    self.error_count += 1
                    continue
            
            logger.info(f"Loaded {len(self.binaries_data)} GTFOBins entries (sequential)")

    # Application-Level Validation - empty required parameters

    # The MCP Library handles...
    # - protocol level validation (malformed JSON RPC)
    # - checking the tool call against its schema

    # Found edge case for  where the library doesn't verify that the required parameter is a non-empty string
    # for functions search_gtfobins and get_binary_details

    def validate_empty_params(self, required: str, arguments: Dict[str, Any]) -> None:
        """
        Validate that tools aren't recieving empty strings for required parameters - raises McpError if invalid
        The MCP Library doesn't provide this validation when checking tool schema
        """
        logger.info(f"Validating edge case: Ensure {required} didn't recieve empty string")
        try:
            req = arguments[required]
            if not req.strip():
                #self.validation_errors += 1
                raise McpError(error=ErrorData(
                    code=-32602,
                    message=f"Invalid parameter: {required} must be a non-empty string"
                ))
                
            logger.info(f"Validation passed for edge case!")

        except McpError as e:
            logger.warning(f"Validation failed: Required parameter {required} recieved empty string as input")
            self.error_count += 1
            raise

    def setup_handlers(self):
        """Set up MCP server handlers"""
        logger.info("Setting up handlers")
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available GTFOBins resources"""
            try:
                logger.info("Handling list_resources")
                self.request_count += 1
                if not self.binaries_data:
                    logger.error("No binaries data loaded")
                    raise McpError(error=ErrorData(code=-32000, message="Server error: No binaries loaded"))
                resources = []
                for binary_name in self.binaries_data.keys():
                    try:
                        resources.append(Resource(
                            uri=AnyUrl(f"gtfobins://{binary_name}"),
                            name=f"GTFOBins: {binary_name}",
                            description=f"GTFOBins entry for {binary_name}",
                            mimeType="text/plain"
                        ))
                    except ValidationError as e: #expected to be thrown by pydantic if error occurs when parsing or validation
                        logger.error(f"Validation error for binary {binary_name}: {e}")
                        self.error_count += 1
                        continue
                    except Exception as e:
                        logger.error(f"Error creating resource for {binary_name}: {e}")
                        self.error_count += 1
                        continue

                logger.info(f"Returning {len(resources)} resources")
                return resources
            except McpError:
                self.error_count += 1
                raise
            except Exception as e:
                logger.error(f"Unexpected error in list_resources: {e}")
                self.error_count += 1
                raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

        @self.server.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str:
            """Read a specific GTFOBins resource"""
            try:
                logger.info(f"Handling read_resource: {uri}")
                self.request_count += 1
                if not str(uri).startswith("gtfobins://"):
                    logger.warning(f"Invalid URI scheme: {uri}")
                    raise McpError(error=ErrorData(code=-32602, message=f"Invalid parameters: Unsupported URI scheme: {uri}"))
                    
                binary_name = str(uri).replace("gtfobins://", "")

                if not binary_name:
                    logger.warning("Empty binary name in URI")
                    raise McpError(error=ErrorData(code=-32602, message="Invalid parameters: Binary name cannot be empty"))
                
                if binary_name not in self.binaries_data:
                    logger.warning(f"Binary not found: {binary_name}")
                    raise McpError(error=ErrorData(code=-32001, message=f"Resource not found in GTFOBins: Binary {binary_name}")) #server specific error
                    
                data = self.binaries_data[binary_name]
                
                # Format the response
                result = f"# {binary_name}\n\n"
                
                try:
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
                
                except Exception as format_error:
                    logger.error(f"Error formatting response for {binary_name}: {format_error}")
                    self.error_count += 1
                    result = f"# {binary_name}\n\nError formatting response: {str(format_error)}"
                
                logger.info(f"Successfully read resource: {binary_name}")
                return result
            except McpError as e:
                if e.error.code == -32001: #application-level error (binary not found)
                    self.error_count += 1
                raise #Re-raise MCP errors - so library can handle the error response formatting
            except Exception as e:
                logger.error(f"Unexpected error in read_resource: {e}")
                self.error_count += 1
                raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            try:
                logger.info("Handling list_tools")
                self.request_count += 1
            
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
                    ),
                    Tool(
                        name="get_server_status",
                        description="Get server status and performance metrics",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    )
                ]
            except Exception as e:
                logger.error(f"Unexpected error in list_tools: {e}")
                self.error_count += 1
                raise McpError(-32000, f"Server error: {str(e)}")

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            logger.info(f"Tool call: {name} with arguments: {arguments}")
            self.request_count += 1
            start_time = datetime.datetime.now()
            
            try:
                # Validate tool name isn't left empty
                if not name.strip():
                    #self.validation_errors += 1
                    logger.warning(f"Validation failed: Tool name is empty")
                    raise McpError(error=ErrorData(code=-32602, message="Invalid parameters: Tool name must be a non-empty string"))
                
                # Route to specific tool handlers
                if name == "search_gtfobins":
                    self.validate_empty_params('query', arguments)
                    result = await self._handle_search_gtfobins(arguments)
                
                elif name == "get_binary_details":
                    self.validate_empty_params('binary', arguments)
                    result = await self._handle_get_binary_details(arguments)
                
                elif name == "list_binaries_by_function":
                    #MCP library sufficiently handles parameter validation - don't worry about empty edge case
                    result = await self._handle_list_binaries_by_function(arguments)

                elif name == "get_server_status":
                    #no params to validate
                    result = await self._handle_get_server_status(arguments)
                
                else:
                    logger.error(f"Unknown tool: {name}")
                    raise McpError(error=ErrorData(code=-32601, message=f"Method not found: Unknown tool: {name}"))
                
                duration = datetime.datetime.now() - start_time
                logger.info(f"Tool call completed: {name} in {duration.total_seconds():.3f}s")
                return result  
            
            except McpError as e:
                duration = datetime.datetime.now() - start_time
                logger.error(f"Tool call failed for '{name}' - {e.error.message} (duration: {duration.total_seconds():.3f}s)")
                raise  # Re-raise to return MCP error to client
            except Exception as e:
                duration = datetime.datetime.now() - start_time
                logger.error(f"Tool call crashed: {name} - {str(e)} (duration: {duration.total_seconds():.3f}s)")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.error_count += 1
                raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))
            
    async def _handle_search_gtfobins(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """handle tool call for search_gtfobins"""
        try:
            query = arguments.get("query", "").lower()
            function_type = arguments.get("function_type")

            logger.info(f"Starting search for query='{query}', function_type={function_type}")
            logger.info(f"Available binaries: {len(self.binaries_data)}")
                
            if not self.binaries_data:
                logger.warning("No GTFOBins data loaded")
                #return [TextContent(type="text", text="No GTFOBins data loaded")]
                raise McpError(error=ErrorData(code=-32000, message="Server error: No GTFOBins data loaded"))
            
            results = []
            processed_count = 0
            for binary_name, data in self.binaries_data.items():
                processed_count +=1
                try:
                    # Search in binary name
                    if query in binary_name.lower():
                        match_reason = f"Binary name matches '{query}'"
                        
                        # Check function type filter
                        if function_type and function_type not in data.get('functions', {}):
                            logger.debug(f"Binary {binary_name} matches query but not function_type filter")
                            continue
                            
                        functions = list(data.get('functions', {}).keys())
                        results.append({
                            'binary': binary_name,
                            'match_reason': match_reason,
                            'available_functions': functions
                        })
                        logger.debug(f"Added match: {binary_name}")

                except Exception as e:
                    logger.error(f"Error processing binary {binary_name} in search: {e}")
                    continue
            
            logger.info(f"Search completed: processed {processed_count} binaries, found {len(results)} matches")
            if len(results) == 0:
                raise McpError(error=ErrorData(code=-32004, message=f"Resource not found: Search query '{query}' for binary name or technique returned no results"))
            
            response = f"Found {len(results)} matches for '{query}'"
            if function_type:
                response += f" with function '{function_type}'"
            response += ":\n\n"
            
            for result in results[:20]:  # Limit to 20 results
                response += f"**{result['binary']}**\n"
                response += f"- Match: {result['match_reason']}\n"
                response += f"- Functions: {', '.join(result['available_functions'])}\n\n"
            
            logger.info(f"Returning search_gtfobins results: {len(results)} matches")
            return [TextContent(type="text", text=response)]
        except McpError as e:
            self.error_count += 1
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search_gtfobins: {e}")
            self.error_count += 1
            raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

    async def _handle_get_binary_details(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """tool call for get_binary_details"""
        try:
            binary = arguments.get("binary", "")
            
            if not self.binaries_data:
                raise McpError(error=ErrorData(code=-32000, message="Server error: No GTFOBins data loaded"))

            if binary not in self.binaries_data:
                raise McpError(error=ErrorData(code=-32004, message=f"Resource not found: Binary '{binary}' not found in GTFOBins database"))
            
            data = self.binaries_data[binary]
            response = f"# {binary}\n\n"
            
            try:
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
            except Exception as e:
                logger.error(f"Error formatting binary details for {binary}: {e}")
                response += f"Error formatting details: {str(e)}\n"
            
            logger.info(f"Returning get_binary_details for {binary}")
            return [TextContent(type="text", text=response)]
        
        except McpError as e:
            self.error_count += 1
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_binary_details: {e}")
            self.error_count += 1
            raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

    async def _handle_list_binaries_by_function(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """tool call for list_binaries_by_function"""
        function = arguments.get("function", "")
        try:
            
            if not self.binaries_data:
                #return [TextContent(type="text", text="No GTFOBins data loaded")]
                logger.warning("No GTFOBins data loaded")
                raise McpError(error=ErrorData(code=-32000, message="Server error: No GTFOBins data loaded"))

            matching_binaries = []
            for binary_name, data in self.binaries_data.items():
                    if function in data.get('functions', {}):
                        matching_binaries.append(binary_name)
            
            response = f"Binaries supporting '{function}' function ({len(matching_binaries)} found):\n\n"
            for binary in sorted(matching_binaries):
                response += f"- {binary}\n"
            
            logger.info(f"Returning list_binaries_by_function: {len(matching_binaries)} matches")
            return [TextContent(type="text", text=response)]
        
        except McpError as e:
            self.error_count += 1
            raise

        except Exception as e:
            logger.error(f"Unexpected error in list_binaries_by_function: {e}")
            self.error_count += 1
            raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

    async def _handle_get_server_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """tool call for get_server_status"""
        try:
            uptime = datetime.datetime.now() - self.start_time
            process = psutil.Process()
            mem_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=0.1)
            response = (
                f"Server Status:\n"
                f"- Uptime: {uptime}\n"
                f"- Memory: {mem_info.rss / 1024 / 1024:.2f} MB\n"
                f"- CPU: {cpu_percent:.1f}%\n"
                f"- Requests Handled: {self.request_count}\n"
                f"- Errors Encountered (Application-Level): {self.error_count}\n"
                #f"- Validation Errors: {self.validation_errors}\n"
                #f"- Error Rate: {(self.error_count / max(1, self.request_count) * 100):.1f}%\n"
                f"- Binaries Loaded: {len(self.binaries_data)}\n"
            )
            logger.info("Server status retrieved successfully")
            return [TextContent(type="text", text=response)]
        
        except Exception as e:
            logger.error(f"Unexpected error in get_server_status: {e}")
            self.error_count += 1
            raise McpError(error=ErrorData(code=-32000, message=f"Server error: {str(e)}"))

        
async def main():
    """Main function to run the MCP server"""
    try:
        logger.info("Starting GTFOBins MCP Server...")
        server_instance = GTFOBinsServer()
        
        server_instance.setup_handlers()
        
        logger.info("Server handlers set up, starting stdio server...")
        
        # Run the server using stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("STDIO server started, running MCP server...")
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
            logger.info("MCP server running")
    except Exception as e:
        logger.error(f"Server startup error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise McpError(error=ErrorData(code=-32000, message=f"Server startup error: {str(e)}"))

if __name__ == "__main__":
    asyncio.run(main())