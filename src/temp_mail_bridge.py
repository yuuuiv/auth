import logging
import secrets
import base64
import json
from typing import Any

import requests
from fastapi import HTTPException

from config import settings


_logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.temp_mail_api_base and settings.temp_mail_admin_auth)


def _api_url(path: str) -> str:
    return f"{settings.temp_mail_api_base.rstrip('/')}/{path.lstrip('/')}"


def _request(method: str, path: str, **kwargs) -> Any:
    if not is_configured():
        raise HTTPException(
            status_code=400,
            detail="未配置 Temp Mail Worker 桥接。请设置 temp_mail_api_base 和 temp_mail_admin_auth。",
        )
    headers = {
        "x-admin-auth": settings.temp_mail_admin_auth,
        "Content-Type": "application/json",
        **kwargs.pop("headers", {}),
    }
    try:
        res = requests.request(
            method,
            _api_url(path),
            headers=headers,
            timeout=20,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Temp Mail Worker 请求失败: {exc}",
        ) from exc

    if res.status_code >= 400:
        detail = res.text[:800] if res.text else res.reason
        raise HTTPException(
            status_code=400,
            detail=f"Temp Mail Worker 返回错误: {res.status_code} {detail}",
        )

    if not res.text:
        return {}
    try:
        return res.json()
    except ValueError:
        return res.text


def find_temp_mail_user(email: str) -> dict[str, Any] | None:
    data = _request(
        "GET",
        "/admin/users",
        params={"limit": 20, "offset": 0, "query": email},
    )
    rows = data.get("results", []) if isinstance(data, dict) else []
    email_lower = email.lower()
    return next(
        (
            row
            for row in rows
            if str(row.get("user_email", "")).lower() == email_lower
        ),
        None,
    )


def sync_temp_mail_user(email: str, password_hash: str | None = None) -> dict[str, Any] | None:
    if not is_configured() or not email:
        return None
    existing = find_temp_mail_user(email)
    if existing:
        return existing

    password = password_hash or secrets.token_hex(32)
    _request(
        "POST",
        "/admin/users",
        json={"email": email, "password": password},
    )
    return find_temp_mail_user(email)


def _random_address_name() -> str:
    words = ["quiet", "swift", "silver", "green", "nova", "pixel", "river", "cloud"]
    animals = ["otter", "fox", "lynx", "panda", "raven", "koala", "mink", "heron"]
    return f"{secrets.choice(words)}-{secrets.choice(animals)}-{secrets.randbelow(9000) + 1000}"


def get_bound_addresses(email: str, create_user: bool = True) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    user = sync_temp_mail_user(email) if create_user else find_temp_mail_user(email)
    if not user:
        return None, []
    data = _request("GET", f"/admin/users/bind_address/{user['id']}")
    return user, data.get("results", []) if isinstance(data, dict) else []


def get_address_jwt(email: str, address_id: int) -> dict[str, Any]:
    _user, addresses = get_bound_addresses(email)
    address_ids = {int(row["id"]) for row in addresses if row.get("id") is not None}
    if address_id not in address_ids:
        raise HTTPException(status_code=403, detail="该邮箱地址不属于当前用户")
    return _request("GET", f"/admin/show_password/{address_id}")


def get_address_forwarding_rules(email: str, address_id: int) -> dict[str, Any]:
    get_address_jwt(email, address_id)
    return _request("GET", f"/admin/address_forwarding_rules/{address_id}")


def save_address_forwarding_rules(email: str, address_id: int, rules: list[dict[str, Any]]) -> dict[str, Any]:
    get_address_jwt(email, address_id)
    return _request(
        "POST",
        f"/admin/address_forwarding_rules/{address_id}",
        json={"rules": rules},
    )


def delete_address_mail(email: str, address_id: int, mail_id: int) -> dict[str, Any]:
    credential = get_address_jwt(email, address_id).get("jwt")
    if not credential:
        raise HTTPException(status_code=400, detail="未获取到邮箱凭证")
    return _request(
        "DELETE",
        f"/api/mails/{mail_id}",
        headers={"x-user-token": credential},
    )


def create_bound_address(email: str, payload: dict[str, Any]) -> dict[str, Any]:
    user = sync_temp_mail_user(email)
    if not user:
        raise HTTPException(status_code=400, detail="Temp Mail 用户同步失败")
    data = _request(
        "POST",
        "/admin/new_address",
        json={
            "name": payload.get("name") or _random_address_name(),
            "domain": payload.get("domain") or "",
            "enablePrefix": payload.get("enablePrefix", True),
            "enableRandomSubdomain": payload.get("enableRandomSubdomain", False),
        },
    )
    address_id = data.get("address_id") if isinstance(data, dict) else None
    if not address_id:
        raise HTTPException(status_code=400, detail="Temp Mail Worker 未返回 address_id")
    _request(
        "POST",
        "/admin/users/bind_address",
        json={"user_id": user["id"], "address_id": address_id},
    )
    return data


def _decode_unverified_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="地址凭证格式无效")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法解析地址凭证") from exc


def bind_verified_address_jwt(email: str, address_jwt: str) -> dict[str, Any]:
    user = sync_temp_mail_user(email)
    if not user:
        raise HTTPException(status_code=400, detail="Temp Mail 用户同步失败")
    _request(
        "POST",
        "/open_api/credential_login",
        json={"credential": address_jwt},
    )
    payload = _decode_unverified_jwt_payload(address_jwt)
    address_id = payload.get("address_id")
    if not address_id:
        raise HTTPException(status_code=400, detail="地址凭证缺少 address_id")
    return _request(
        "POST",
        "/admin/users/bind_address",
        json={"user_id": user["id"], "address_id": address_id},
    )


def list_user_mails(email: str, limit: int, offset: int, address: str = "") -> dict[str, Any]:
    _user, addresses = get_bound_addresses(email)
    allowed_addresses = [row.get("name") or row.get("address") for row in addresses]
    allowed_addresses = [item for item in allowed_addresses if item]
    allowed_set = set(allowed_addresses)
    if address:
        if address not in allowed_set:
            raise HTTPException(status_code=403, detail="该邮箱地址不属于当前用户")
        return _request(
            "GET",
            "/admin/mails",
            params={"limit": limit, "offset": offset, "address": address},
        )

    if not allowed_addresses:
        return {"count": 0, "results": []}

    fetch_limit = min(max(limit + offset, limit), 100)
    all_results: list[dict[str, Any]] = []
    total_count = 0
    for item in allowed_addresses:
        data = _request(
            "GET",
            "/admin/mails",
            params={"limit": fetch_limit, "offset": 0, "address": item},
        )
        if isinstance(data, dict):
            total_count += int(data.get("count") or 0)
            all_results.extend(data.get("results") or [])

    def sort_key(row: dict[str, Any]) -> tuple[str, int]:
        return str(row.get("created_at") or ""), int(row.get("id") or 0)

    all_results.sort(key=sort_key, reverse=True)
    return {
        "count": total_count,
        "results": all_results[offset:offset + limit],
    }


def list_user_sendbox(email: str, limit: int, offset: int, address: str = "") -> dict[str, Any]:
    _user, addresses = get_bound_addresses(email)
    allowed_addresses = [row.get("name") or row.get("address") for row in addresses]
    allowed_addresses = [item for item in allowed_addresses if item]
    if address:
        if address not in set(allowed_addresses):
            raise HTTPException(status_code=403, detail="该邮箱地址不属于当前用户")
        return _request("GET", "/admin/sendbox", params={"limit": limit, "offset": offset, "address": address})
    if not allowed_addresses:
        return {"count": 0, "results": []}

    all_results: list[dict[str, Any]] = []
    total_count = 0
    for item in allowed_addresses:
        data = _request("GET", "/admin/sendbox", params={"limit": min(limit + offset, 100), "offset": 0, "address": item})
        if isinstance(data, dict):
            total_count += int(data.get("count") or 0)
            all_results.extend(data.get("results") or [])
    all_results.sort(key=lambda row: (str(row.get("created_at") or ""), int(row.get("id") or 0)), reverse=True)
    return {"count": total_count, "results": all_results[offset:offset + limit]}


def try_sync_temp_mail_user(email: str, password_hash: str | None = None) -> None:
    try:
        sync_temp_mail_user(email, password_hash)
    except Exception as exc:
        _logger.warning("Failed to sync temp-mail user %s: %s", email, exc)
