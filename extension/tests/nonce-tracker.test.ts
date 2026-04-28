import { describe, it, expect, beforeEach } from "vitest";
import { trackNonce, hasNonce, clearNonces } from "../src/background/nonce-tracker.js";

describe("nonce-tracker", () => {
  beforeEach(() => clearNonces());

  it("accepts a fresh nonce", () => {
    expect(trackNonce("abc123")).toBe(true);
  });

  it("rejects a duplicate nonce", () => {
    trackNonce("abc123");
    expect(trackNonce("abc123")).toBe(false);
  });

  it("accepts different nonces", () => {
    expect(trackNonce("nonce1")).toBe(true);
    expect(trackNonce("nonce2")).toBe(true);
  });

  it("hasNonce reflects tracked state", () => {
    expect(hasNonce("xyz")).toBe(false);
    trackNonce("xyz");
    expect(hasNonce("xyz")).toBe(true);
  });

  it("clearNonces resets state", () => {
    trackNonce("nonce1");
    clearNonces();
    expect(trackNonce("nonce1")).toBe(true);
  });
});
