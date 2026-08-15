import argparse
from datetime import date, datetime, timedelta

from app.db.session import SessionLocal
from app.indicators.service import IndicatorService


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.indicators.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compute = subparsers.add_parser("compute", help="compute and persist indicator snapshots")
    compute.add_argument("--symbols", required=True, help="comma-separated symbols, e.g. BBCA,BBRI")
    compute.add_argument("--start", type=_parse_date, required=False)
    compute.add_argument("--end", type=_parse_date, required=False)

    args = parser.parse_args(argv)

    if args.command == "compute":
        end = args.end or date.today()
        start = args.start or (end - timedelta(days=90))
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

        session = SessionLocal()
        try:
            service = IndicatorService(session)
            for symbol in symbols:
                summary = service.compute_and_persist(symbol, persist_from=start, persist_to=end)
                print(
                    f"{symbol}: computed={summary.computed} persisted_in_range={summary.persisted}"
                )
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
