# stdio_main.py
# Stdio entry point for local MCP clients (Kiro, Claude Desktop, etc.) that
# launch the server themselves via "command"/"args" in their MCP config.
# The HTTP transport in main.py is unchanged; this just exposes the same
# tools/resources/prompts over stdin/stdout.
#
# Note: logging in mcp_server.py goes to stderr, so it does not corrupt the
# JSON-RPC stream on stdout.
from mcp_server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
