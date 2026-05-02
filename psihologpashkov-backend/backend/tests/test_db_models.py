from app.db import models
from app.db.base import Base


def test_user_model_registered_in_metadata() -> None:
    assert models.User.__tablename__ == "users"
    assert "users" in Base.metadata.tables


def test_refresh_session_model_registered_in_metadata() -> None:
    assert models.RefreshSession.__tablename__ == "refresh_sessions"
    assert "refresh_sessions" in Base.metadata.tables


def test_user_table_has_required_columns() -> None:
    table = Base.metadata.tables["users"]

    assert {"id", "email", "password_hash", "is_active", "is_superuser"}.issubset(
        table.columns.keys()
    )


def test_refresh_session_table_has_required_columns() -> None:
    table = Base.metadata.tables["refresh_sessions"]

    assert {"id", "user_id", "jti_hash", "expires_at", "revoked_at"}.issubset(table.columns.keys())


def test_user_table_has_avatar_path_column() -> None:
    table = Base.metadata.tables["users"]

    assert "avatar_path" in table.columns


def test_user_table_has_email_verified_at_column() -> None:
    table = Base.metadata.tables["users"]

    assert "email_verified_at" in table.columns


def test_email_verification_token_model_registered_in_metadata() -> None:
    assert models.EmailVerificationToken.__tablename__ == "email_verification_tokens"
    assert "email_verification_tokens" in Base.metadata.tables


def test_email_verification_token_table_has_required_columns() -> None:
    table = Base.metadata.tables["email_verification_tokens"]

    assert {"id", "user_id", "token_hash", "expires_at", "used_at"}.issubset(
        table.columns.keys()
    )
