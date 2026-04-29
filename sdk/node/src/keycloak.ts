import axios from "axios";

export class KeycloakClient {
  private readonly baseUrl: string;
  private readonly realm: string;
  private readonly clientId: string;
  private readonly clientSecret: string;
  private accessToken: string | null = null;
  private tokenExpiresAt = 0;

  constructor(baseUrl: string, realm: string, clientId: string, clientSecret: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.realm = realm;
    this.clientId = clientId;
    this.clientSecret = clientSecret;
  }

  static fromEnv(): KeycloakClient {
    const baseUrl = process.env.KEYCLOAK_HOST;
    const realm = process.env.KEYCLOAK_REALM ?? "hitl";
    const clientId = process.env.KEYCLOAK_CLI_CLIENT_ID;
    const clientSecret = process.env.KEYCLOAK_CLI_CLIENT_SECRET;

    if (!baseUrl) throw new Error("KEYCLOAK_HOST is required");
    if (!clientId) throw new Error("KEYCLOAK_CLI_CLIENT_ID is required");
    if (!clientSecret) throw new Error("KEYCLOAK_CLI_CLIENT_SECRET is required");

    return new KeycloakClient(baseUrl, realm, clientId, clientSecret);
  }

  private async ensureToken(): Promise<void> {
    if (this.accessToken && Date.now() / 1000 < this.tokenExpiresAt - 10) return;

    const tokenUrl = `${this.baseUrl}/realms/${this.realm}/protocol/openid-connect/token`;
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
    const url = `${this.baseUrl}/admin/realms/${this.realm}/users/${userId}`;
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
    const url = `${this.baseUrl}/admin/realms/${this.realm}/users/${userId}`;
    const resp = await axios.get<Record<string, unknown>>(url, {
      headers: { Authorization: `Bearer ${this.accessToken}` },
    });
    return resp.data;
  }
}
