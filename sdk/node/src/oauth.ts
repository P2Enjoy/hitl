import axios from "axios";

export class OAuthClient {
  private readonly _oauthServerUrl: string;
  private readonly _realm: string;
  private readonly clientId: string;
  private readonly clientSecret: string;
  private accessToken: string | null = null;
  private tokenExpiresAt = 0;

  constructor(oauthServerUrl: string, realm: string, clientId: string, clientSecret: string) {
    this._oauthServerUrl = oauthServerUrl.replace(/\/$/, "");
    this._realm = realm;
    this.clientId = clientId;
    this.clientSecret = clientSecret;
  }

  get oauthServerUrl(): string {
    return this._oauthServerUrl;
  }

  get realm(): string {
    return this._realm;
  }

  /**
   * Construct from environment variables.
   * Prefers OAUTH_* names; falls back to KEYCLOAK_* for backward compatibility.
   */
  static fromEnv(): OAuthClient {
    const oauthServerUrl =
      process.env.OAUTH_SERVER_URL ?? process.env.KEYCLOAK_HOST;
    const realm =
      process.env.OAUTH_REALM ?? process.env.KEYCLOAK_REALM ?? "hitl";
    const clientId =
      process.env.OAUTH_CLI_CLIENT_ID ?? process.env.KEYCLOAK_CLI_CLIENT_ID;
    const clientSecret =
      process.env.OAUTH_CLI_CLIENT_SECRET ?? process.env.KEYCLOAK_CLI_CLIENT_SECRET;

    if (!oauthServerUrl)
      throw new Error("OAUTH_SERVER_URL (or KEYCLOAK_HOST) is required");
    if (!clientId)
      throw new Error("OAUTH_CLI_CLIENT_ID (or KEYCLOAK_CLI_CLIENT_ID) is required");
    if (!clientSecret)
      throw new Error("OAUTH_CLI_CLIENT_SECRET (or KEYCLOAK_CLI_CLIENT_SECRET) is required");

    return new OAuthClient(oauthServerUrl, realm, clientId, clientSecret);
  }

  private async ensureToken(): Promise<void> {
    if (this.accessToken && Date.now() / 1000 < this.tokenExpiresAt - 10) return;

    const tokenUrl = `${this._oauthServerUrl}/realms/${this._realm}/protocol/openid-connect/token`;
    const params = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: this.clientId,
      client_secret: this.clientSecret,
    });

    const resp = await axios.post<{ access_token: string; expires_in: number }>(
      tokenUrl,
      params.toString(),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
    );

    this.accessToken = resp.data.access_token;
    this.tokenExpiresAt = Date.now() / 1000 + (resp.data.expires_in ?? 300);
  }

  async getUserPubkey(userId: string): Promise<string> {
    await this.ensureToken();
    const url = `${this._oauthServerUrl}/admin/realms/${this._realm}/users/${userId}`;
    const resp = await axios.get<{ attributes?: Record<string, string[]> }>(url, {
      headers: { Authorization: `Bearer ${this.accessToken}` },
    });

    const keys = resp.data.attributes?.ed25519_public_key ?? [];
    if (keys.length === 0) {
      throw new Error(`No ed25519_public_key registered for user ${userId}`);
    }
    return keys[0];
  }

  async getUserInfo(userId: string): Promise<Record<string, unknown>> {
    await this.ensureToken();
    const url = `${this._oauthServerUrl}/admin/realms/${this._realm}/users/${userId}`;
    const resp = await axios.get<Record<string, unknown>>(url, {
      headers: { Authorization: `Bearer ${this.accessToken}` },
    });
    return resp.data;
  }
}

// Backward-compatible alias
export const KeycloakClient = OAuthClient;
export type KeycloakClient = OAuthClient;
