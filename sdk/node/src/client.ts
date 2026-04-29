import {
  checkExtensionAvailability,
  generateChallenge,
  requestSignature,
} from "./challenge.js";
import {
  HitlDenied,
  HitlExtensionUnavailable,
  HitlTimeout,
  HitlVerificationError,
} from "./errors.js";
import { OAuthClient } from "./oauth.js";
import { isDenied } from "./types.js";
import type { SignedResponse } from "./types.js";
import { verifySignedResponse } from "./verify.js";

export class HitlClient {
  private readonly oauthClient: OAuthClient;

  constructor(oauthClient: OAuthClient) {
    this.oauthClient = oauthClient;
  }

  static fromEnv(): HitlClient {
    return new HitlClient(OAuthClient.fromEnv());
  }

  /**
   * Run the full challenge → sign → verify pipeline.
   *
   * Returns the verified SignedResponse on approval.
   *
   * @throws {HitlExtensionUnavailable} signing host not reachable
   * @throws {HitlDenied}               user clicked Deny
   * @throws {HitlTimeout}              user did not respond in time
   * @throws {HitlVerificationError}    signature invalid or replay detected
   */
  async requestApproval(action: string, toolName = "@hitl/sdk"): Promise<SignedResponse> {
    const available = await checkExtensionAvailability();
    if (!available) {
      throw new HitlExtensionUnavailable(
        "HITL signing host is not reachable. " +
          "Ensure the browser extension is loaded and the native messaging host is installed. " +
          "Run `npx @hitl/sdk setup host` to install the host.",
      );
    }

    const challenge = generateChallenge(action, toolName);

    let response;
    try {
      response = await requestSignature(challenge);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message.toLowerCase() : "";
      if (msg.includes("timeout") || msg.includes("timed out") || msg.includes("econnaborted")) {
        throw new HitlTimeout(`User did not respond in time: ${e}`);
      }
      throw e;
    }

    if (isDenied(response)) {
      throw new HitlDenied(`User denied the action: ${JSON.stringify(action)}`);
    }

    let approved: boolean;
    try {
      approved = await verifySignedResponse(challenge, response, this.oauthClient);
    } catch (e) {
      if (e instanceof HitlVerificationError) throw e;
      throw new HitlVerificationError(String(e));
    }

    if (!approved) {
      throw new HitlVerificationError("Ed25519 signature verification failed");
    }

    return response;
  }
}
