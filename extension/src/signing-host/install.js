#!/usr/bin/env node
/**
 * Installs the native messaging host manifest.
 * Run once after building the extension:  node signing-host/install.js
 *
 * Requires the extension ID to be known. Pass as:
 *   EXTENSION_ID=abc123 node signing-host/install.js
 * or it writes a placeholder and prints instructions.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const HOST_SCRIPT = path.resolve(__dirname, "index.js");
const EXTENSION_ID = process.env.EXTENSION_ID || "";

// ── Determine install paths by platform ───────────────────────────────────

function getChromePaths() {
  const platform = os.platform();
  if (platform === "linux") {
    return {
      system: "/etc/opt/chrome/native-messaging-hosts/com.hitl.signer.json",
      user: path.join(os.homedir(), ".config/google-chrome/NativeMessagingHosts/com.hitl.signer.json"),
    };
  }
  if (platform === "darwin") {
    return {
      system: "/Library/Google/Chrome/NativeMessagingHosts/com.hitl.signer.json",
      user: path.join(os.homedir(), "Library/Application Support/Google/Chrome/NativeMessagingHosts/com.hitl.signer.json"),
    };
  }
  if (platform === "win32") {
    return { system: null, user: null, registry: true };
  }
  throw new Error(`Unsupported platform: ${platform}`);
}

function getFirefoxPaths() {
  const platform = os.platform();
  if (platform === "linux") {
    return {
      user: path.join(os.homedir(), ".mozilla/native-messaging-hosts/com.hitl.signer.json"),
    };
  }
  if (platform === "darwin") {
    return {
      user: path.join(os.homedir(), "Library/Application Support/Mozilla/NativeMessagingHosts/com.hitl.signer.json"),
    };
  }
  throw new Error(`Unsupported platform: ${platform}`);
}

// ── Write wrapper script ───────────────────────────────────────────────────

const wrapperPath = path.join(os.homedir(), ".local/bin/hitl-signing-host");

function writeWrapper() {
  const dir = path.dirname(wrapperPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    wrapperPath,
    `#!/usr/bin/env bash\nexec node "${HOST_SCRIPT}" "$@"\n`,
    { mode: 0o755 }
  );
  console.log(`Wrapper script written: ${wrapperPath}`);
}

// ── Write manifest ─────────────────────────────────────────────────────────

function writeManifest(destPath, manifest) {
  const dir = path.dirname(destPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(destPath, JSON.stringify(manifest, null, 2));
  console.log(`Manifest written: ${destPath}`);
}

// ── Main ───────────────────────────────────────────────────────────────────

writeWrapper();

const chromePaths = getChromePaths();
const chromeManifest = {
  name: "com.hitl.signer",
  description: "HITL signing host",
  path: wrapperPath,
  type: "stdio",
  allowed_origins: EXTENSION_ID
    ? [`chrome-extension://${EXTENSION_ID}/`]
    : ["chrome-extension://REPLACE_WITH_EXTENSION_ID/"],
};
writeManifest(chromePaths.user, chromeManifest);

try {
  const firefoxPaths = getFirefoxPaths();
  const firefoxManifest = {
    name: "com.hitl.signer",
    description: "HITL signing host",
    path: wrapperPath,
    type: "stdio",
    allowed_extensions: ["hitl-signer@hitl.dev"],
  };
  writeManifest(firefoxPaths.user, firefoxManifest);
} catch {
  console.log("Firefox native messaging host install skipped (non-Linux/macOS).");
}

if (!EXTENSION_ID) {
  console.log(
    "\n⚠️  Extension ID not set. Update the Chrome manifest at:\n" +
    `   ${chromePaths.user}\n` +
    "   Replace REPLACE_WITH_EXTENSION_ID with your actual Chrome extension ID.\n" +
    "   Find it at chrome://extensions after loading the unpacked extension.\n"
  );
}

console.log("\nNative messaging host installed successfully.");
