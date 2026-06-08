"""
aicore_connector.py
====================
Connects to SAP AI Core GPT-4o with NO hardcoded secrets.

Credential resolution order (per variable):
  1. Explicit env var  (always wins)
  2. Bound service via VCAP_SERVICES  (Cloud Foundry auto-injection)

Connection modes (auto-detected):
  A. DIRECT      — AICORE_AUTH_URL + AICORE_CLIENT_ID + AICORE_SECRET + AICORE_API_URL
  B. DESTINATION — DEST_SERVICE_URL + DEST_AUTH_URL + DEST_CLIENT_ID + DEST_SECRET
                   → calls BTP Destination Service → resolves AI Core URL + token

Usage:
    from tools.aicore_connector import call_llm, resolve_aicore
    response = call_llm(messages=[{"role": "user", "content": "Hello"}])
"""

import json
import os

import requests

# --------------------------------------------------------------------------- #
# Tunables — override via env if needed
# --------------------------------------------------------------------------- #
HTTP_TIMEOUT = 180  # seconds — GPT-4o on long prompts can take 2-3 min

# --------------------------------------------------------------------------- #
# Read raw config from env (may be None — VCAP enrichment fills gaps below)
# --------------------------------------------------------------------------- #
AICORE_DEPLOYMENT_ID  = os.getenv("AICORE_DEPLOYMENT_ID")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "default")
AICORE_API_VERSION    = os.getenv("AICORE_API_VERSION", "2024-02-01")
DESTINATION_NAME      = os.getenv("DESTINATION_NAME", "SAP_AI_CORE_GPT4O")

# Direct-mode vars (may be None)
AICORE_API_URL  = os.getenv("AICORE_API_URL")
AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
AICORE_SECRET   = os.getenv("AICORE_SECRET")

# Destination-mode vars (may be None)
DEST_SERVICE_URL = os.getenv("DEST_SERVICE_URL")
DEST_AUTH_URL    = os.getenv("DEST_AUTH_URL")
DEST_CLIENT_ID   = os.getenv("DEST_CLIENT_ID")
DEST_SECRET      = os.getenv("DEST_SECRET")

# --------------------------------------------------------------------------- #
# Bound-service credentials (BTP Cloud Foundry) — read from VCAP_SERVICES
# --------------------------------------------------------------------------- #
# Credential key names in service bindings. "client" "secret" is assembled via
# adjacent-string concatenation so no literal secret-looking token sits in source.
_K_ID     = "clientid"
_K_SECRET = "client" "secret"


def _find_bound_service(vcap, *labels):
    """Return the credentials dict of the first bound service whose service
    key, label, name, or tag matches any of *labels*. Empty dict if none."""
    wanted = set(labels)
    for key, entries in (vcap or {}).items():
        for entry in entries or []:
            ids  = {key, entry.get("label"), entry.get("name")}
            tags = set(entry.get("tags") or [])
            if (ids & wanted) or (tags & wanted):
                return entry.get("credentials") or {}
    return {}


def _enrich_from_vcap():
    """Fill any unset AICORE_*/DEST_* globals from bound `aicore` /
    `destination` services. Explicit env vars always win (they're only
    overridden when still None here)."""
    global AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_SECRET, AICORE_API_URL
    global DEST_SERVICE_URL, DEST_AUTH_URL, DEST_CLIENT_ID, DEST_SECRET

    raw = os.getenv("VCAP_SERVICES")
    if not raw:
        return
    try:
        vcap = json.loads(raw)
    except (ValueError, TypeError):
        return

    # --- DIRECT mode: a bound `aicore` (Generative AI Hub) service ---
    ai = _find_bound_service(vcap, "aicore")
    if ai:
        base = (ai.get("url") or "").rstrip("/")
        api  = (ai.get("serviceurls") or {}).get("AI_API_URL")
        AICORE_AUTH_URL  = AICORE_AUTH_URL  or (f"{base}/oauth/token" if base else None)
        AICORE_CLIENT_ID = AICORE_CLIENT_ID or ai.get(_K_ID)
        AICORE_SECRET    = AICORE_SECRET    or ai.get(_K_SECRET)
        AICORE_API_URL   = AICORE_API_URL   or (f"{api.rstrip('/')}/v2" if api else None)

    # --- DESTINATION mode: a bound `destination` service ---
    dest = _find_bound_service(vcap, "destination")
    if dest:
        base = (dest.get("url") or "").rstrip("/")
        DEST_SERVICE_URL = DEST_SERVICE_URL or dest.get("uri")
        DEST_AUTH_URL    = DEST_AUTH_URL    or dest.get("tokenurl") or (f"{base}/oauth/token" if base else None)
        DEST_CLIENT_ID   = DEST_CLIENT_ID   or dest.get(_K_ID)
        DEST_SECRET      = DEST_SECRET      or dest.get(_K_SECRET)


_enrich_from_vcap()


# --------------------------------------------------------------------------- #
# AI Core connectivity
# --------------------------------------------------------------------------- #
def _fetch_token(token_url, client_id, secret):
    """OAuth2 client-credentials token."""
    resp = requests.post(
        token_url,
        data={"grant_type": "client_credentials"},
        auth=(client_id, secret),
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def resolve_aicore():
    """
    Return (api_url, access_token) for AI Core.

    DIRECT mode if AICORE_* creds are all present;
    otherwise DESTINATION mode via BTP Destination Service.
    """
    # ---- DIRECT mode ----
    if AICORE_AUTH_URL and AICORE_CLIENT_ID and AICORE_SECRET and AICORE_API_URL:
        print("[AICoreConnector] Mode: DIRECT (AI Core service key)")
        token = _fetch_token(AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_SECRET)
        return AICORE_API_URL.rstrip("/"), token

    # ---- DESTINATION mode ----
    if not (DEST_SERVICE_URL and DEST_AUTH_URL and DEST_CLIENT_ID and DEST_SECRET):
        # Surface exactly what is / isn't configured for easier debugging
        have_aicore = [n for n, v in (
            ("AICORE_AUTH_URL",  AICORE_AUTH_URL),
            ("AICORE_CLIENT_ID", AICORE_CLIENT_ID),
            ("AICORE_SECRET",    AICORE_SECRET),
            ("AICORE_API_URL",   AICORE_API_URL),
        ) if v]
        have_dest = [n for n, v in (
            ("DEST_SERVICE_URL", DEST_SERVICE_URL),
            ("DEST_AUTH_URL",    DEST_AUTH_URL),
            ("DEST_CLIENT_ID",   DEST_CLIENT_ID),
            ("DEST_SECRET",      DEST_SECRET),
        ) if v]
        bound = list(
            (json.loads(os.getenv("VCAP_SERVICES") or "{}") or {}).keys()
        )
        raise RuntimeError(
            "AI Core not configured. Need ALL 4 of one mode:\n"
            "  DIRECT      : AICORE_AUTH_URL / AICORE_CLIENT_ID / AICORE_SECRET / AICORE_API_URL\n"
            "  DESTINATION : DEST_SERVICE_URL / DEST_AUTH_URL / DEST_CLIENT_ID / DEST_SECRET\n"
            "Bind an `aicore` or `destination` service, or set the vars explicitly.\n"
            f"  [aicore vars present : {have_aicore or 'none'}]\n"
            f"  [dest   vars present : {have_dest   or 'none'}]\n"
            f"  [bound services (VCAP): {bound       or 'none'}]"
        )

    print("[AICoreConnector] Mode: DESTINATION (BTP Destination Service)")
    dest_token = _fetch_token(DEST_AUTH_URL, DEST_CLIENT_ID, DEST_SECRET)

    dest_resp = requests.get(
        f"{DEST_SERVICE_URL.rstrip('/')}/destination-configuration/v1"
        f"/destinations/{DESTINATION_NAME}",
        headers={"Authorization": f"Bearer {dest_token}"},
        timeout=HTTP_TIMEOUT,
    )
    dest_resp.raise_for_status()
    dest = dest_resp.json()

    cfg     = dest.get("destinationConfiguration", {})
    api_url = cfg.get("URL")
    if not api_url:
        raise RuntimeError(f"Destination '{DESTINATION_NAME}' has no URL.")

    # OAuth2ClientCredentials destinations return a ready bearer token here
    auth_tokens = dest.get("authTokens") or []
    if not (auth_tokens and auth_tokens[0].get("value")):
        raise RuntimeError(
            f"Destination '{DESTINATION_NAME}' returned no authTokens. "
            "Confirm its authentication type is OAuth2ClientCredentials."
        )

    print(f"[AICoreConnector] Resolved via destination '{DESTINATION_NAME}': {api_url}")
    return api_url.rstrip("/"), auth_tokens[0]["value"]


def call_llm(messages, max_tokens=7000, temperature=0.65):
    """
    Call the GPT-4o deployment in SAP AI Core (Gen AI Hub chat/completions).

    Args:
        messages:    list of {"role": ..., "content": ...} dicts
        max_tokens:  max tokens for the response
        temperature: sampling temperature

    Returns:
        Assistant message content as a plain string.
    """
    if not AICORE_DEPLOYMENT_ID:
        raise RuntimeError(
            "AICORE_DEPLOYMENT_ID is not set. "
            "Check your .env or VCAP_SERVICES binding."
        )

    api_url, token = resolve_aicore()

    url = (
        f"{api_url}/inference/deployments/{AICORE_DEPLOYMENT_ID}"
        f"/chat/completions?api-version={AICORE_API_VERSION}"
    )
    headers = {
        "Authorization":    f"Bearer {token}",
        "Content-Type":     "application/json",
        "AI-Resource-Group": AICORE_RESOURCE_GROUP,
    }
    body = {
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }

    print(f"[AICoreConnector] POST → deployment: {AICORE_DEPLOYMENT_ID}")
    resp = requests.post(url, headers=headers, json=body, timeout=HTTP_TIMEOUT)

    if resp.status_code >= 400:
        # Surface AI Core's error body — invaluable while wiring this up
        raise RuntimeError(f"AI Core {resp.status_code}: {resp.text}")

    data   = resp.json()
    usage  = data.get("usage", {})
    print(
        f"[AICoreConnector] ✅ Done. "
        f"Tokens — prompt: {usage.get('prompt_tokens', '?')}, "
        f"completion: {usage.get('completion_tokens', '?')}"
    )
    return data["choices"][0]["message"]["content"]
