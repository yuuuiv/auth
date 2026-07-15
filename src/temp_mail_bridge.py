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
        # /api/* is protected by the Worker JWT middleware, which reads the
        # standard Bearer credential. x-user-token is only used by /user_api.
        headers={"Authorization": f"Bearer {credential}"},
    )


def send_address_mail(email: str, address_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    credential = get_address_jwt(email, address_id).get("jwt")
    if not credential:
        raise HTTPException(status_code=400, detail="未获取到邮箱凭证")
    return _request(
        "POST",
        "/api/send_mail",
        json=payload,
        headers={"Authorization": f"Bearer {credential}"},
    )


def _ensure_worker_user_address_limit() -> None:
    target = max(0, int(settings.temp_mail_user_max_address_count or 0))
    if target <= 0:
        return
    current = _request("GET", "/admin/user_settings")
    if not isinstance(current, dict):
        return
    current_limit = int(current.get("maxAddressCount") or 0)
    # Worker uses 0 as unlimited. Never replace an unlimited or already higher
    # administrator setting with the bridge default.
    if current_limit == 0 or current_limit >= target:
        return
    _request(
        "POST",
        "/admin/user_settings",
        json={**current, "maxAddressCount": target},
    )


def _ensure_account_send_balance(address_jwt: str, address: str) -> None:
    balance = max(0, int(settings.temp_mail_account_send_balance or 0))
    if not address_jwt or not address or balance <= 0:
        return
    try:
        # This creates the sender row when it does not exist. The admin endpoint
        # can then update the concrete row to the account-specific balance.
        _request(
            "POST",
            "/api/request_send_mail_access",
            headers={"Authorization": f"Bearer {address_jwt}"},
        )
        result = _request(
            "GET",
            "/admin/address_sender",
            params={"limit": 20, "offset": 0, "address": address},
        )
        rows = result.get("results", []) if isinstance(result, dict) else []
        sender = next((row for row in rows if row.get("id") is not None), None)
        if not sender:
            raise RuntimeError("Worker 未创建 address_sender 记录")
        current_balance = max(0, int(sender.get("balance") or 0))
        current_enabled = bool(int(sender.get("enabled") or 0))
        if current_enabled and current_balance >= balance:
            return
        _request(
            "POST",
            "/admin/address_sender",
            json={
                "address_id": sender["id"],
                "address": address,
                "enabled": True,
                "balance": max(current_balance, balance),
                # Initial account quota is infrastructure setup, not a later
                # administrator change. Keep this first update out of inboxes.
                "notify": False,
            },
        )
    except Exception as exc:
        _logger.warning("Failed to initialize account send balance for %s: %s", address, exc)


def create_bound_address(email: str, payload: dict[str, Any]) -> dict[str, Any]:
    user = sync_temp_mail_user(email)
    if not user:
        raise HTTPException(status_code=400, detail="Temp Mail 用户同步失败")
    _ensure_worker_user_address_limit()
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
    try:
        _request(
            "POST",
            "/admin/users/bind_address",
            json={"user_id": user["id"], "address_id": address_id},
        )
    except Exception:
        # /admin/new_address and /admin/users/bind_address are separate Worker
        # operations. Roll the first one back if binding fails (for example,
        # when the user's address limit is reached) to avoid orphan addresses.
        try:
            _request("DELETE", f"/admin/delete_address/{address_id}")
        except Exception as cleanup_exc:
            _logger.warning("Failed to remove unbound address %s: %s", address_id, cleanup_exc)
        raise
    _ensure_account_send_balance(
        str(data.get("jwt") or ""),
        str(data.get("address") or ""),
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
    _ensure_worker_user_address_limit()
    _request(
        "POST",
        "/open_api/credential_login",
        json={"credential": address_jwt},
    )
    payload = _decode_unverified_jwt_payload(address_jwt)
    address_id = payload.get("address_id")
    if not address_id:
        raise HTTPException(status_code=400, detail="地址凭证缺少 address_id")
    _, bound_addresses = get_bound_addresses(email)
    already_bound = any(
        int(row.get("id") or 0) == int(address_id)
        for row in bound_addresses
    )
    result = _request(
        "POST",
        "/admin/users/bind_address",
        json={"user_id": user["id"], "address_id": address_id},
    )
    if not already_bound:
        _ensure_account_send_balance(address_jwt, str(payload.get("address") or ""))
    return result


def list_user_mails(email: str, limit: int, offset: int, address: str = "") -> dict[str, Any]:
    _user, addresses = get_bound_addresses(email)
    address_rows = [
        row for row in addresses
        if row.get("id") is not None and (row.get("name") or row.get("address"))
    ]
    allowed_addresses = [row.get("name") or row.get("address") for row in address_rows]
    rows_by_address = {
        row.get("name") or row.get("address"): row
        for row in address_rows
    }

    def list_parsed_mail(row: dict[str, Any], page_limit: int, page_offset: int) -> dict[str, Any]:
        """Use the address JWT and the Worker's parsed endpoint.

        /admin/mails returns complete raw RFC822 messages.  Returning those to
        the browser forced it to parse every message before a mailbox switch
        could render.  /api/parsed_mails keeps that work at the Worker and
        returns the small, already parsed representation instead.
        """
        # ``row`` came from get_bound_addresses above, so ownership has already
        # been checked. Avoid calling get_address_jwt here: it would fetch the
        # same binding list once more for every mailbox switch.
        credential = _request("GET", f"/admin/show_password/{int(row['id'])}").get("jwt")
        if not credential:
            raise HTTPException(status_code=400, detail="未获取到邮箱凭证")
        return _request(
            "GET",
            "/api/parsed_mails",
            params={"limit": page_limit, "offset": page_offset},
            headers={"Authorization": f"Bearer {credential}"},
        )

    if address:
        row = rows_by_address.get(address)
        if not row:
            raise HTTPException(status_code=403, detail="该邮箱地址不属于当前用户")
        return list_parsed_mail(row, limit, offset)

    if not allowed_addresses:
        return {"count": 0, "results": []}

    fetch_limit = min(max(limit + offset, limit), 100)
    all_results: list[dict[str, Any]] = []
    total_count = 0
    for row in address_rows:
        data = list_parsed_mail(row, fetch_limit, 0)
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
