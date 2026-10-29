// Family Cards DEMO — access-code gate (Cloudflare Pages middleware).
// Demo edition: the codes in codes.json are demo codes for the
// fictional Emma / Noah cards, minted with mint_codes.py.
// Runs on EVERY request, including static assets.
// Access codes arrive as ?c=<token>; only their SHA-256 hashes live in
// codes.json (imported at build time — no runtime assets fetch, so no
// middleware recursion). A valid code mints a signed fc_auth cookie
// (HMAC-SHA256 over a base64url JSON payload, keyed by env.CODE_SECRET)
// and redirects to the same URL without the code. If CODE_SECRET is not
// configured the gate fails closed: everything returns 401.

import codes from "../codes.json";

const KID_FILES = { emma: "emma.json", noah: "noah.json" };
const COOKIE_NAME = "fc_auth";

const EXPIRED_PAGE = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Link expired</title></head>
<body style="font-family: system-ui, sans-serif; text-align: center; padding: 48px 20px; background: #fdf8f2; color: #222;">
<h1 style="font-size: 1.5rem;">This link has expired</h1>
<p style="font-size: 1.15rem;">Whoever shared this demo with you can give you a fresh one.</p>
</body></html>`;

const FORBIDDEN_PAGE = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Not your card</title></head>
<body style="font-family: system-ui, sans-serif; text-align: center; padding: 48px 20px; background: #fdf8f2; color: #222;">
<h1 style="font-size: 1.5rem;">That's not your card</h1>
<p style="font-size: 1.15rem;">Use the link that came with your own demo card.</p>
</body></html>`;

function htmlPage(body, status) {
  return new Response(body, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

export async function sha256Hex(text) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(text)
  );
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function b64urlEncodeBytes(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function b64urlEncodeText(text) {
  return b64urlEncodeBytes(new TextEncoder().encode(text));
}

export function b64urlDecodeText(part) {
  const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export async function hmacSign(secret, payloadPart) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payloadPart)
  );
  return b64urlEncodeBytes(new Uint8Array(sig));
}

export async function makeCookieValue(scope, exp, secret) {
  const payloadPart = b64urlEncodeText(JSON.stringify({ scope, exp }));
  const sigPart = await hmacSign(secret, payloadPart);
  return `${payloadPart}.${sigPart}`;
}

export async function verifyCookieValue(value, secret, nowMs = Date.now()) {
  if (!value || typeof value !== "string") return null;
  const dot = value.indexOf(".");
  if (dot <= 0 || dot === value.length - 1) return null;
  const payloadPart = value.slice(0, dot);
  const sigPart = value.slice(dot + 1);
  const expected = await hmacSign(secret, payloadPart);
  if (sigPart.length !== expected.length) return null;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= sigPart.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  if (diff !== 0) return null;
  let payload;
  try {
    payload = JSON.parse(b64urlDecodeText(payloadPart));
  } catch {
    return null;
  }
  if (!payload || typeof payload.scope !== "string" || !payload.exp) {
    return null;
  }
  if (!(Date.parse(payload.exp) > nowMs)) return null;
  return payload;
}

function readCookie(request, name) {
  const header = request.headers.get("cookie") || "";
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    if (part.slice(0, eq).trim() === name) return part.slice(eq + 1).trim();
  }
  return null;
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname;

  // Crawlers may always read the Disallow file.
  if (path === "/robots.txt") return context.next();

  const secret = env.CODE_SECRET;
  // Fail closed when the signing secret is not configured.
  if (!secret) return htmlPage(EXPIRED_PAGE, 401);

  // --- Code redemption: ?c=<token> on any request -------------------
  const token = url.searchParams.get("c");
  if (token !== null) {
    const hash = await sha256Hex(token);
    const now = Date.now();
    const entry = (codes || []).find(
      (c) => c.sha256 === hash && Date.parse(c.expires) > now
    );
    if (!entry) return htmlPage(EXPIRED_PAGE, 401);
    const value = await makeCookieValue(entry.scope, entry.expires, secret);
    const clean = new URL(url);
    clean.searchParams.delete("c");
    const expiresUtc = new Date(entry.expires).toUTCString();
    return new Response(null, {
      status: 302,
      headers: {
        location: clean.toString(),
        "set-cookie":
          `${COOKIE_NAME}=${value}; HttpOnly; Secure; SameSite=Lax; ` +
          `Path=/; Expires=${expiresUtc}`,
        "cache-control": "no-store",
      },
    });
  }

  // --- Cookie authentication ----------------------------------------
  const payload = await verifyCookieValue(
    readCookie(request, COOKIE_NAME),
    secret
  );
  if (!payload) return htmlPage(EXPIRED_PAGE, 401);
  const scope = payload.scope;

  // --- /scope.json: handled here, returns the verified scope --------
  if (path === "/scope.json") {
    return new Response(JSON.stringify({ scope }), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
      },
    });
  }

  // --- /note: DEMO stub — acknowledges, never forwards anywhere -----
  if (path === "/note") {
    return new Response(JSON.stringify({ ok: true, demo: true }), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
      },
    });
  }

  // --- Scope enforcement --------------------------------------------
  if (Object.prototype.hasOwnProperty.call(KID_FILES, scope)) {
    const allowed = new Set([
      "/",
      "/index.html",
      "/manifest.json",
      "/scope.json",
      "/" + KID_FILES[scope],
    ]);
    if (!allowed.has(path)) return htmlPage(FORBIDDEN_PAGE, 403);
  } else if (scope !== "parent" && scope !== "owner") {
    return htmlPage(FORBIDDEN_PAGE, 403);
  }

  return context.next();
}
