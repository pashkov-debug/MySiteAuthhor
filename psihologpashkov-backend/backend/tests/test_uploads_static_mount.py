from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_uploads_static_mount_serves_existing_file(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    uploads_root = tmp_path / "uploads"
    avatars_dir = uploads_root / "avatars"
    avatars_dir.mkdir(parents=True)

    avatar_file = avatars_dir / "test-avatar.txt"
    avatar_file.write_text("avatar-test", encoding="utf-8")

    app = create_app(
        test_settings.model_copy(
            update={
                "uploads_root": str(uploads_root),
                "uploads_public_path": "/uploads",
            }
        )
    )
    client = TestClient(app)

    response = client.get("/uploads/avatars/test-avatar.txt")

    assert response.status_code == 200
    assert response.text == "avatar-test"


def test_uploads_static_mount_returns_404_for_missing_file(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    uploads_root = tmp_path / "uploads"
    uploads_root.mkdir(parents=True)

    app = create_app(
        test_settings.model_copy(
            update={
                "uploads_root": str(uploads_root),
                "uploads_public_path": "/uploads",
            }
        )
    )
    client = TestClient(app)

    response = client.get("/uploads/avatars/missing.png")

    assert response.status_code == 404
