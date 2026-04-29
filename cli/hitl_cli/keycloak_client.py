# Backward-compatibility shim — use hitl_cli.oauth_client.OAuthClient in new code.
from .oauth_client import OAuthClient as KeycloakClient  # noqa: F401

__all__ = ["KeycloakClient"]
