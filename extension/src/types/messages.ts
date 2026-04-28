import type { ChallengeRequest, ApprovalResult } from "./challenge.js";

export type BackgroundMessage =
  | { type: "SIGN_CHALLENGE"; challenge: ChallengeRequest }
  | { type: "GET_STATUS" }
  | { type: "LOGIN" }
  | { type: "LOGOUT" }
  | { type: "GET_PENDING_CHALLENGE" };

export type BackgroundResponse =
  | { type: "SIGN_RESULT"; result: ApprovalResult }
  | { type: "STATUS"; authenticated: boolean; hasKeypair: boolean; username: string | null }
  | { type: "LOGIN_RESULT"; success: boolean; error?: string }
  | { type: "PENDING_CHALLENGE"; challenge: ChallengeRequest | null }
  | { type: "ERROR"; message: string };

export type PopupMessage =
  | { type: "APPROVE" }
  | { type: "DENY" }
  | { type: "LOGIN" }
  | { type: "LOGOUT" };
