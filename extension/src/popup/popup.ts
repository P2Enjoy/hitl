import type { BackgroundResponse, BackgroundMessage } from "../types/messages.js";
import type { ChallengeRequest } from "../types/challenge.js";

function sendMessage(msg: BackgroundMessage): Promise<BackgroundResponse> {
  return chrome.runtime.sendMessage(msg) as Promise<BackgroundResponse>;
}

function show(id: string): void {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  document.getElementById(id)?.classList.remove("hidden");
}

function setDot(state: "grey" | "green" | "yellow" | "red"): void {
  const dot = document.getElementById("status-dot");
  if (!dot) return;
  dot.className = `dot dot-${state}`;
}

let countdownInterval: ReturnType<typeof setInterval> | null = null;

function startCountdown(expiresAt: number): void {
  if (countdownInterval) clearInterval(countdownInterval);
  const el = document.getElementById("countdown");
  countdownInterval = setInterval(() => {
    const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
    if (el) el.textContent = String(remaining);
    if (remaining === 0) {
      if (countdownInterval) clearInterval(countdownInterval);
      showResult(false, "Approval timed out");
    }
  }, 1000);
}

function showApproval(challenge: ChallengeRequest): void {
  const actionEl = document.getElementById("action-text");
  const toolEl = document.getElementById("tool-name");
  const nonceEl = document.getElementById("nonce-preview");
  if (actionEl) actionEl.textContent = challenge.action;
  if (toolEl) toolEl.textContent = challenge.tool_name;
  if (nonceEl) nonceEl.textContent = challenge.nonce.slice(0, 12) + "…";
  show("view-approval");
  setDot("yellow");
  const ttlSeconds = 300;
  startCountdown(Date.now() + ttlSeconds * 1000);
}

function showResult(approved: boolean, message?: string): void {
  if (countdownInterval) clearInterval(countdownInterval);
  const iconEl = document.getElementById("result-icon");
  const textEl = document.getElementById("result-text");
  if (iconEl) iconEl.textContent = approved ? "✅" : "❌";
  if (textEl) textEl.textContent = message ?? (approved ? "Approved" : "Denied");
  show("view-result");
  setDot(approved ? "green" : "red");
  setTimeout(() => window.close(), 2000);
}

async function init(): Promise<void> {
  const statusResp = await sendMessage({ type: "GET_STATUS" });
  if (statusResp.type !== "STATUS") return;

  if (!statusResp.authenticated) {
    show("view-login");
    setDot("grey");
    document.getElementById("btn-login")?.addEventListener("click", async () => {
      const resp = await sendMessage({ type: "LOGIN" });
      if (resp.type === "LOGIN_RESULT" && resp.success) {
        await init();
      } else if (resp.type === "LOGIN_RESULT") {
        showResult(false, `Login failed: ${resp.error ?? "unknown error"}`);
      }
    });
    return;
  }

  // Logged in — check for pending challenge
  const pendingResp = await sendMessage({ type: "GET_PENDING_CHALLENGE" });
  if (pendingResp.type === "PENDING_CHALLENGE" && pendingResp.challenge) {
    showApproval(pendingResp.challenge);

    document.getElementById("btn-approve")?.addEventListener("click", async () => {
      const resp = await chrome.runtime.sendMessage({ type: "POPUP_APPROVE" }) as BackgroundResponse;
      showResult(true, resp.type === "ERROR" ? `Error: ${resp.message}` : "Approved");
    });

    document.getElementById("btn-deny")?.addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "POPUP_DENY" });
      showResult(false, "Denied");
    });
  } else {
    // Idle state
    const usernameEl = document.getElementById("username-label");
    if (usernameEl) usernameEl.textContent = statusResp.username ?? "";
    show("view-idle");
    setDot("green");

    document.getElementById("btn-logout")?.addEventListener("click", async () => {
      await sendMessage({ type: "LOGOUT" });
      await init();
    });
  }
}

document.addEventListener("DOMContentLoaded", init);
