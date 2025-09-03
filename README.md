# GTFOBins MCP Server

A Model Context Protocol (MCP) server that provides seamless access to the GTFOBins database through Claude Desktop. Query exploitation techniques, search for specific binaries, and explore privilege escalation methods directly from your Claude conversations.

> **What is GTFOBins?** GTFOBins is a curated list of Unix binaries that can be used to bypass local security restrictions in misconfigured systems. This MCP server brings that knowledge directly into Claude Desktop.

## ✨ Features

- 🔍 **Smart Search**: Find binaries by name, function type, or technique
- 📋 **Function Filtering**: List binaries by specific capabilities (shell, file-upload, SUID, etc.)
- 📖 **Detailed Information**: Get complete exploitation techniques with code examples
- 🐳 **Dockerized**: Clean, isolated deployment with minimal dependencies
- 🚀 **On-Demand**: No persistent containers - runs fresh for each session

## 🎯 Use Cases

- **Security Research**: Quickly lookup exploitation techniques during assessments
- **Red Team Operations**: Find creative ways to abuse legitimate system utilities
- **Blue Team Defense**: Understand what attackers can do with common binaries
- **Educational**: Learn about Unix security and privilege escalation vectors
- **CTF Competitions**: Fast reference for challenge solving

### 👩🏻‍🔧 Changes in This Version
- **Architecture-Agnostic Builds**: The `Dockerfile` no longer specifies a platform (e.g., `linux/arm64`), allowing builds on any architecture (x86_64, ARM64, etc.).
- **Multiprocessing**: Added multiprocessing to `server.py` for faster loading of GTFOBins data, with a fallback to sequential processing if needed.
- **Logging**: Added logging to `/app/logs/gtfobins.log` for server events and errors.
- **Error Handling**: Improved application-level error handling in `server.py` for better reliability.
- **Testing**: Added `test_malformed.sh` to run test cases against the server.
- **MCP Inspector**: Added support for debugging with MCP Inspector.

## 🚀 Quick Start

### Prerequisites

- Docker installed and running
- Claude Desktop application
- Apple Silicon Mac (M1/M2/M3) or compatible system

### 1. Setup Project

```bash
# Create project directory
mkdir gtfobins-mcp-server
cd gtfobins-mcp-server

# Copy the following files to this directory:
# - Dockerfile
# - requirements.txt  
# - server.py
```

### 2. Build Docker Image

```bash
# Build the image
docker build -t gtfobins-mcp-server .

# Test the build
docker run --rm gtfobins-mcp-server python -c "
import sys; sys.path.append('/app')
from server import GTFOBinsServer
server = GTFOBinsServer()
print(f'✅ Successfully loaded {len(server.binaries_data)} GTFOBins entries')
"
```

### 3. Configure Claude Desktop

Edit your Claude Desktop configuration file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gtfobins": {
      "command": "docker",
      "args": [
        "run",
	      "--rm",
        "-i",
        "gtfobins-mcp-server",
        "python",
        "/app/server.py"
      ],
      "env": {}
    }
  }
}

```

### 4. Restart Claude Desktop

Completely quit and restart Claude Desktop to load the new MCP server.

## 💬 Usage Examples

Once configured, you can interact with GTFOBins directly through Claude Desktop:

### Search for Binaries
```
"What GTFOBins techniques are available for python?"
"Search for binaries that can create reverse shells"
"Show me wget exploitation methods"
```

### Filter by Function Type
```
"List all binaries that support file upload"
"What binaries can be used for SUID privilege escalation?"
"Show me all shell escape techniques"
```

### Get Detailed Information
```
"Get complete exploitation details for curl"
"Show me the sudo techniques for vim"
"What are all the capabilities-based attacks for systemctl?"
```

## 🐛 Testing and Debugging

### Test Script
The test script `test_malformed.sh` defines a function that allows specific test cases to be sent to the GTFOBins MCP Server via STDIO. The function handles the required initialization of the MCP conversation before sending the test request to the server. These requests and responses are captured and logged to `test_cases.txt` for further analysis. There are currently **31** test cases that cover general tool validation, resource validation, invalid tool parameters, and more!

### Debugging with MCP Inspector
The MCP Inspector is an interactive developer tool, and is the fastest way to test and debug any MCP server. To debug the GTFOBins MCP Server using MCP Inspector, follow these steps outlined below:

#### 1. Install Node.js
```bash
# Begin by checking if you have Node.js installed
node -v # If you see a version number, you have it

# If not, install Node.js using Homebrew
brew install node
```

#### 2. Ensure the Docker Image is Built
```bash
docker inspect gtfobins-mcp-server

# If no image is available, build it:
docker build -t gtfobins-mcp-server .
```

#### 3. Run MCP Inspector
```bash
# The Inspector runs directly through npx
npx @modelcontextprotocol/inspector "/usr/local/bin/docker" run -i --quiet gtfobins-mcp-server
```

From here, a session token will be generated and the MCP Inspector will launch in your browser. Once you connect to the server, you will be able to start interacting with the interface and perform operations such as view avaiable tools, list resources, make specific tool calls, etc. You can see the different requests/responses in the **History** section of the interface. View the `gtfobins.log` file for specific events such as application-level error handling, errors encountered when loading GTFOBins data, server startup errors, etc. 


### Utilizing Logs
Logs are written to /app/logs/gtfobins.log, and can be accessed through `docker exec.` If you wish to access these logs locally, you can mount a local `logs` directory as a volume when running the container:

```bash
mkdir -p logs
docker run -it --rm -v $(pwd)/logs:/app/logs gtfobins-server

```

## 🛠 Available Tools

The MCP server provides three main tools:

### 1. `search_gtfobins`
Search the database by binary name or technique keywords.

**Parameters:**
- `query` (required): Search term
- `function_type` (optional): Filter by function type

**Example**: Search for "python" binaries with "shell" function

### 2. `get_binary_details`
Get complete exploitation information for a specific binary.

**Parameters:**
- `binary` (required): Name of the binary

**Example**: Get all techniques available for "wget"

### 3. `list_binaries_by_function`
List all binaries that support a specific function type.

**Parameters:**
- `function` (required): One of: shell, file-upload, file-download, file-write, file-read, library-load, suid, sudo, capabilities

**Example**: List all binaries with SUID exploitation techniques

A fourth tool has been added to collect an display specific testing related metrics for the MCP Server:

### 4. `get_server_status`
Get server status and performance metrics such as CPU percentage, number of requests handled, etc. 

## 📁 Project Structure

```
gtfobins-mcp-server/
├── Dockerfile              # Container definition with GTFOBins data
├── requirements.txt        # Python dependencies (MCP SDK, PyYAML, etc.)
├── server.py              # Main MCP server implementation
├── docker-compose.yml     # Optional: Alternative deployment method
├── build.sh              # Automated setup script
├── test_malformed.sh     # Automated test script to send malformed and valid requests to MCP Server
├── test_cases.txt        # Output of test cases
└── README.md             # This documentation
```

## 🔧 Architecture

The MCP server works by:

1. **Data Loading**: Clones the GTFOBins repository during Docker build
2. **Parsing**: Processes all markdown files with YAML frontmatter
3. **Indexing**: Creates searchable data structures in memory
4. **MCP Interface**: Exposes search/query capabilities through MCP tools
5. **On-Demand Execution**: Runs fresh containers for each Claude Desktop session

## 🐛 Troubleshooting

### Common Issues

**"No such container" error:**
- The new configuration uses `docker run` instead of `docker exec`
- No persistent container needed - each session runs fresh

**"Container not running" error:**
- Ensure you're using the updated Claude Desktop configuration
- Check that Docker is running: `docker ps`

**Build failures:**
- Although the `--platform linux/arm64` flag has been removed, you can check the Docker logs or inspect the Docker image to ensure the architecture used to build is as expected
- Check Docker has sufficient disk space for the image

**MCP connection issues:**
- Verify the claude_desktop_config.json syntax is valid JSON
- Completely restart Claude Desktop after configuration changes
- Check Claude Desktop logs for specific error messages

### Debug Commands

```bash
# Test Docker image
docker run --rm gtfobins-mcp-server python --version

# Test GTFOBins data loading
docker run --rm gtfobins-mcp-server python -c "
import sys; sys.path.append('/app')
from server import GTFOBinsServer
server = GTFOBinsServer()
print(f'Loaded: {len(server.binaries_data)} binaries')
print('Sample binaries:', list(server.binaries_data.keys())[:5])
"

# Check configuration file
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
```

### Getting Help

If you encounter issues:

1. Check the Claude Desktop logs for specific error messages
2. Verify all files are correctly placed in the project directory
3. Ensure Docker is running and has sufficient resources
4. Test the Docker image independently before connecting to Claude

## 🔒 Security Considerations

**Important Security Notes:**

- This server provides **read-only access** to GTFOBins data
- GTFOBins contains legitimate system administration techniques that **could be misused**
- **Use responsibly** and in accordance with your organization's security policies
- Intended for **authorized security testing** and **educational purposes only**
- The Docker container runs with **minimal privileges** and **no network access** by default

**Best Practices:**
- Only use in authorized testing environments
- Understand your organization's security policies before deployment
- Keep the Docker image updated with latest GTFOBins data
- Monitor usage for compliance with security guidelines

## 📄 License & Attribution

This project is for educational and legitimate security research purposes.

- **GTFOBins Data**: Subject to its own license terms at [GTFOBins.github.io](https://gtfobins.github.io)
- **MCP Server Code**: Educational use - please respect responsible disclosure practices
- **Docker Configuration**: Freely usable for legitimate security research

## 🤝 Contributing

Improvements welcome! Areas for contribution:

- Additional search capabilities
- Better error handling and logging
- Performance optimizations
- Extended filtering options
- Integration with other security tools

## 📚 Learn More

- **GTFOBins**: [https://gtfobins.github.io](https://gtfobins.github.io)
- **Model Context Protocol**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Claude Desktop**: [https://claude.ai/desktop](https://claude.ai/desktop)
- **Docker**: [https://docs.docker.com](https://docs.docker.com)

---

**⚡ Ready to explore? Ask Claude: "What GTFOBins techniques are available for your favorite Unix utility?"**
