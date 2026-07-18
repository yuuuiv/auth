"""Password hashing helpers used by the auth service."""

import base64
import hashlib
import hmac
import os


_SALT_BYTES = 16
_KEY_BYTES = 64
# 16 MiB working set is a safer baseline for Vercel/Python serverless
# runtimes while remaining materially stronger than the legacy SHA-256 value.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_BYTES,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encode(salt)}${encode(digest)}"


def verify_password(stored: str, password: str) -> bool:
    if not isinstance(stored, str) or not isinstance(password, str):
        return False
    if stored.startswith("scrypt$"):
        try:
            _, n, r, p, salt_value, digest_value = stored.split("$", 5)
            decode = lambda value: base64.urlsafe_b64decode(value + "===")
            expected = decode(digest_value)
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=decode(salt_value),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(expected),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    # Legacy accounts stored SHA-256(password) from the old browser client.
    legacy_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(stored, legacy_sha256) or hmac.compare_digest(stored, password)


def is_legacy_hash(stored: str) -> bool:
    return bool(stored) and not stored.startswith("scrypt$")
