class HitlError(Exception):
    """Base exception for all HITL errors."""


class HitlDenied(HitlError):
    """The human explicitly denied the approval request."""


class HitlTimeout(HitlError):
    """The human did not respond within the TTL window."""


class HitlVerificationError(HitlError):
    """Signature verification failed — the response cannot be trusted."""


class HitlExtensionUnavailable(HitlError):
    """The browser extension / native messaging host is not reachable."""
