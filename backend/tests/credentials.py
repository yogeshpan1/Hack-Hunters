"""Ephemeral credentials generated per test process; never printed or persisted."""
import secrets

TEST_PASSWORD = secrets.token_urlsafe(32)
SECOND_PASSWORD = secrets.token_urlsafe(32)
