import os

from dotenv import load_dotenv

if not load_dotenv():
    print("Warning: no .env file found, relying on system environment variables")

# =========================================================
# POSTGRES
# =========================================================
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE")
POSTGRES_CHANNEL_BINDING = os.getenv("POSTGRES_CHANNEL_BINDING")

if POSTGRES_PORT is not None:
    try:
        POSTGRES_PORT = int(POSTGRES_PORT)
    except ValueError:
        raise OSError(f"POSTGRES_PORT must be an integer, got: {POSTGRES_PORT!r}")

POSTGRES_SCHEMA_BRONZE = os.getenv("POSTGRES_SCHEMA_BRONZE")
POSTGRES_SCHEMA_SILVER = os.getenv("POSTGRES_SCHEMA_SILVER")
POSTGRES_SCHEMA_GOLD = os.getenv("POSTGRES_SCHEMA_GOLD")
POSTGRES_SCHEMA_PUBLIC = os.getenv("POSTGRES_SCHEMA_PUBLIC")

# =========================================================
# MONGODB
# =========================================================
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

# =========================================================
# DATABRICKS
# =========================================================
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA")






