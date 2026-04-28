class HitlError(Exception):
    """Base class for HITL errors."""


class HitlDenied(HitlError):
    """User explicitly denied the approval request."""


class HitlTimeout(HitlError):
    """User did not respond within the TTL window."""


class HitlVerificationError(HitlError):
    """Signature verification failed — response cannot be trusted."""


class HitlExtensionUnavailable(HitlError):
    """The browser extension / signing host is not reachable."""
