"""Public-demo reset: put the database back to exactly the synthetic seed.

Run once (``python -m app.demo_reset``) or as a long-running job (``--loop``), which seeds an
empty database at start and then resets it every ``EDUPULSE_DEMO_RESET_HOURS`` hours. A reset
deletes everything first, so self sign-up accounts, audit entries and sessions created since the
last reset are removed. The delete and the new seed run in one transaction: visitors never see a
half-empty database. The loop only runs when ``EDUPULSE_PUBLIC_DEMO`` is true.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.seed import SeedConfig, SeedSummary, database_has_data, reset, resolve_password, seed


def reset_demo(session: Session, config: SeedConfig) -> SeedSummary:
    """Delete all data and seed it again (the caller owns the transaction)."""
    reset(session)
    return seed(session, config)


def _log(event: str, **fields: object) -> None:
    record = {"time": datetime.now(UTC).isoformat(), "event": event, **fields}
    print(json.dumps(record), flush=True)


def run_once(config: SeedConfig, *, only_if_empty: bool = False) -> bool:
    with get_session_factory()() as session, session.begin():
        if only_if_empty and database_has_data(session):
            return False
        summary = reset_demo(session, config)
    _log("demo_reset", counts=summary.counts)
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reset the public demo to the synthetic seed.")
    parser.add_argument("--loop", action="store_true", help="seed if empty, then reset on a timer")
    args = parser.parse_args(argv)
    settings = get_settings()
    config = SeedConfig(password=resolve_password(os.environ.get("EDUPULSE_DEMO_PASSWORD")))
    if not args.loop:
        run_once(config)
        return
    if not settings.public_demo:
        _log("demo_reset_disabled", reason="EDUPULSE_PUBLIC_DEMO is not true")
        return
    if run_once(config, only_if_empty=True):
        _log("demo_seeded", reason="database was empty")
    interval = settings.demo_reset_hours * 3600
    while True:
        time.sleep(interval)
        run_once(config)


if __name__ == "__main__":
    main()
