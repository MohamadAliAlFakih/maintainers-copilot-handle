"""JWT strategy factory — signing key comes from Vault at startup."""
from fastapi_users.authentication import JWTStrategy


def build_jwt_strategy(signing_key: str, lifetime_seconds: int = 900) -> JWTStrategy:
    """Builds a JWT strategy with the Vault-loaded signing key. Default lifetime 15 min."""
    return JWTStrategy(secret=signing_key, lifetime_seconds=lifetime_seconds)
