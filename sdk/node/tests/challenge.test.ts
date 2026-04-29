import { describe, it, expect } from "vitest";
import { challengeBytes, generateChallenge } from "../src/challenge.js";
import type { ChallengeRequest } from "../src/types.js";

describe("challengeBytes", () => {
  it("produces sorted keys with no whitespace", () => {
    const ch: ChallengeRequest = {
      nonce: "a".repeat(64),
      timestamp: 1700000000,
      action: "delete /tmp/x",
      tool_name: "test-tool",
      version: "1",
    };
    const bytes = challengeBytes(ch);
    const text = bytes.toString("utf-8");
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const keys = Object.keys(parsed);

    expect(keys).toEqual([...keys].sort());
    expect(text).not.toContain(" ");
    expect(text).not.toContain("\n");
  });

  it("produces canonical format byte-for-byte identical to Python", () => {
    const ch: ChallengeRequest = {
      nonce: "b".repeat(64),
      timestamp: 1000,
      action: "run",
      tool_name: "tool",
      version: "1",
    };
    const bytes = challengeBytes(ch);
    const expected = Buffer.from(
      `{"action":"run","nonce":"${"b".repeat(64)}","timestamp":1000,"tool_name":"tool","version":"1"}`,
      "utf-8",
    );
    expect(bytes).toEqual(expected);
  });
});

describe("generateChallenge", () => {
  it("produces a valid challenge with correct shape", () => {
    const ch = generateChallenge("my action", "my-tool");
    expect(ch.action).toBe("my action");
    expect(ch.tool_name).toBe("my-tool");
    expect(ch.version).toBe("1");
    expect(ch.nonce).toHaveLength(64);
    expect(/^[0-9a-f]+$/.test(ch.nonce)).toBe(true);
    expect(ch.timestamp).toBeGreaterThan(0);
  });
});
