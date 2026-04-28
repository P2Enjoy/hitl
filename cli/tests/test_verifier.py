import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hitl_cli.challenge import challenge_bytes, generate_challenge
from hitl_cli.models import ChallengeRequest, SignedResponse
from hitl_cli.verifier import _b64url_decode, _parse_jwt_sub, verify_signed_response


def _make_jwt(sub: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"EdDSA"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": sub, "exp": int(time.time()) + 300}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.fakesig"


def _sign_challenge(private_key: Ed25519PrivateKey, challenge: ChallengeRequest) -> str:
    payload = challenge_bytes(challenge)
    sig = private_key.sign(payload)
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _pubkey_b64url(private_key: Ed25519PrivateKey) -> str:
    pub_bytes = private_key.public_key().public_bytes_raw()
    return base64.urlsafe_b64encode(pub_bytes).decode().rstrip("=")


@pytest.fixture
def keypair():
    private_key = Ed25519PrivateKey.generate()
    return private_key


@pytest.mark.asyncio
async def test_verify_valid_signature(keypair) -> None:
    challenge = generate_challenge("test action", "test-tool")
    user_id = "user-abc-123"
    access_token = _make_jwt(user_id)
    signature = _sign_challenge(keypair, challenge)
    pubkey_b64url = _pubkey_b64url(keypair)

    response = SignedResponse(
        signature=signature,
        access_token=access_token,
        user_id=user_id,
        nonce=challenge.nonce,
        timestamp=challenge.timestamp,
    )

    mock_keycloak = AsyncMock()
    mock_keycloak.get_user_pubkey.return_value = pubkey_b64url

    with patch("hitl_cli.verifier._check_nonce", new_callable=AsyncMock):
        result = await verify_signed_response(challenge, response, mock_keycloak)

    assert result is True


@pytest.mark.asyncio
async def test_reject_wrong_signature(keypair) -> None:
    challenge = generate_challenge("action", "tool")
    other_key = Ed25519PrivateKey.generate()
    user_id = "user-xyz"
    access_token = _make_jwt(user_id)
    signature = _sign_challenge(other_key, challenge)  # wrong key
    pubkey_b64url = _pubkey_b64url(keypair)

    response = SignedResponse(
        signature=signature,
        access_token=access_token,
        user_id=user_id,
        nonce=challenge.nonce,
        timestamp=challenge.timestamp,
    )

    mock_keycloak = AsyncMock()
    mock_keycloak.get_user_pubkey.return_value = pubkey_b64url

    with patch("hitl_cli.verifier._check_nonce", new_callable=AsyncMock):
        result = await verify_signed_response(challenge, response, mock_keycloak)

    assert result is False


@pytest.mark.asyncio
async def test_reject_expired_challenge(keypair) -> None:
    challenge = ChallengeRequest(
        nonce="a" * 64,
        timestamp=int(time.time()) - 9999,  # way in the past
        action="old action",
        tool_name="tool",
        version="1",
    )
    user_id = "user-old"
    access_token = _make_jwt(user_id)
    signature = _sign_challenge(keypair, challenge)

    response = SignedResponse(
        signature=signature,
        access_token=access_token,
        user_id=user_id,
        nonce=challenge.nonce,
        timestamp=challenge.timestamp,
    )

    mock_keycloak = AsyncMock()
    mock_keycloak.get_user_pubkey.return_value = _pubkey_b64url(keypair)

    with pytest.raises(ValueError, match="expired"):
        await verify_signed_response(challenge, response, mock_keycloak)


def test_parse_jwt_sub() -> None:
    token = _make_jwt("my-user-id")
    assert _parse_jwt_sub(token) == "my-user-id"
