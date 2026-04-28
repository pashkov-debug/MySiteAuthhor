from pathlib import Path

from alembic.config import Config


def test_alembic_config_exists_and_points_to_migrations() -> None:
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini_path = project_root / "alembic.ini"

    assert alembic_ini_path.is_file()

    config = Config(str(alembic_ini_path))

    assert config.get_main_option("script_location") == "backend/app/db/migrations"


def test_alembic_versions_directory_exists() -> None:
    project_root = Path(__file__).resolve().parents[2]
    versions_dir = project_root / "backend/app/db/migrations/versions"

    assert versions_dir.is_dir()
