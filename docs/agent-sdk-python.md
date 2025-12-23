# Claude Agent SDK for Python - Complete Documentation

## Overview

The Claude Agent SDK for Python is a Python SDK for Claude Agent that enables programmatic interaction with Claude Code. It allows you to query Claude Code, use tools, create custom tools, and implement hooks for automated feedback and deterministic processing.

**Repository:** `anthropics/claude-agent-sdk-python`
**License:** MIT
**Stars:** 3.6k | **Forks:** 484

---

## Installation

```bash
pip install claude-agent-sdk
```

**Prerequisites:**
- Python 3.10+

**Note:** The Claude Code CLI is automatically bundled with the package. No separate installation is required. The SDK uses the bundled CLI by default.

Optional configurations:
```python
# Install Claude Code separately
# curl -fsSL https://claude.ai/install.sh | bash

# Specify a custom CLI path
options = ClaudeAgentOptions(cli_path="/path/to/claude")
```

---

## Quick Start

```python
import anyio
from claude_agent_sdk import query

async def main():
    async for message in query(prompt="What is 2 + 2?"):
        print(message)

anyio.run(main)
```

---

## Core Features & Usage

### 1. Basic Usage: query()

`query()` is an async function that returns an `AsyncIterator` of response messages.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

# Simple query
async for message in query(prompt="Hello Claude"):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)

# With options
options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1
)

async for message in query(prompt="Tell me a joke", options=options):
    print(message)
```

### 2. Using Tools

Enable Claude to use built-in tools:

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode='acceptEdits'  # auto-accept file edits
)

async for message in query(
    prompt="Create a hello.py file",
    options=options
):
    # Process tool use and results
    pass
```

### 3. Working Directory

Specify the working directory for tool execution:

```python
from pathlib import Path

options = ClaudeAgentOptions(
    cwd="/path/to/project"  # or Path("/path/to/project")
)
```

---

## ClaudeSDKClient - Advanced Usage

`ClaudeSDKClient` supports bidirectional, interactive conversations with Claude Code. It enables **custom tools** and **hooks**, both defined as Python functions.

### Custom Tools (In-Process SDK MCP Servers)

Custom tools are Python functions offered to Claude for invocation as needed. They run as in-process MCP servers, eliminating the need for separate subprocesses.

#### Creating a Simple Tool

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

# Define a tool using the @tool decorator
@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {
        "content": [
            {"type": "text", "text": f"Hello, {args['name']}!"}
        ]
    }

# Create an SDK MCP server
server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

# Use it with Claude
options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")

    # Extract and print response
    async for msg in client.receive_response():
        print(msg)
```

#### Benefits Over External MCP Servers

- **No subprocess management** - Runs in the same process as your application
- **Better performance** - No IPC overhead for tool calls
- **Simpler deployment** - Single Python process instead of multiple
- **Easier debugging** - All code runs in the same process
- **Type safety** - Direct Python function calls with type hints

#### Migration from External Servers

```python
# BEFORE: External MCP server (separate process)
options = ClaudeAgentOptions(
    mcp_servers={
        "calculator": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "calculator_server"]
        }
    }
)

# AFTER: SDK MCP server (in-process)
from my_tools import add, subtract

calculator = create_sdk_mcp_server(
    name="calculator",
    tools=[add, subtract]
)

options = ClaudeAgentOptions(
    mcp_servers={"calculator": calculator}
)
```

#### Mixed Server Support

You can use both SDK and external MCP servers together:

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "internal": sdk_server,  # In-process SDK server
        "external": {  # External subprocess server
            "type": "stdio",
            "command": "external-server"
        }
    }
)
```

### Hooks

A **hook** is a Python function that the Claude Code application (not Claude) invokes at specific points of the Claude agent loop. Hooks provide deterministic processing and automated feedback for Claude.

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def check_bash_command(input_data, tool_use_id, context):
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]
    if tool_name != "Bash":
        return {}
    command = tool_input.get("command", "")
    block_patterns = ["foo.sh"]
    for pattern in block_patterns:
        if pattern in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Command contains invalid pattern: {pattern}",
                }
            }
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command]),
        ],
    }
)

async with ClaudeSDKClient(options=options) as client:
    # Test 1: Command with forbidden pattern (will be blocked)
    await client.query("Run the bash command: ./foo.sh --help")
    async for msg in client.receive_response():
        print(msg)

    print("\n" + "=" * 50 + "\n")

    # Test 2: Safe command that should work
    await client.query("Run the bash command: echo 'Hello from hooks example!'")
    async for msg in client.receive_response():
        print(msg)
```

---

## Type System

See `src/claude_agent_sdk/types.py` for complete type definitions:

- `ClaudeAgentOptions` - Configuration options
- `AssistantMessage`, `UserMessage`, `SystemMessage`, `ResultMessage` - Message types
- `TextBlock`, `ToolUseBlock`, `ToolResultBlock` - Content blocks

---

## Error Handling

```python
from claude_agent_sdk import (
    ClaudeSDKError,           # Base error
    CLINotFoundError,         # Claude Code not installed
    CLIConnectionError,       # Connection issues
    ProcessError,             # Process failed
    CLIJSONDecodeError,       # JSON parsing issues
)

try:
    async for message in query(prompt="Hello"):
        pass
except CLINotFoundError:
    print("Please install Claude Code")
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")
```

---

## Available Tools

See the [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code/settings#tools-available-to-claude) for a complete list of available tools.

---

## Examples

- **Quick Start:** `examples/quick_start.py`
- **Streaming Mode:** `examples/streaming_mode.py`
- **IPython Interactive:** `examples/streaming_mode_ipython.py`
- **MCP Calculator:** `examples/mcp_calculator.py`
- **Hooks:** `examples/hooks.py`

---

## Migrating from Claude Code SDK

If upgrading from versions < 0.1.0:

- `ClaudeCodeOptions` → `ClaudeAgentOptions` (renamed)
- Merged system prompt configuration
- Settings isolation and explicit control
- New programmatic subagents and session forking features

See `CHANGELOG.md` for details.

---

## Development

### Initial Setup

```bash
./scripts/initial-setup.sh
```

This installs a pre-push hook that runs lint checks before pushing. To skip temporarily:
```bash
git push --no-verify
```

### Building Wheels Locally

```bash
# Install build dependencies
pip install build twine

# Build wheel with bundled CLI
python scripts/build_wheel.py

# Build with specific version
python scripts/build_wheel.py --version 0.1.4

# Build with specific CLI version
python scripts/build_wheel.py --cli-version 2.0.0

# Clean bundled CLI after building
python scripts/build_wheel.py --clean

# Skip CLI download (use existing)
python scripts/build_wheel.py --skip-download
```

### Release Workflow

To create a new release:

1. **Trigger the workflow** manually from the Actions tab with:
   - `version`: Package version (e.g., `0.1.5`)
   - `claude_code_version`: Claude Code CLI version (e.g., `2.0.0` or `latest`)

2. **The workflow will:**
   - Build platform-specific wheels for macOS, Linux, and Windows
   - Bundle the specified Claude Code CLI version
   - Build a source distribution
   - Publish all artifacts to PyPI
   - Create a release branch with version updates
   - Open a PR with updated files (version, CLI version, CHANGELOG)

3. **Review and merge** the release PR to update main

---

## License and Terms

Use of this SDK is governed by Anthropic's [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms), including when powering products and services made available to customers and end users, except where specific components are covered by different licenses as indicated in their LICENSE files.
