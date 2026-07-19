import logging
import secrets
import time
from typing import Optional

import requests
from fastapi import HTTPException

from config import settings

from .base import TokenClientBase


_logger = logging.getLogger(__name__)


class UpstashTokenClient(TokenClientBase):
    _type = "upstash"

    @classmethod
    def _headers(cls) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.upstash_api_token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def _post(cls, path: str, command):
        return requests.post(
            f"{settings.upstash_api_url.rstrip('/')}{path}",
            json=command,
            headers=cls._headers(),
            timeout=10,
        )

    @classmethod
    def store_token(cls, key: str, token: str, expire_seconds: int) -> None:
        try:
            response = cls._post("", ["SET", key, token, "EX", int(expire_seconds)])
            response.raise_for_status()
            if response.json().get("result") == "OK":
                return
        except Exception as exc:
            _logger.error("Store token failed: %s", exc)
        raise HTTPException(status_code=400, detail="Store token failed")

    @classmethod
    def get_token(cls, key: str) -> Optional[str]:
        try:
            response = cls._post("", ["GET", key])
            if response.status_code != 200:
                _logger.error("Get token failed: %s", response.status_code)
                return None
            return response.json().get("result")
        except Exception as exc:
            _logger.error("Get token failed: %s", exc)
        return None

    @classmethod
    def check_rate_limit(cls, key: str, time_window_seconds: int, max_requests: int) -> None:
        current_timestamp = int(time.time())
        commands = [
            ["ZREMRANGEBYSCORE", key, "-inf", current_timestamp - time_window_seconds],
            ["ZADD", key, current_timestamp, f"{current_timestamp}:{secrets.token_hex(4)}"],
            ["EXPIRE", key, int(time_window_seconds)],
            ["ZCARD", key],
        ]
        try:
            response = cls._post("/multi-exec", commands)
            response.raise_for_status()
            results = response.json()
            if not isinstance(results, list) or len(results) != 4 or not all(
                isinstance(item, dict) and "result" in item for item in results
            ):
                raise HTTPException(status_code=400, detail="Can't get rate limit result")
            request_count = results[-1].get("result", 0)
            if int(request_count or 0) > max_requests:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except HTTPException:
            raise
        except Exception as exc:
            _logger.error("Rate limit failed: %s", exc)
            raise HTTPException(status_code=400, detail="Rate limit failed") from exc
