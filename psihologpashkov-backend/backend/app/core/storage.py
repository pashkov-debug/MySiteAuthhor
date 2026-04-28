from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import Settings, get_settings


class StorageError(Exception):
    pass


class InvalidStoragePathError(StorageError):
    pass


class UnsupportedAvatarExtensionError(StorageError):
    pass


class AvatarFileTooLargeError(StorageError):
    pass


class EmptyAvatarFileError(StorageError):
    pass


def get_avatar_storage_dir(settings: Settings | None = None) -> Path:
    app_settings = settings or get_settings()

    return Path(app_settings.uploads_root) / app_settings.avatar_upload_subdir


def ensure_avatar_storage_dir(settings: Settings | None = None) -> Path:
    avatar_dir = get_avatar_storage_dir(settings)
    avatar_dir.mkdir(parents=True, exist_ok=True)

    return avatar_dir


def validate_avatar_filename(
    filename: str,
    settings: Settings | None = None,
) -> str:
    if not filename or not filename.strip():
        raise UnsupportedAvatarExtensionError("Avatar filename must not be empty")

    app_settings = settings or get_settings()
    suffix = Path(filename).suffix.lower()

    if suffix not in app_settings.avatar_allowed_extensions_set:
        raise UnsupportedAvatarExtensionError("Avatar file extension is not supported")

    return suffix


def validate_avatar_size(
    size_bytes: int,
    settings: Settings | None = None,
) -> None:
    app_settings = settings or get_settings()

    if size_bytes <= 0:
        raise EmptyAvatarFileError("Avatar file must not be empty")

    if size_bytes > app_settings.avatar_max_size_bytes:
        raise AvatarFileTooLargeError("Avatar file is too large")


def build_avatar_object_name(
    user_id: UUID,
    original_filename: str,
    settings: Settings | None = None,
) -> str:
    suffix = validate_avatar_filename(original_filename, settings)

    return f"{user_id}/{uuid4().hex}{suffix}"


def build_avatar_public_path(
    object_name: str,
    settings: Settings | None = None,
) -> str:
    app_settings = settings or get_settings()

    return (
        f"{app_settings.uploads_public_path.rstrip('/')}/"
        f"{app_settings.avatar_upload_subdir.strip('/')}/"
        f"{object_name}"
    )


def extract_avatar_object_name_from_public_path(
    avatar_path: str,
    settings: Settings | None = None,
) -> str | None:
    app_settings = settings or get_settings()
    expected_prefix = (
        f"{app_settings.uploads_public_path.rstrip('/')}/"
        f"{app_settings.avatar_upload_subdir.strip('/')}/"
    )

    if not avatar_path.startswith(expected_prefix):
        return None

    object_name = avatar_path.removeprefix(expected_prefix)

    return object_name or None


def resolve_avatar_path(
    object_name: str,
    settings: Settings | None = None,
) -> Path:
    if not object_name or not object_name.strip():
        raise InvalidStoragePathError("Avatar object name must not be empty")

    object_path = Path(object_name)

    if object_path.is_absolute() or ".." in object_path.parts:
        raise InvalidStoragePathError("Avatar object path is invalid")

    return get_avatar_storage_dir(settings) / object_path


def save_avatar_content(
    user_id: UUID,
    original_filename: str,
    content: bytes,
    settings: Settings | None = None,
) -> str:
    validate_avatar_size(len(content), settings)

    object_name = build_avatar_object_name(
        user_id=user_id,
        original_filename=original_filename,
        settings=settings,
    )
    file_path = resolve_avatar_path(object_name, settings)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)

    return build_avatar_public_path(object_name, settings)


def delete_avatar_by_public_path(
    avatar_path: str | None,
    settings: Settings | None = None,
) -> bool:
    if not avatar_path:
        return False

    object_name = extract_avatar_object_name_from_public_path(avatar_path, settings)

    if object_name is None:
        return False

    file_path = resolve_avatar_path(object_name, settings)

    if not file_path.is_file():
        return False

    file_path.unlink()

    return True
