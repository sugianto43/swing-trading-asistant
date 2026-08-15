import argparse
from datetime import date, datetime, timedelta

from app.db.session import SessionLocal
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.ingestion import IngestionService
from app.marketdata.provider import MarketDataProvider


def _build_provider(name: str) -> MarketDataProvider:
    if name == "fixture":
        return FixtureProvider()
    if name == "yfinance":
        from app.marketdata.yfinance_provider import YfinanceProvider

        return YfinanceProvider()
    raise ValueError(f"unknown provider: {name!r} (expected 'fixture' or 'yfinance')")


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.marketdata.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="sync instruments and ingest OHLCV/corp actions")
    ingest.add_argument("--provider", choices=["fixture", "yfinance"], default="fixture")
    ingest.add_argument("--symbols", required=True, help="comma-separated symbols, e.g. BBCA,BBRI")
    ingest.add_argument("--start", type=_parse_date, required=False)
    ingest.add_argument("--end", type=_parse_date, required=False)

    args = parser.parse_args(argv)

    if args.command == "ingest":
        end = args.end or date.today()
        start = args.start or (end - timedelta(days=90))
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

        provider = _build_provider(args.provider)
        session = SessionLocal()
        try:
            service = IngestionService(session, provider)
            instrument_summary = service.sync_instruments()
            print(f"instruments: {instrument_summary}")

            for symbol in symbols:
                price_summary = service.ingest_prices(symbol, start, end)
                print(
                    f"{symbol} prices: status={price_summary.status.value} "
                    f"processed={price_summary.records_processed} "
                    f"flagged={price_summary.records_flagged} notes={price_summary.notes}"
                )
                action_summary = service.ingest_corporate_actions(symbol, start, end)
                print(
                    f"{symbol} corporate actions: status={action_summary.status.value} "
                    f"processed={action_summary.records_processed}"
                )
        finally:
            session.close()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
