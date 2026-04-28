import type { BackgroundMessage, BackgroundResponse } from "../types/messages.js";
import type { ChallengeRequest, ApprovalResult } from "../types/challenge.js";
import { generateKeypair, exportPublicKey, signChallenge } from "./crypto.js";
import {
  storeKeypair,
  loadKeypair,
  loadTokens,
  loadUser,
  clearAll,
} from "./keystore.js";
import { loginWithKeycloak, logout } from "./oauth.js";
import { registerPublicKey } from "./pubkey-register.js";
import { trackNonce } from "./nonce-tracker.js";
import {
  setPendingChallenge,
  getPendingChallenge,
  resolvePending,
  rejectPending,
} from "./signing-server.js";

// ── Native Messaging: relay from signing-host HTTP bridge ───────────────────

let nativePort: chrome.runtime.Port | null = null;

function connectNativeHost(): void {
  nativePort = chrome.runtime.connectNative("com.hitl.signer");

  nativePort.onMessage.addListener(async (msg: unknown) => {
    const message = msg as { type: string; challenge?: ChallengeRequest; requestId?: string };
    if (message.type === "SIGN_REQUEST" && message.challenge) {
      const result = await handleSignRequest(message.challenge);
      nativePort?.postMessage({ type: "SIGN_RESPONSE", requestId: message.requestId, result });
    }
  });

  nativePort.onDisconnect.addListener(() => {
    nativePort = null;
    // Reconnect after a short delay
    setTimeout(connectNativeHost, 5000);
  });
}

// Connect native host on service worker startup
connectNativeHost();

// ── Internal message handler (from popup) ──────────────────────────────────

chrome.runtime.onMessage.addListener(
  (message: unknown, _sender, sendResponse: (resp: BackgroundResponse) => void) => {
    const msg = message as BackgroundMessage;
    handleMessage(msg).then(sendResponse).catch((err: Error) => {
      sendResponse({ type: "ERROR", message: err.message });
    });
    return true; // keep channel open for async response
  },
);

async function handleMessage(msg: BackgroundMessage): Promise<BackgroundResponse> {
  switch (msg.type) {
    case "GET_STATUS": {
      const tokens = await loadTokens();
      const user = await loadUser();
      const keypair = await loadKeypair();
      return {
        type: "STATUS",
        authenticated: !!tokens && tokens.expires_at > Date.now() / 1000,
        hasKeypair: !!keypair,
        username: user?.username ?? null,
      };
    }

    case "LOGIN": {
      try {
        const tokens = await loginWithKeycloak();
        // Generate fresh keypair on every login
        const pair = await generateKeypair();
        await storeKeypair(pair);
        const pubkey = await exportPublicKey(pair.publicKey);
        await registerPublicKey(tokens.access_token, tokens.user_id, pubkey);
        return { type: "LOGIN_RESULT", success: true };
      } catch (err) {
        return { type: "LOGIN_RESULT", success: false, error: String(err) };
      }
    }

    case "LOGOUT": {
      await logout();
      return { type: "STATUS", authenticated: false, hasKeypair: false, username: null };
    }

    case "GET_PENDING_CHALLENGE": {
      return { type: "PENDING_CHALLENGE", challenge: getPendingChallenge() };
    }

    case "SIGN_CHALLENGE": {
      const result = await handleSignRequest(msg.challenge);
      return { type: "SIGN_RESULT", result };
    }
  }
}

async function handleSignRequest(challenge: ChallengeRequest): Promise<ApprovalResult> {
  // Check nonce hasn't been used this session
  if (!trackNonce(challenge.nonce)) {
    throw new Error(`Nonce already used: ${challenge.nonce}`);
  }

  // Queue challenge for popup approval
  const resultPromise = setPendingChallenge(challenge);

  // Open popup to prompt user
  await chrome.action.openPopup();

  // Wait for user response
  const result = await resultPromise;
  return result;
}

// ── Popup approval/denial ───────────────────────────────────────────────────

chrome.runtime.onMessage.addListener(
  (message: unknown, _sender, sendResponse: (resp: BackgroundResponse) => void) => {
    const msg = message as { type: "POPUP_APPROVE" | "POPUP_DENY" };
    if (msg.type === "POPUP_APPROVE") {
      handleApprove().then(sendResponse).catch((err: Error) =>
        sendResponse({ type: "ERROR", message: err.message }),
      );
      return true;
    }
    if (msg.type === "POPUP_DENY") {
      handleDeny();
      sendResponse({ type: "STATUS", authenticated: false, hasKeypair: false, username: null });
    }
  },
);

async function handleApprove(): Promise<BackgroundResponse> {
  const challenge = getPendingChallenge();
  if (!challenge) throw new Error("No pending challenge to approve");

  const [pair, tokens] = await Promise.all([loadKeypair(), loadTokens()]);
  if (!pair) throw new Error("No keypair in session. Please log in.");
  if (!tokens) throw new Error("Not authenticated. Please log in.");

  const signature = await signChallenge(pair.privateKey, challenge);

  const result: ApprovalResult = {
    signature,
    access_token: tokens.access_token,
    user_id: tokens.user_id,
    nonce: challenge.nonce,
    timestamp: challenge.timestamp,
  };

  resolvePending(result);
  return { type: "SIGN_RESULT", result };
}

function handleDeny(): void {
  const challenge = getPendingChallenge();
  if (challenge) {
    resolvePending({ denied: true, nonce: challenge.nonce, timestamp: challenge.timestamp });
  }
}
