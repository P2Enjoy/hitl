from pydantic import BaseModel, Field


class ChallengeRequest(BaseModel):
    nonce: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]+$")
    timestamp: int
    action: str = Field(..., min_length=1, max_length=4096)
    tool_name: str = Field(..., min_length=1, max_length=256)
    version: str = Field(default="1")


class SignedResponse(BaseModel):
    signature: str      # base64url Ed25519 signature (64 bytes)
    access_token: str   # Keycloak JWT
    user_id: str        # Keycloak sub claim
    nonce: str          # Echo of challenge nonce
    timestamp: int      # Echo of challenge timestamp


class DeniedResponse(BaseModel):
    denied: bool = True
    nonce: str
    timestamp: int


class HealthResponse(BaseModel):
    status: str
    authenticated: bool
