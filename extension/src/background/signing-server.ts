import type { ChallengeRequest, ApprovalResult } from "../types/challenge.js";

// Pending challenge waiting for user action in the popup.
let pendingChallenge: ChallengeRequest | null = null;
let pendingResolve: ((result: ApprovalResult) => void) | null = null;
let pendingReject: ((err: Error) => void) | null = null;

export function setPendingChallenge(challenge: ChallengeRequest): Promise<ApprovalResult> {
  // Clear any stale pending challenge
  if (pendingReject) {
    pendingReject(new Error("Superseded by a new challenge"));
    pendingReject = null;
    pendingResolve = null;
  }

  pendingChallenge = challenge;

  return new Promise((resolve, reject) => {
    pendingResolve = resolve;
    pendingReject = reject;

    // Auto-expire after TTL
    const ttl = parseInt(
      (typeof globalThis !== "undefined" &&
        (globalThis as Record<string, unknown>)["CHALLENGE_TTL_SECONDS"] as string) ||
        "300",
    );
    setTimeout(() => {
      if (pendingChallenge?.nonce === challenge.nonce) {
        clearPendingChallenge();
        reject(new Error("Challenge expired — user did not respond in time"));
      }
    }, ttl * 1000);
  });
}

export function getPendingChallenge(): ChallengeRequest | null {
  return pendingChallenge;
}

export function resolvePending(result: ApprovalResult): void {
  pendingChallenge = null;
  pendingResolve?.(result);
  pendingResolve = null;
  pendingReject = null;
}

export function rejectPending(reason: string): void {
  pendingChallenge = null;
  pendingReject?.(new Error(reason));
  pendingResolve = null;
  pendingReject = null;
}

export function clearPendingChallenge(): void {
  pendingChallenge = null;
  pendingResolve = null;
  pendingReject = null;
}
