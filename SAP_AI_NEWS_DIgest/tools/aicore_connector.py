import os
import requests
from datetime import datetime, timedelta


class AICoreDestinationConnector:
    """
    Connects to SAP AI Core GPT-4o via BTP Destination Service
    or directly via AI Core service key credentials.

    Priority:
      1. BTP Destination Service  (if BTP_DESTINATION_URL is set)
      2. Direct AI Core credentials (fallback via AICORE_* env vars)

    Handles OAuth2 token fetching, caching, and refresh automatically.
    """

    def __init__(self):
        self._token_cache = {}
        self.use_destination = bool(os.getenv("BTP_DESTINATION_URL"))

        if self.use_destination:
            print("[AICoreConnector] Mode: BTP Destination Service")
            self._dest_url         = os.getenv("BTP_DESTINATION_URL", "").rstrip("/")
            self._dest_name        = os.getenv("BTP_DESTINATION_NAME")
            self._dest_client_id   = os.getenv("BTP_UAACLIENTID")
            self._dest_client_secret = os.getenv("BTP_UAACLIENTSECRET")
            self._dest_token_url   = os.getenv("BTP_UAATOKENURL")
        else:
            print("[AICoreConnector] Mode: Direct AI Core credentials")
            self._aicore_auth_url      = os.getenv("AICORE_AUTH_URL")
            self._aicore_client_id     = os.getenv("AICORE_CLIENT_ID")
            self._aicore_client_secret = os.getenv("AICORE_CLIENT_SECRET")
            self._aicore_base_url      = os.getenv("AICORE_BASE_URL", "").rstrip("/")
            self._aicore_resource_group = os.getenv("AICORE_RESOURCE_GROUP", "default")
            self._aicore_deployment_id  = os.getenv("AICORE_DEPLOYMENT_ID")

    # ──────────────────────────────────────────────────────────
    # TOKEN MANAGEMENT
    # ──────────────────────────────────────────────────────────

    def _get_oauth_token(self, token_url: str, client_id: str, client_secret: str) -> str:
        """
        Fetch OAuth2 client_credentials token.
        Caches token and reuses until 5 minutes before expiry.
        """
        cache_key = f"{token_url}::{client_id}"

        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if datetime.now() < cached["expires_at"]:
                print(f"[AICoreConnector] Using cached token for {client_id[:8]}...")
                return cached["token"]

        print(f"[AICoreConnector] Fetching new OAuth token from {token_url}")
        response = requests.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))

        self._token_cache[cache_key] = {
            "token": token,
            "expires_at": datetime.now() + timedelta(seconds=expires_in - 300)
        }
        print(f"[AICoreConnector] Token obtained. Expires in {expires_in}s")
        return token

    # ──────────────────────────────────────────────────────────
    # DESTINATION SERVICE PATH
    # ──────────────────────────────────────────────────────────

    def _resolve_via_destination(self) -> dict:
        """
        Calls BTP Destination Service API to resolve AI Core connection details.

        Flow:
          1. Get Destination Service OAuth token
          2. Call /destination-configuration/v1/destinations/{name}
          3. Extract AI Core URL, token, resource group, deployment ID
          4. If destination doesn't return a token, fetch AI Core token separately

        Returns dict: { base_url, token, resource_group, deployment_id }
        """
        # Step 1: Authenticate with Destination Service
        dest_token = self._get_oauth_token(
            self._dest_token_url,
            self._dest_client_id,
            self._dest_client_secret
        )

        # Step 2: Fetch destination config
        dest_api_url = (
            f"{self._dest_url}"
            f"/destination-configuration/v1/destinations/{self._dest_name}"
        )
        print(f"[AICoreConnector] Fetching destination: {self._dest_name}")

        dest_response = requests.get(
            dest_api_url,
            headers={"Authorization": f"Bearer {dest_token}"},
            timeout=15
        )
        dest_response.raise_for_status()
        dest_data = dest_response.json()

        # Step 3: Parse destination config
        dest_config  = dest_data.get("destinationConfiguration", {})
        auth_tokens  = dest_data.get("authTokens", [{}])

        aicore_url       = dest_config.get("URL", "").rstrip("/")
        resource_group   = dest_config.get("AI-Resource-Group", "default")
        deployment_id    = dest_config.get("DeploymentID", "")

        # Try to use token provided by Destination Service first
        aicore_token = auth_tokens[0].get("value", "") if auth_tokens else ""

        # Fallback: fetch AI Core token ourselves if destination didn't provide one
        if not aicore_token:
            print("[AICoreConnector] Destination did not return token — fetching directly")
            ai_auth_url     = dest_config.get("tokenServiceURL", "")
            ai_client_id    = dest_config.get("clientId", "")
            ai_client_secret = dest_config.get("clientSecret", "")

            if ai_auth_url and ai_client_id:
                aicore_token = self._get_oauth_token(
                    ai_auth_url, ai_client_id, ai_client_secret
                )
            else:
                raise ValueError(
                    "Could not obtain AI Core token from Destination Service "
                    "or destination config. Check BTP destination properties."
                )

        print(f"[AICoreConnector] Resolved via Destination: {aicore_url}, deployment: {deployment_id}")
        return {
            "base_url": aicore_url,
            "token": aicore_token,
            "resource_group": resource_group,
            "deployment_id": deployment_id
        }

    # ──────────────────────────────────────────────────────────
    # DIRECT CREDENTIAL PATH
    # ──────────────────────────────────────────────────────────

    def _resolve_direct(self) -> dict:
        """
        Uses AI Core service key credentials directly.
        No BTP Destination Service involved.
        Suitable for local dev and testing.
        """
        token = self._get_oauth_token(
            self._aicore_auth_url,
            self._aicore_client_id,
            self._aicore_client_secret
        )
        print(f"[AICoreConnector] Direct mode: {self._aicore_base_url}, deployment: {self._aicore_deployment_id}")
        return {
            "base_url": self._aicore_base_url,
            "token": token,
            "resource_group": self._aicore_resource_group,
            "deployment_id": self._aicore_deployment_id
        }

    # ──────────────────────────────────────────────────────────
    # CHAT COMPLETION
    # ──────────────────────────────────────────────────────────

    def chat_completion(
        self,
        messages: list,
        max_tokens: int = 7000,
        temperature: float = 0.65
    ) -> str:
        """
        Calls SAP AI Core GPT-4o chat completions endpoint.

        Endpoint pattern:
          {base_url}/v2/inference/deployments/{deployment_id}/chat/completions

        Args:
            messages:    List of {"role": ..., "content": ...} dicts
            max_tokens:  Max tokens for the response
            temperature: Sampling temperature

        Returns:
            Assistant message content as a plain string
        """
        conn = (
            self._resolve_via_destination()
            if self.use_destination
            else self._resolve_direct()
        )

        endpoint = (
            f"{conn['base_url']}/v2/inference/deployments"
            f"/{conn['deployment_id']}/chat/completions?api-version=2024-02-01"
        )

        headers = {
            "Authorization": f"Bearer {conn['token']}",
            "Content-Type":  "application/json",
            "AI-Resource-Group": conn["resource_group"]
        }

        payload = {
            "model":       "gpt-4o",
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature
        }

        print(f"[AICoreConnector] → POST {endpoint}")

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=180   # GPT-4o on long prompts can take 2–3 min
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"SAP AI Core call failed [{response.status_code}]: {response.text}"
            )

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        usage   = result.get("usage", {})
        print(
            f"[AICoreConnector] ✅ Response received. "
            f"Tokens — prompt: {usage.get('prompt_tokens', '?')}, "
            f"completion: {usage.get('completion_tokens', '?')}"
        )
        return content
