#!/usr/bin/env node
/**
 * Official Cursor Agent SDK bridge for ShipCrew.
 * Uses browser login (Cursor.auth.login) — no manual API key required.
 */
import { pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

function print(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

async function loadSdk() {
  try {
    return await import("@cursor/sdk");
  } catch (err) {
    print({
      ok: false,
      error: `@cursor/sdk не установлен. cd tools/cursor-runner && npm install. ${String(err)}`,
    });
    process.exit(2);
  }
}

async function cmdStatus() {
  const { Cursor } = await loadSdk();
  try {
    const status = await Cursor.auth.status();
    print({ ok: true, ...status });
  } catch (err) {
    print({ ok: false, status: "error", error: String(err) });
    process.exit(1);
  }
}

async function cmdLogin() {
  const { Cursor } = await loadSdk();
  try {
    const result = await Cursor.auth.login({
      apiKeyName: "ShipCrew",
      onLoginUrl: (url) => {
        print({ ok: true, phase: "open_browser", url });
      },
    });
    print({
      ok: true,
      phase: "done",
      email: result.email || null,
      apiKeyExpiresAtMs: result.apiKeyExpiresAtMs,
      // ключ не печатаем целиком
      keyPreview: result.apiKey ? `${result.apiKey.slice(0, 4)}…${result.apiKey.slice(-4)}` : null,
    });
  } catch (err) {
    print({ ok: false, error: String(err) });
    process.exit(1);
  }
}

async function cmdRun(argv) {
  const cwdIdx = argv.indexOf("--cwd");
  const promptIdx = argv.indexOf("--prompt");
  const cwd = cwdIdx >= 0 ? argv[cwdIdx + 1] : process.cwd();
  let prompt = promptIdx >= 0 ? argv[promptIdx + 1] : "";
  if (!prompt || prompt === "-") {
    prompt = fs.readFileSync(0, "utf8");
  }
  if (!prompt.trim()) {
    print({ ok: false, error: "empty prompt" });
    process.exit(1);
  }

  const { Agent, Cursor } = await loadSdk();
  const auth = await Cursor.auth.status();
  if (!auth || auth.status !== "logged-in") {
    print({ ok: false, error: "Cursor SDK не залогинен. Сначала: node run.mjs login" });
    process.exit(1);
  }

  const agent = await Agent.create({
    local: { cwd },
  });
  const run = await agent.send(prompt);
  const events = [];
  let text = "";
  for await (const event of run.stream()) {
    events.push(event?.type || "event");
    const chunk =
      event?.message?.content ||
      event?.text ||
      event?.delta ||
      (typeof event?.content === "string" ? event.content : "");
    if (typeof chunk === "string") text += chunk;
    else if (Array.isArray(chunk)) {
      for (const part of chunk) {
        if (typeof part?.text === "string") text += part.text;
      }
    }
  }
  print({
    ok: true,
    cwd,
    summary: text.slice(0, 12000) || "Cursor agent finished",
    events: events.slice(-40),
  });
}

const [cmd, ...rest] = process.argv.slice(2);
if (cmd === "status") await cmdStatus();
else if (cmd === "login") await cmdLogin();
else if (cmd === "run") await cmdRun(rest);
else {
  print({ ok: false, error: "usage: run.mjs <status|login|run> [--cwd DIR] [--prompt TEXT|-]" });
  process.exit(1);
}

// silence unused in some bundlers
void path;
void pathToFileURL;
