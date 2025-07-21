# GTFOBins MCP Server

A Model Context Protocol (MCP) server that provides seamless access to the GTFOBins database through Claude Desktop. Query exploitation techniques, search for specific binaries, and explore privilege escalation methods directly from your Claude conversations.

> **What is GTFOBins?** GTFOBins is a curated list of Unix binaries that can be used to bypass local security restrictions in misconfigured systems. This MCP server brings that knowledge directly into Claude Desktop.

## ✨ Features

- 🔍 **Smart Search**: Find binaries by name, function type, or technique
- 📋 **Function Filtering**: List binaries by specific capabilities (shell, file-upload, SUID, etc.)
- 📖 **Detailed Information**: Get complete exploitation techniques with code examples
- 🐳 **Dockerized**: Clean, isolated deployment with minimal dependencies
- 🍎 **Apple Silicon Optimized**: Native ARM64 support for M1/M2/M3 Macs
- 🚀 **On-Demand**: No persistent containers - runs fresh for each session

## 🎯 Use Cases

- **Security Research**: Quickly lookup exploitation techniques during assessments
- **Red Team Operations**: Find creative ways to abuse legitimate system utilities
- **Blue Team Defense**: Understand what attackers can do with common binaries
- **Educational**: Learn about Unix security and privilege escalation vectors
- **CTF Competitions**: Fast reference for challenge solving

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
# Build the image for Apple Silicon
docker build --platform linux/arm64 -t gtfobins-mcp-server .

# Test the build
docker run --rm --platform linux/arm64 gtfobins-mcp-server python -c "
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
        "--platform",
        "linux/arm64",
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

## 📁 Project Structure

```
gtfobins-mcp-server/
├── Dockerfile              # Container definition with GTFOBins data
├── requirements.txt        # Python dependencies (MCP SDK, PyYAML, etc.)
├── server.py              # Main MCP server implementation
├── docker-compose.yml     # Optional: Alternative deployment method
├── build.sh              # Automated setup script
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
- Ensure you're on Apple Silicon and using the `--platform linux/arm64` flag
- Check Docker has sufficient disk space for the image

**MCP connection issues:**
- Verify the claude_desktop_config.json syntax is valid JSON
- Completely restart Claude Desktop after configuration changes
- Check Claude Desktop logs for specific error messages

### Debug Commands

```bash
# Test Docker image
docker run --rm --platform linux/arm64 gtfobins-mcp-server python --version

# Test GTFOBins data loading
docker run --rm --platform linux/arm64 gtfobins-mcp-server python -c "
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
