import { describe, it, expect } from "vitest";
import { canonicalChallengeBytes } from "../src/background/crypto.js";
import type { ChallengeRequest } from "../src/types/challenge.js";

describe("canonicalChallengeBytes", () => {
  it("produces sorted-key JSON with no whitespace", () => {
    const challenge: ChallengeRequest = {
      nonce: "abc123",
      timestamp: 1700000000,
      action: "delete file",
      tool_name: "hitl-cli",
      version: "1",
    };
    const bytes = canonicalChallengeBytes(challenge);
    const str = new TextDecoder().decode(bytes);
    expect(str).toBe(
      '{"action":"delete file","nonce":"abc123","timestamp":1700000000,"tool_name":"hitl-cli","version":"1"}',
    );
  });

  it("is deterministic across calls", () => {
    const challenge: ChallengeRequest = {
      nonce: "xyz",
      timestamp: 12345,
      action: "test",
      tool_name: "test-tool",
      version: "1",
    };
    const a = canonicalChallengeBytes(challenge);
    const b = canonicalChallengeBytes(challenge);
    expect(new TextDecoder().decode(a)).toBe(new TextDecoder().decode(b));
  });
});
