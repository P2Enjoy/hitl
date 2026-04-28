#!/usr/bin/env node
/**
 * Native Messaging Host — HTTP relay between tools and the browser extension.
 *
 * Listens on localhost:7331 for POST /sign requests from tools.
 * Forwards challenge to the extension via the NativeMessaging stdio protocol.
 * Returns the signed response back over HTTP.
 *
 * NativeMessaging protocol: each message is a 4-byte little-endian length
 * followed by a UTF-8 JSON payload, on stdin/stdout.
 */

"use strict";

const http = require("http");

const PORT = parseInt(process.env.EXTENSION_SIGNING_PORT || "7331", 10);

// ── NativeMessaging I/O ───────────────────────────────────────────────────

/** @type {Map<string, {resolve: Function, reject: Function, timer: NodeJS.Timeout}>} */
const pending = new Map();

function readNativeMessage(onMessage) {
  let buffer = Buffer.alloc(0);

  process.stdin.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);

    while (buffer.length >= 4) {
      const msgLen = buffer.readUInt32LE(0);
      if (buffer.length < 4 + msgLen) break;

      const json = buffer.slice(4, 4 + msgLen).toString("utf8");
      buffer = buffer.slice(4 + msgLen);

      try {
        onMessage(JSON.parse(json));
      } catch (e) {
        process.stderr.write(`Failed to parse native message: ${e}\n`);
      }
    }
  });
}

function writeNativeMessage(msg) {
  const json = JSON.stringify(msg);
  const buf = Buffer.alloc(4 + Buffer.byteLength(json, "utf8"));
  buf.writeUInt32LE(Buffer.byteLength(json, "utf8"), 0);
  buf.write(json, 4, "utf8");
  process.stdout.write(buf);
}

// Handle responses from the extension
readNativeMessage((msg) => {
  if (msg.type === "SIGN_RESPONSE" && msg.requestId) {
    const entry = pending.get(msg.requestId);
    if (entry) {
      clearTimeout(entry.timer);
      pending.delete(msg.requestId);
      entry.resolve(msg.result);
    }
  }
});

function sendToExtension(challenge, requestId) {
  return new Promise((resolve, reject) => {
    const ttl = parseInt(process.env.CHALLENGE_TTL_SECONDS || "300", 10);
    const timer = setTimeout(() => {
      pending.delete(requestId);
      reject(new Error("Timed out waiting for extension response"));
    }, ttl * 1000 + 5000); // extra 5s grace

    pending.set(requestId, { resolve, reject, timer });
    writeNativeMessage({ type: "SIGN_REQUEST", challenge, requestId });
  });
}

// ── HTTP Server ────────────────────────────────────────────────────────────

const server = http.createServer((req, res) => {
  // CORS headers — only allow localhost
  res.setHeader("Access-Control-Allow-Origin", "http://localhost");
  res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", authenticated: pending.size >= 0 }));
    return;
  }

  if (req.method === "POST" && req.url === "/sign") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", async () => {
      let challenge;
      try {
        challenge = JSON.parse(body);
      } catch {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Invalid JSON body" }));
        return;
      }

      if (!challenge.nonce || !challenge.timestamp || !challenge.action) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Missing required challenge fields" }));
        return;
      }

      const requestId = `${challenge.nonce}-${Date.now()}`;
      try {
        const result = await sendToExtension(challenge, requestId);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(result));
      } catch (err) {
        res.writeHead(504, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err) }));
      }
    });
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(PORT, "127.0.0.1", () => {
  process.stderr.write(`HITL signing host listening on 127.0.0.1:${PORT}\n`);
});

process.on("SIGTERM", () => server.close(() => process.exit(0)));
process.on("SIGINT", () => server.close(() => process.exit(0)));
