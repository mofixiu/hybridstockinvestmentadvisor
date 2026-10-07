"""Apply the versioned product-foundation migration to the configured DB."""

from sqlalchemy import inspect, text

from src.api.database import Base, engine


MIGRATION_ID = "20261007_product_foundation"


def apply(bind=engine) -> None:
    with bind.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version VARCHAR(100) PRIMARY KEY, "
                "applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        # create_all is idempotent and also creates additive tables added in
        # later compatible revisions, even when the original migration ID is
        # already present.
        Base.metadata.create_all(bind=connection)
        inspector = inspect(connection)
        password_reset_columns = {column["name"] for column in inspector.get_columns("password_resets")}
        if "otp_hash" not in password_reset_columns:
            connection.execute(text("ALTER TABLE password_resets ADD COLUMN otp_hash VARCHAR(64) NULL"))
        if "failed_attempts" not in password_reset_columns:
            connection.execute(
                text("ALTER TABLE password_resets ADD COLUMN failed_attempts INT NOT NULL DEFAULT 0")
            )
        paper_signal_columns = {column["name"] for column in inspector.get_columns("paper_signals")}
        if "prior_probability_positive" not in paper_signal_columns:
            connection.execute(
                text("ALTER TABLE paper_signals ADD COLUMN prior_probability_positive DECIMAL(8, 6) NULL")
            )

        applied = connection.execute(
            text("SELECT version FROM schema_migrations WHERE version = :version"),
            {"version": MIGRATION_ID},
        ).first()
        if applied:
            print(f"Migration already applied: {MIGRATION_ID}")
            return

        connection.execute(
            text("INSERT INTO schema_migrations (version) VALUES (:version)"),
            {"version": MIGRATION_ID},
        )
    print(f"Applied migration: {MIGRATION_ID}")


def rollback(bind=engine, *, confirm_drop_data: bool = False) -> None:
    """Remove this migration's research/invite tables, preserving account data.

    Market bars and paper-signal rows are deleted, so callers must pass the
    explicit confirmation flag. Added password-reset columns remain in place;
    leaving those nullable/defaulted columns is safe for older application code.
    """
    if not confirm_drop_data:
        raise ValueError("rollback requires confirm_drop_data=True because research data is deleted")

    with bind.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if "schema_migrations" not in tables:
            print("No migration metadata exists; nothing to roll back")
            return
        applied = connection.execute(
            text("SELECT version FROM schema_migrations WHERE version = :version"),
            {"version": MIGRATION_ID},
        ).first()
        if not applied:
            print(f"Migration is not applied: {MIGRATION_ID}")
            return

        for table_name in (
            "model_release_approvals",
            "paper_signals",
            "market_daily_bars",
            "tester_invites",
        ):
            if table_name in tables:
                connection.execute(text(f"DROP TABLE {table_name}"))
        connection.execute(
            text("DELETE FROM schema_migrations WHERE version = :version"),
            {"version": MIGRATION_ID},
        )
    print(f"Rolled back migration: {MIGRATION_ID}; user and portfolio data was preserved")


if __name__ == "__main__":
    apply()
