export { HitlClient } from "./client.js";
export { OAuthClient, KeycloakClient } from "./oauth.js";
export { generateChallenge, challengeBytes, requestSignature, checkExtensionAvailability } from "./challenge.js";
export { verifySignedResponse } from "./verify.js";
export {
  HitlError,
  HitlDenied,
  HitlTimeout,
  HitlVerificationError,
  HitlExtensionUnavailable,
} from "./errors.js";
export type { ChallengeRequest, SignedResponse, DeniedResponse, SignOrDenyResponse } from "./types.js";
export { isDenied } from "./types.js";
