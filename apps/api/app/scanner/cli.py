import argparse
from datetime import date, datetime

from app.db.session import SessionLocal
from app.scanner.service import ScannerService


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.scanner.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="run setup detection/scoring for symbols")
    scan.add_argument("--symbols", required=True, help="comma-separated symbols, e.g. BBCA,BBRI")
    scan.add_argument("--date", type=_parse_date, required=False)

    args = parser.parse_args(argv)

    if args.command == "scan":
        as_of = args.date or date.today()
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

        session = SessionLocal()
        try:
            service = ScannerService(session)
            run = service.scan_many(symbols, as_of)
            print(
                f"scan {run.scan_date}: status={run.status.value} "
                f"scanned={run.symbols_scanned} skipped_stale={run.symbols_skipped_stale} "
                f"candidates_found={run.candidates_found}"
            )
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
