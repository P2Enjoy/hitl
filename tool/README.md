# tool/ — Pattern 1: HITL-enabled Tool

**Use this pattern when**: you own the tool's Python code and want the tool itself to be the approval gate — so it can never run without a human signature, regardless of which agent calls it or how it's invoked.

The check is inside the function, not outside it. This means approval travels with the tool wherever it's deployed: called by an agent, invoked from a script, or used in a pipeline.

For other HITL integration patterns see the [root README](../README.md).

## Usage

```python
from hitl_tool.decorator import require_human_approval
from hitl_tool.exceptions import HitlDenied, HitlTimeout, HitlVerificationError

@require_human_approval("Delete file: {kwargs[path]}")
async def delete_file(path: str) -> bool:
    os.remove(path)
    return True

# Calling the tool triggers the HITL flow:
try:
    await delete_file(path="/tmp/important.txt")
except HitlDenied:
    print("User denied the request")
except HitlVerificationError:
    print("Signature verification failed")
```

## Action Template Variables

| Variable | Value |
|----------|-------|
| `{func_name}` | Function name |
| `{args_preview}` | Truncated positional args |
| `{kwargs}` | Truncated kwargs dict |
| `{kwargs[key]}` | Specific kwarg value |

## Demo

```bash
python -m hitl_tool.demo_tool
```

Runs three operations (file deletion, shell command, simulated email), each requiring approval in the browser extension popup.

## Exceptions

| Exception | When raised |
|-----------|------------|
| `HitlDenied` | User clicked Deny |
| `HitlTimeout` | User didn't respond within TTL |
| `HitlVerificationError` | Signature verification failed |
| `HitlExtensionUnavailable` | Signing host not reachable |
