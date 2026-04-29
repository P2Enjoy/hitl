#!/usr/bin/env node
/**
 * hitl-setup (Node.js) — one-stop setup CLI for the HITL infrastructure.
 *
 * Usage:
 *   npx @hitl/sdk setup infra          Start Keycloak + Redis
 *   npx @hitl/sdk setup hooks          Install Claude Code PreToolUse hooks
 *   npx @hitl/sdk setup host           Install native messaging host
 *   npx @hitl/sdk setup all            Run all of the above
 *   npx @hitl/sdk setup status         Check what's configured
 */

"use strict";

const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const [, , command = "help", ...rest] = process.argv;

// ── helpers ───────────────────────────────────────────────────────────────────

function run(cmd, opts = {}) {
  return spawnSync(cmd, { shell: true, stdio: "inherit", ...opts });
}

function settingsPath(global_) {
  return global_
    ? path.join(os.homedir(), ".claude", "settings.json")
    : path.join(process.cwd(), ".claude", "settings.json");
}

function loadSettings(p) {
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return {};
  }
}

function saveSettings(p, data) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(data, null, 2) + "\n");
}

const HOOK_ENTRY = { type: "command", command: "hitl-hook" };
const HOOK_MATCHERS = [
  { matcher: "Bash", hooks: [HOOK_ENTRY] },
  { matcher: "Edit|Write|MultiEdit", hooks: [HOOK_ENTRY] },
];

function isHitlHook(h) {
  return h && h.type === "command" && h.command === "hitl-hook";
}

function installHooks(cfg) {
  if (!cfg.hooks) cfg.hooks = {};
  if (!cfg.hooks.PreToolUse) cfg.hooks.PreToolUse = [];
  const pre = cfg.hooks.PreToolUse;
  const existing = Object.fromEntries(pre.filter(e => e.matcher).map(e => [e.matcher, e]));
  for (const block of HOOK_MATCHERS) {
    if (existing[block.matcher]) {
      const hl = existing[block.matcher].hooks || (existing[block.matcher].hooks = []);
      if (!hl.some(isHitlHook)) hl.push(HOOK_ENTRY);
    } else {
      pre.push({ matcher: block.matcher, hooks: [HOOK_ENTRY] });
    }
  }
  return cfg;
}

// ── commands ──────────────────────────────────────────────────────────────────

const commands = {
  infra() {
    const sub = rest[0] || "start";
    const composeFile = path.join(__dirname, "..", "data", "docker-compose.yml");
    if (sub === "start") {
      run(`docker compose -f "${composeFile}" up -d`);
    } else if (sub === "stop") {
      run(`docker compose -f "${composeFile}" down`);
    } else if (sub === "status") {
      run(`docker compose -f "${composeFile}" ps`);
    } else if (sub === "logs") {
      run(`docker compose -f "${composeFile}" logs --tail=50 ${rest[1] || ""}`);
    } else {
      console.error(`Unknown infra subcommand: ${sub}`);
      process.exit(1);
    }
  },

  hooks() {
    const global_ = rest.includes("--global");
    const show = rest.includes("--show");
    const uninstall = rest.includes("--uninstall");

    if (show) {
      console.log(JSON.stringify({ hooks: { PreToolUse: HOOK_MATCHERS } }, null, 2));
      return;
    }

    const p = settingsPath(global_);
    let cfg = loadSettings(p);

    if (uninstall) {
      const pre = cfg.hooks?.PreToolUse || [];
      for (const block of pre) {
        if (block.hooks) block.hooks = block.hooks.filter(h => !isHitlHook(h));
      }
      if (cfg.hooks) cfg.hooks.PreToolUse = pre.filter(b => b.hooks?.length);
      saveSettings(p, cfg);
      console.log(`Uninstalled HITL hooks from ${p}`);
    } else {
      cfg = installHooks(cfg);
      saveSettings(p, cfg);
      const scope = global_ ? "global (~/.claude/)" : "project (.claude/)";
      console.log(`Installed HITL hooks in ${scope}settings.json → ${p}`);
    }
  },

  host() {
    const browser = rest.find(a => a.startsWith("--browser="))?.split("=")[1] || "chrome";
    // Delegate to the extension's installer script
    const installerCandidates = [
      path.join(process.cwd(), "extension", "src", "signing-host", "install.js"),
      path.join(__dirname, "..", "..", "extension", "src", "signing-host", "install.js"),
    ];
    const installer = installerCandidates.find(p => fs.existsSync(p));
    if (!installer) {
      console.error(
        "Cannot find extension/src/signing-host/install.js.\n" +
        "Build the extension first: cd extension && npm run build"
      );
      process.exit(1);
    }
    const env = { ...process.env, BROWSER: browser };
    run(`node "${installer}"`, { env });
  },

  status() {
    console.log("HITL status\n" + "─".repeat(40));

    // Docker
    try {
      const r = spawnSync("docker", ["compose", "ps", "--format", "json"], { encoding: "utf-8" });
      if (r.status === 0 && r.stdout.trim()) {
        console.log("  Infrastructure: running");
      } else {
        console.log("  Infrastructure: not running  (run: npx @hitl/sdk setup infra)");
      }
    } catch {
      console.log("  Infrastructure: docker not available");
    }

    // Hooks
    const projectPath = settingsPath(false);
    const globalPath = settingsPath(true);
    function hasHooks(p) {
      const cfg = loadSettings(p);
      const pre = cfg.hooks?.PreToolUse || [];
      return pre.some(b => b.hooks?.some(isHitlHook));
    }
    if (hasHooks(projectPath)) {
      console.log(`  Hooks:          project-level installed (${projectPath})`);
    } else if (hasHooks(globalPath)) {
      console.log(`  Hooks:          global installed (${globalPath})`);
    } else {
      console.log("  Hooks:          not installed  (run: npx @hitl/sdk setup hooks)");
    }

    // Env vars
    const required = ["KEYCLOAK_HOST", "KEYCLOAK_CLI_CLIENT_ID", "KEYCLOAK_CLI_CLIENT_SECRET"];
    const missing = required.filter(v => !process.env[v]);
    if (missing.length) {
      console.log(`  Env vars:       missing: ${missing.join(", ")}`);
    } else {
      console.log("  Env vars:       all required vars set");
    }
  },

  all() {
    console.log("==> Starting infrastructure...");
    commands.infra.call({ rest: [] });

    console.log("\n==> Installing Claude Code hooks...");
    const p = settingsPath(false);
    const cfg = installHooks(loadSettings(p));
    saveSettings(p, cfg);
    console.log(`  Hooks installed: ${p}`);

    console.log("\n==> Installing native messaging host...");
    commands.host();

    console.log("\nDone! Next:");
    console.log("  1. Load extension/dist-chrome/ in Chrome (developer mode)");
    console.log("  2. Click the extension icon → Login");
    console.log("  3. Set KEYCLOAK_HOST, KEYCLOAK_CLI_CLIENT_ID, KEYCLOAK_CLI_CLIENT_SECRET in .env");
  },

  help() {
    console.log(`
hitl-setup — HITL infrastructure setup

Commands:
  infra [start|stop|status|logs]   Manage Keycloak + Redis via Docker Compose
  hooks [--global] [--uninstall]   Install Claude Code PreToolUse hooks
  host  [--browser=chrome|firefox] Install native messaging host
  all                              Run infra + hooks + host
  status                           Check what's configured
    `.trim());
  },
};

const handler = commands[command];
if (handler) {
  handler();
} else {
  console.error(`Unknown command: ${command}`);
  commands.help();
  process.exit(1);
}
