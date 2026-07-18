import requests
import logging

from fastapi import HTTPException

from config import settings


URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
_logger = logging.getLogger(__name__)


class CloudFlareTurnstile:

    @classmethod
    def check(cls, token: str, remote_ip: str = "", expected_action: str = "") -> bool:
        if not settings.cf_turnstile_secret_key:
            return True
        if not token or len(token) > 2048:
            raise HTTPException(status_code=400, detail="Turnstile verification is required")

        payload = {
            "secret": settings.cf_turnstile_secret_key,
            "response": token,
        }
        if remote_ip:
            payload["remoteip"] = remote_ip
        try:
            response = requests.post(URL, json=payload, headers={
                "Content-Type": "application/json",
            }, timeout=10)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            _logger.warning("Turnstile Siteverify request failed: %s", exc)
            raise HTTPException(
                status_code=503, detail="Turnstile verification service is temporarily unavailable"
            ) from exc

        if not result.get("success"):
            error_codes = result.get("error-codes") or []
            _logger.info("Turnstile rejected a token: %s", ",".join(map(str, error_codes)))
            raise HTTPException(status_code=400, detail="Turnstile verification failed; please retry")

        hostname = str(result.get("hostname") or "").lower().rstrip(".")
        allowed_hostnames = settings.get_turnstile_allowed_hostnames()
        if allowed_hostnames and not any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in allowed_hostnames
        ):
            _logger.warning("Turnstile hostname mismatch: %s", hostname or "(missing)")
            raise HTTPException(status_code=400, detail="Turnstile hostname verification failed")

        if expected_action and result.get("action") != expected_action:
            _logger.warning("Turnstile action mismatch: expected=%s received=%s", expected_action, result.get("action"))
            raise HTTPException(status_code=400, detail="Turnstile action verification failed")

        return True
