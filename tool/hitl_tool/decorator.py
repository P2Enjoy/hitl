import functools
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from .hitl_check import perform_hitl_check

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def require_human_approval(
    action_template: str = "{func_name}({args_preview})",
) -> Callable[[F], F]:
    """
    Decorator that gates an async tool function behind a cryptographic HITL check.

    The action_template supports:
        {func_name}     — the wrapped function's name
        {args_preview}  — truncated positional args string
        {kwargs}        — truncated kwargs string
        {kwargs[key]}   — specific kwarg value

    Raises:
        HitlDenied            — user denied
        HitlTimeout           — user did not respond
        HitlVerificationError — signature invalid
        HitlExtensionUnavailable — signing host not reachable
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                action = action_template.format(
                    func_name=func.__name__,
                    args_preview=str(args)[:80],
                    kwargs=str(kwargs)[:80],
                    **{f"kwargs[{k}]": v for k, v in kwargs.items()},
                )
            except (KeyError, IndexError):
                action = f"{func.__name__}({str(args)[:40]}, {str(kwargs)[:40]})"

            module = func.__module__ or "unknown"
            await perform_hitl_check(action, tool_name=module)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
