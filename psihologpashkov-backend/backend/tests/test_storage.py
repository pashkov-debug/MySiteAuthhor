from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.core.storage import (
    AvatarFileTooLargeError,
    EmptyAvatarFileError,
    InvalidStoragePathError,
    UnsupportedAvatarExtensionError,
    build_avatar_object_name,
    ensure_avatar_storage_dir,
    resolve_avatar_path,
    validate_avatar_filename,
    validate_avatar_size,
)


def make_storage_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_name="Test API",
        app_env="test",
        api_v1_prefix="/api/v1",
        cors_origins="https://psihologpashkov.ru",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        jwt_access_secret="test-access-secret-32-bytes-minimum-value",
        jwt_refresh_secret="test-refresh-secret-32-bytes-minimum-value",
        jwt_algorithm="HS256",
        jwt_access_ttl_minutes=15,
        jwt_refresh_ttl_days=30,
        auth_refresh_cookie_name="refresh_token",
        auth_refresh_cookie_domain=None,
        auth_refresh_cookie_path="/api/v1/auth",
        auth_refresh_cookie_secure=False,
        auth_refresh_cookie_samesite="lax",
        cache_default_ttl_seconds=300,
        uploads_root=str(tmp_path / "uploads"),
        avatar_upload_subdir="avatars",
        avatar_max_size_bytes=1024,
        avatar_allowed_extensions=".jpg,.jpeg,.png,.webp",
        enable_openapi=True,
    )


def test_ensure_avatar_storage_dir_creates_directory(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    avatar_dir = ensure_avatar_storage_dir(settings)

    assert avatar_dir.is_dir()
    assert avatar_dir == tmp_path / "uploads" / "avatars"


def test_validate_avatar_filename_accepts_supported_extension(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    assert validate_avatar_filename("avatar.PNG", settings) == ".png"


def test_validate_avatar_filename_rejects_unsupported_extension(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    with pytest.raises(UnsupportedAvatarExtensionError):
        validate_avatar_filename("avatar.gif", settings)


def test_validate_avatar_size_accepts_valid_size(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    validate_avatar_size(512, settings)


def test_validate_avatar_size_rejects_empty_file(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    with pytest.raises(EmptyAvatarFileError):
        validate_avatar_size(0, settings)


def test_validate_avatar_size_rejects_too_large_file(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    with pytest.raises(AvatarFileTooLargeError):
        validate_avatar_size(2048, settings)


def test_build_avatar_object_name_uses_user_directory_and_safe_random_name(
    tmp_path: Path,
) -> None:
    settings = make_storage_settings(tmp_path)
    user_id = uuid4()

    object_name = build_avatar_object_name(user_id, "../../avatar.jpg", settings)

    assert object_name.startswith(f"{user_id}/")
    assert object_name.endswith(".jpg")
    assert ".." not in object_name


def test_resolve_avatar_path_rejects_path_traversal(tmp_path: Path) -> None:
    settings = make_storage_settings(tmp_path)

    with pytest.raises(InvalidStoragePathError):
        resolve_avatar_path("../secret.txt", settings)
