import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

from .models import BlacklistedToken, User
from .utils import get_role

ACCESS = "access"
REFRESH = "refresh"
ALGORITHM = "HS256"


class TokenError(Exception):
    pass


def token_settings(token_type):
    if token_type == ACCESS:
        return settings.JWT_SECRET_KEY, timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES)
    return settings.JWT_REFRESH_SECRET_KEY, timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS)


def create_token(user, token_type):
    secret, lifetime = token_settings(token_type)
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user.pk,
        "username": user.username,
        "role": get_role(user),
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_token_pair(user):
    return {
        "access": create_token(user, ACCESS),
        "refresh": create_token(user, REFRESH),
        "token_type": "Bearer",
        "access_expires_in_minutes": settings.ACCESS_TOKEN_LIFETIME_MINUTES,
    }


def decode_token(token, token_type):
    secret, _ = token_settings(token_type)
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError(f"The {token_type} token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise TokenError(f"The {token_type} token is invalid.")

    if payload.get("type") != token_type:
        raise TokenError(f"Please send a {token_type} token.")
    if BlacklistedToken.objects.filter(jti=payload["jti"]).exists():
        raise TokenError(f"The {token_type} token has been logged out.")
    return payload


def get_user_from_payload(payload):
    user = User.objects.filter(pk=payload["user_id"]).first()
    if user is None or not user.is_active:
        raise TokenError("The user for this token no longer exists or is inactive.")
    return user


def blacklist_token(payload, user):
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    BlacklistedToken.objects.get_or_create(jti=payload["jti"], defaults={"user": user, "expires_at": expires_at})
