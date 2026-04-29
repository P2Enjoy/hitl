export interface ChallengeRequest {
  nonce: string;       // 64 hex chars (256-bit random)
  timestamp: number;   // Unix seconds
  action: string;
  tool_name: string;
  version: string;     // "1"
}

export interface SignedResponse {
  signature: string;    // base64url Ed25519 signature (64 bytes → 86 base64url chars)
  access_token: string; // Keycloak JWT
  user_id: string;      // Keycloak sub claim
  nonce: string;        // echo of challenge nonce
  timestamp: number;    // echo of challenge timestamp
}

export interface DeniedResponse {
  denied: true;
  nonce: string;
  timestamp: number;
}

export type SignOrDenyResponse = SignedResponse | DeniedResponse;

export function isDenied(r: SignOrDenyResponse): r is DeniedResponse {
  return (r as DeniedResponse).denied === true;
}
