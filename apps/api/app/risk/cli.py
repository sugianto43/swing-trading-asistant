import argparse
from datetime import date, datetime

from app.db.enums import SetupType
from app.db.session import SessionLocal
from app.risk.service import RiskService


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.risk.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="build a trade plan for one instrument/setup/date")
    plan.add_argument("--symbol", required=True)
    plan.add_argument("--setup", required=True, choices=[s.value for s in SetupType])
    plan.add_argument("--date", type=_parse_date, required=True, dest="plan_date")
    plan.add_argument("--capital", type=float, required=True)

    args = parser.parse_args(argv)

    if args.command == "plan":
        session = SessionLocal()
        try:
            service = RiskService(session)
            trade_plan = service.build_plan(
                symbol=args.symbol,
                setup_type=SetupType(args.setup),
                plan_date=args.plan_date,
                capital=args.capital,
            )
            print(f"trade plan {trade_plan.id}: status={trade_plan.status.value}")
            if trade_plan.status.value == "REJECTED":
                for reason in trade_plan.rejection_reasons:
                    print(f"  - {reason}")
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
