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
