import argparse

from app.ai.orchestrator import AIAnalystService
from app.db.session import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.ai.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="run a grounded AI analysis")
    analyze.add_argument("--question", required=True)
    analyze.add_argument("--symbol", default=None)

    args = parser.parse_args(argv)

    if args.command == "analyze":
        session = SessionLocal()
        try:
            service = AIAnalystService(session)
            snapshot = service.analyze(question=args.question, symbol=args.symbol)
            print(f"snapshot {snapshot.id}: provider={snapshot.provider} model={snapshot.model}")
            print(snapshot.response)
            if snapshot.guardrail_flags:
                print(f"guardrail flags: {snapshot.guardrail_flags}")
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
