"""
hitl_cli — cryptographically signed human-in-the-loop permission system.

Public API for use by tool/, skill/, and mcp/ packages:
    from hitl_cli.challenge import generate_challenge, challenge_bytes, request_signature
    from hitl_cli.verifier import verify_signed_response
    from hitl_cli.keycloak_client import KeycloakClient
    from hitl_cli.models import ChallengeRequest, SignedResponse
"""
