import csv
import io
from datetime import date
from importlib import resources

from app.db.enums import ListingStatus
from app.marketdata.provider import RawInstrument

SEED_SOURCE = "idx-seed"


def load_seed_instruments() -> list[RawInstrument]:
    """Load the local IDX instrument-universe seed.

    No provider used in this phase exposes an instrument-master/listing
    API, so the universe is bootstrapped from this static file rather than
    invented at runtime. Extending IDX coverage means editing this seed,
    not guessing symbols. See docs/data/VENDOR-EVALUATION.md §8.
    """
    csv_path = resources.files(__package__).joinpath("idx_instruments.csv")
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return [
        RawInstrument(
            symbol=row["symbol"],
            source_symbol=row["source_symbol"],
            company_name=row["company_name"],
            source=SEED_SOURCE,
            sector=row["sector"] or None,
            subsector=row["subsector"] or None,
            listing_date=date.fromisoformat(row["listing_date"]) if row["listing_date"] else None,
            status=ListingStatus(row["status"]),
        )
        for row in reader
    ]
