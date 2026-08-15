import argparse
from datetime import datetime

from app.db.enums import ExecutionSide
from app.db.session import SessionLocal
from app.positions.execution_service import ExecutionService


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.positions.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="record a manual execution")
    record.add_argument("--symbol", required=True)
    record.add_argument("--side", required=True, choices=[s.value for s in ExecutionSide])
    record.add_argument("--quantity", type=int, required=True)
    record.add_argument("--price", type=float, required=True)
    record.add_argument("--fee", type=float, default=0.0)
    record.add_argument("--executed-at", type=_parse_datetime, required=True)
    record.add_argument("--notes", default=None)

    args = parser.parse_args(argv)

    if args.command == "record":
        session = SessionLocal()
        try:
            service = ExecutionService(session)
            position = service.record_execution(
                symbol=args.symbol,
                side=ExecutionSide(args.side),
                quantity=args.quantity,
                price=args.price,
                fee=args.fee,
                executed_at=args.executed_at,
                notes=args.notes,
            )
            print(f"position {position.id}: status={position.status.value}")
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
