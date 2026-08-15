import argparse
from datetime import date, datetime

from rq import Worker

from app.worker.pipeline import enqueue_pipeline
from app.worker.queue import DEFAULT_QUEUE_NAME, DEFAULT_RETRY, get_queue, get_redis
from app.worker.scheduler import register_daily_pipeline


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_symbols(value: str) -> list[str]:
    return [s.strip().upper() for s in value.split(",") if s.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.worker.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_worker = subparsers.add_parser("run-worker", help="start an RQ worker process")
    run_worker.add_argument("--burst", action="store_true", help="process queued jobs then exit")

    enqueue = subparsers.add_parser(
        "enqueue-pipeline", help="enqueue one run of the daily pipeline"
    )
    enqueue.add_argument("--symbols", required=True)
    enqueue.add_argument("--date", type=_parse_date, required=False, dest="as_of")

    register = subparsers.add_parser(
        "register-scheduler", help="register the daily pipeline cron job"
    )
    register.add_argument("--symbols", required=True)

    args = parser.parse_args(argv)

    if args.command == "run-worker":
        redis = get_redis()
        worker = Worker([DEFAULT_QUEUE_NAME], connection=redis)
        worker.work(burst=args.burst)
        return 0

    if args.command == "enqueue-pipeline":
        symbols = _parse_symbols(args.symbols)
        queue = get_queue()
        job = queue.enqueue(enqueue_pipeline, symbols, args.as_of, retry=DEFAULT_RETRY)
        print(f"enqueued pipeline job {job.id} for {args.as_of or date.today()}")
        return 0

    if args.command == "register-scheduler":
        symbols = _parse_symbols(args.symbols)
        register_daily_pipeline(get_redis(), symbols)
        print(f"registered daily pipeline for symbols: {symbols}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
