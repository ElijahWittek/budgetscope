from pathlib import Path
from secrets import token_urlsafe

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import DatabaseError

from budgetscope.persistence.database import (
    open_existing_encrypted_database,
)


def test_sqlcipher_sqlalchemy_connection(tmp_path: Path) -> None:
    database_path = tmp_path / "encrypted.db"
    passphrase = token_urlsafe(32)

    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=passphrase,
        database=str(database_path)
    )

    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            cipher_version = connection.exec_driver_sql(
                "PRAGMA cipher_version"
            ).scalar_one_or_none()

            assert cipher_version is not None

            connection.exec_driver_sql(
                "CREATE TABLE encryption_probe "
                "(value TEXT NOT NULL)"
            )

            connection.exec_driver_sql(
                "INSERT INTO encryption_probe (value) VALUES (?)",
                ("synthetic-test-data",),
            )
    finally:
        engine.dispose()

    assert database_path.is_file()

    # Encrypted databases must not expose the plaintext SQLite file header.
    assert not database_path.read_bytes().startswith(
        b"SQLite format 3\x00"
    )

    reopened_engine = open_existing_encrypted_database(
        database_path,
        passphrase,
    )

    try:
        with reopened_engine.connect() as connection:
            result = connection.exec_driver_sql(
                "SELECT value FROM encryption_probe"
            ).scalar_one()

            assert result == "synthetic-test-data"
            assert (
                connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
                == 1
            )
    finally:
        reopened_engine.dispose()

    with pytest.raises(DatabaseError):
        open_existing_encrypted_database(
            database_path,
            token_urlsafe(32),
        )

def test_missing_database_is_not_created(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):
        open_existing_encrypted_database(
            database_path,
            token_urlsafe(32),
        )

    assert not database_path.exists()
