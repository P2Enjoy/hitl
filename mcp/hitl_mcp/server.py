import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from .tools import check_hitl_availability, request_approval

load_dotenv()

mcp = FastMCP(
    name="hitl-verification",
    instructions=(
        "HITL (Human-in-the-Loop) verification server. "
        "Use request_approval() before any sensitive or irreversible action to get "
        "cryptographically verified human consent. "
        "Use check_hitl_availability() to verify the signing extension is running "
        "before starting a workflow that requires approvals."
    ),
)

mcp.tool()(request_approval)
mcp.tool()(check_hitl_availability)


def main() -> None:
    port = int(os.getenv("MCP_SERVER_PORT", "8008"))
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
