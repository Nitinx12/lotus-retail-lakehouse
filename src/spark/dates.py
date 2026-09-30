# null safe date parsing with coerce semantics
from __future__ import annotations

from pyspark.sql import functions as F
from pyspark.sql.column import Column


# parses strings to dates returning null on malformed input
def safe_to_date(value: Column | str) -> Column:
    col = value if isinstance(value, Column) else F.col(value)
    return F.try_to_date(col.cast("string"))
