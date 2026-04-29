"""Tests for challenge serialization — must match sdk/node/src/challenge.ts."""

import json

import pytest

from hitl.challenge import challenge_bytes, generate_challenge
from hitl.models import ChallengeRequest


def test_challenge_bytes_sorted_keys_no_whitespace() -> None:
    challenge = ChallengeRequest(
        nonce="a" * 64,
        timestamp=1700000000,
        action="delete /tmp/x",
        tool_name="test-tool",
        version="1",
    )
    result = challenge_bytes(challenge)
    parsed = json.loads(result.decode("utf-8"))

    assert list(parsed.keys()) == sorted(parsed.keys())
    assert b" " not in result
    assert b"\n" not in result


def test_challenge_bytes_canonical_format() -> None:
    challenge = ChallengeRequest(
        nonce="b" * 64,
        timestamp=1000,
        action="run",
        tool_name="tool",
        version="1",
    )
    result = challenge_bytes(challenge)
    expected = json.dumps(
        {
            "action": "run",
            "nonce": "b" * 64,
            "timestamp": 1000,
            "tool_name": "tool",
            "version": "1",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert result == expected


def test_generate_challenge_fields() -> None:
    ch = generate_challenge("my action", "my-tool")
    assert ch.action == "my action"
    assert ch.tool_name == "my-tool"
    assert ch.version == "1"
    assert len(ch.nonce) == 64
    assert all(c in "0123456789abcdef" for c in ch.nonce)
    assert ch.timestamp > 0
