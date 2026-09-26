"""The desktop actions as an MCP server, for the Claude Code provider.

Claude Code (signed in with a Claude Pro or Max plan) runs this over stdio
and may call only these tools: the same allowlisted, schema-checked actions
as every other provider. It is a minimal JSON-RPC 2.0 loop, one message per
line, with the few methods a tools-only server needs.

    python -m halcyon_assistant.mcp_server
"""

import json
import sys

from . import actions

PROTOCOL_VERSION = "2025-06-18"


def tools_list():
    return [{"name": name, "description": spec["description"], "inputSchema": spec["parameters"]}
            for name, spec in actions.ACTIONS.items()]


def handle(message, run=actions.run):
    """One request -> one response dict, or None for notifications."""
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None  # notifications (initialized, cancelled...) need no answer

    def result(value):
        return {"jsonrpc": "2.0", "id": request_id, "result": value}

    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        return result({"protocolVersion": requested, "capabilities": {"tools": {}},
                       "serverInfo": {"name": "halcyon", "version": "1.0"}})
    if method == "ping":
        return result({})
    if method == "tools/list":
        return result({"tools": tools_list()})
    if method == "tools/call":
        params = message.get("params") or {}
        outcome = run(params.get("name", ""), params.get("arguments") or {})
        return result({"content": [{"type": "text", "text": outcome}], "isError": outcome.startswith("error")})
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"unknown method {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
