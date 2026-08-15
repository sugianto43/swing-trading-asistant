import argparse
from datetime import date, datetime

from app.db.session import SessionLocal
from app.intelligence.service import MarketIntelligenceService


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.intelligence.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compute = subparsers.add_parser(
        "compute-breadth", help="compute and persist a breadth snapshot"
    )
    compute.add_argument("--date", type=_parse_date, required=True, dest="as_of")

    args = parser.parse_args(argv)

    if args.command == "compute-breadth":
        session = SessionLocal()
        try:
            service = MarketIntelligenceService(session)
            snapshot = service.compute_breadth_snapshot(args.as_of)
            print(
                f"breadth {snapshot.as_of}: universe={snapshot.universe_size} "
                f"regime={snapshot.regime.value} pct_above_sma50={snapshot.pct_above_sma50}"
            )
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
