import json

import pytest

from hitl_cli.challenge import challenge_bytes, generate_challenge
from hitl_cli.models import ChallengeRequest


def test_generate_challenge_fields() -> None:
    c = generate_challenge("delete file", "hitl-cli")
    assert len(c.nonce) == 64
    assert all(ch in "0123456789abcdef" for ch in c.nonce)
    assert c.action == "delete file"
    assert c.tool_name == "hitl-cli"
    assert c.version == "1"
    assert c.timestamp > 0


def test_generate_challenge_unique_nonces() -> None:
    a = generate_challenge("action", "tool")
    b = generate_challenge("action", "tool")
    assert a.nonce != b.nonce


def test_challenge_bytes_canonical() -> None:
    c = ChallengeRequest(
        nonce="a" * 64,
        timestamp=1700000000,
        action="delete file",
        tool_name="hitl-cli",
        version="1",
    )
    b = challenge_bytes(c)
    decoded = json.loads(b.decode("utf-8"))
    # Must have exactly these keys
    assert set(decoded.keys()) == {"action", "nonce", "timestamp", "tool_name", "version"}


def test_challenge_bytes_sorted_keys() -> None:
    c = ChallengeRequest(
        nonce="b" * 64,
        timestamp=12345,
        action="test",
        tool_name="tool",
        version="1",
    )
    raw = challenge_bytes(c).decode("utf-8")
    # Keys should appear in alphabetical order
    keys_in_order = ["action", "nonce", "timestamp", "tool_name", "version"]
    positions = [raw.index(f'"{k}"') for k in keys_in_order]
    assert positions == sorted(positions), "Keys are not in sorted order"


def test_challenge_bytes_no_whitespace() -> None:
    c = ChallengeRequest(
        nonce="c" * 64,
        timestamp=99999,
        action="a",
        tool_name="t",
        version="1",
    )
    raw = challenge_bytes(c).decode("utf-8")
    assert " " not in raw
    assert "\n" not in raw
    assert "\t" not in raw


def test_challenge_bytes_matches_typescript_expected() -> None:
    # Golden value computed independently to verify TS/Python parity
    c = ChallengeRequest(
        nonce="0" * 64,
        timestamp=1700000000,
        action="delete /tmp/x",
        tool_name="hitl-cli",
        version="1",
    )
    raw = challenge_bytes(c).decode("utf-8")
    expected = (
        '{"action":"delete /tmp/x",'
        '"nonce":"' + "0" * 64 + '",'
        '"timestamp":1700000000,'
        '"tool_name":"hitl-cli",'
        '"version":"1"}'
    )
    assert raw == expected
