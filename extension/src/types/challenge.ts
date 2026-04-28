export interface ChallengeRequest {
  nonce: string;       // 64 hex chars (256-bit random)
  timestamp: number;   // Unix epoch seconds
  action: string;      // Human-readable description of the action
  tool_name: string;   // Name of the requesting tool
  version: "1";        // Schema version — bump when fields change
}

export interface SignedResponse {
  signature: string;     // base64url(Ed25519 signature, 64 bytes)
  access_token: string;  // Keycloak JWT access token
  user_id: string;       // Keycloak sub claim
  nonce: string;         // Echo of challenge nonce
  timestamp: number;     // Echo of challenge timestamp
}

export interface DeniedResponse {
  denied: true;
  nonce: string;
  timestamp: number;
}

export type ApprovalResult = SignedResponse | DeniedResponse;
