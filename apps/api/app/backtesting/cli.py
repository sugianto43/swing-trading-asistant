import argparse
from datetime import date, datetime

from app.backtesting.config import BacktestConfig
from app.backtesting.service import BacktestService
from app.db.enums import SetupType
from app.db.session import SessionLocal


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.backtesting.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run a backtest over a date range")
    run.add_argument("--setup", required=True, choices=[s.value for s in SetupType])
    run.add_argument("--start", type=_parse_date, required=True)
    run.add_argument("--end", type=_parse_date, required=True)
    run.add_argument("--min-score", type=float, default=None)

    args = parser.parse_args(argv)

    if args.command == "run":
        kwargs = {}
        if args.min_score is not None:
            kwargs["min_score"] = args.min_score
        config = BacktestConfig(
            setup_type=SetupType(args.setup), start_date=args.start, end_date=args.end, **kwargs
        )

        session = SessionLocal()
        try:
            service = BacktestService(session)
            backtest_run = service.run(config)
            print(f"backtest {backtest_run.id}: status={backtest_run.status.value}")
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
