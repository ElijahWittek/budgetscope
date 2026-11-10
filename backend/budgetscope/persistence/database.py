from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.pool import NullPool


def configure_foreign_key_enforcement(engine: Engine) -> None:
    """Enable and verify foreign key checks on every new connection."""

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(
        dbapi_connection,
        _connection_record,
    ) -> None:
        # Configure the connection before application transactions begin.
        cursor = dbapi_connection.cursor()

        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA foreign_keys")

            setting = cursor.fetchone()

            if setting is None or setting[0] != 1:
                raise RuntimeError(
                    "SQLite foreign key enforcement is unavailable."
                )
        finally:
            cursor.close()


def open_existing_encrypted_database(
        database_path: Path,
        passphrase: str,
) -> Engine:
    """Open an existing encrypted database and verify its readability."""

    if not database_path.is_absolute():
        raise ValueError("An absolute database path is required.")

    if not database_path.is_file():
        raise FileNotFoundError("Encrypted database file not found.")

    if not passphrase:
        raise ValueError("Passphrase must not be empty.")

    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=passphrase,
        database=str(database_path),
    )

    engine = create_engine(
        database_url,
        poolclass=NullPool,
    )

    configure_foreign_key_enforcement(engine)

    try:
        with engine.connect() as connection:
            # Reading the schema forces SQLCipher to validate the passphrase.
            connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master"
            ).scalar_one()
    except Exception:
        engine.dispose()
        raise

    return engine
