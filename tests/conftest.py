# shared spark session for unit tests
from __future__ import annotations

import pytest
from pyspark.sql import SparkSession

from src.spark.session import get_spark


# reuses one local spark session across the test suite
@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = get_spark("lotus-tests")
    session.conf.set("spark.sql.shuffle.partitions", "2")
    try:
        session.createDataFrame([(1,)], schema="v INT").count()
    except Exception:
        session.stop()
        pytest.skip("spark python workers unavailable in this environment")
        raise
    yield session
    session.stop()
