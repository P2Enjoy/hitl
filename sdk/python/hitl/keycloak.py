# Backward-compatibility shim — use hitl.oauth.OAuthClient in new code.
from .oauth import OAuthClient as KeycloakClient  # noqa: F401

__all__ = ["KeycloakClient"]
