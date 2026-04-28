import { describe, it, expect } from "vitest";
import { base64urlEncode, base64urlDecode } from "../src/utils/base64url.js";

describe("base64url", () => {
  it("round-trips arbitrary bytes", () => {
    const original = new Uint8Array([1, 2, 3, 255, 128, 0, 99]);
    const encoded = base64urlEncode(original);
    const decoded = base64urlDecode(encoded);
    expect(decoded).toEqual(original);
  });

  it("produces URL-safe characters only", () => {
    const bytes = new Uint8Array(64).fill(0xff);
    const encoded = base64urlEncode(bytes);
    expect(encoded).not.toContain("+");
    expect(encoded).not.toContain("/");
    expect(encoded).not.toContain("=");
  });

  it("encodes empty array to empty string", () => {
    expect(base64urlEncode(new Uint8Array(0))).toBe("");
  });
});
