import json
import time
import base64
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth

class TokenManager:
    def __init__(
        self,
        auth_url,
        revoke_url,
        client_id,
        client_secret,
        token_file="/var/run/nsp_token.json",
        refresh_before=300,
        verify_ssl=False,
    ):
        self.auth_url = auth_url
        self.revoke_url = revoke_url
        self.client_id = client_id
        self.client_secret = client_secret

        self.token_file = Path(token_file)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        self.refresh_before = refresh_before
        self.verify_ssl = verify_ssl

    # -------------------------
    # Helpers
    # -------------------------

    def _now(self):
        return int(time.time())

    def _save_tokens(self, data: dict):
        if not isinstance(data, dict) or "access_token" not in data:
            raise RuntimeError("❌ Invalid JSON from auth server")

        tmp = self.token_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.chmod(0o600)
        tmp.replace(self.token_file)

    def _load_tokens(self):
        if not self.token_file.exists():
            return None
        return json.loads(self.token_file.read_text())

    def _decode_exp(self, token: str):
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded).get("exp")
        except Exception:
            return None

    # -------------------------
    # Auth logic
    # -------------------------

    def _get_token(self):
        print("🔐 Getting new token...")
        r = requests.post(
            self.auth_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            json={"grant_type": "client_credentials"},
            verify=self.verify_ssl,
        )
        r.raise_for_status()
        self._save_tokens(r.json())

    def _refresh_token(self):
        tokens = self._load_tokens()
        if not tokens:
            return False

        refresh = tokens.get("refresh_token")
        if not refresh:
            return False

        print("🔁 Refreshing token...")
        r = requests.post(
            self.auth_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
            },
            verify=self.verify_ssl,
        )

        if r.status_code != 200:
            return False

        self._save_tokens(r.json())
        return True

    def ensure_token(self):
        tokens = self._load_tokens()

        if not tokens:
            self._get_token()
            return

        token = tokens.get("access_token")
        exp = self._decode_exp(token)

        if not isinstance(exp, int) or (exp - self._now()) < self.refresh_before:
            if not self._refresh_token():
                self._get_token()

    def get_access_token(self):
        self.ensure_token()
        return self._load_tokens()["access_token"]

    def get_auth_header(self):
        return {
            "Authorization": f"Bearer {self.get_access_token()}"
        }

    # -------------------------
    # Revoke
    # -------------------------

    def revoke(self):
        tokens = self._load_tokens()
        if not tokens:
            return

        token = tokens.get("access_token")
        if not token:
            return

        print("🛑 Revoking token...")
        requests.post(
            self.revoke_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "token": token,
                "token_type_hint": "access_token",
            },
            verify=self.verify_ssl,
        )

        self.token_file.unlink(missing_ok=True)
        print("✅ Token revoked")
