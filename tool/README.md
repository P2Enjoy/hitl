# tool/ — @require_human_approval Decorator

Demonstrates how any Python tool integrates HITL verification with a single decorator.

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
