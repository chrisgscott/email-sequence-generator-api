from logging.config import fileConfig
import sys
from pathlib import Path
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv
import os

# Add the project root directory to the Python path
project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))

from alembic import context
from app.db.database import Base
from app.models import sequence, email
from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('alembic')

load_dotenv()  # This loads the variables from .env file, if it exists

# Override sqlalchemy.url path
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = settings.DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import os

logger.debug(f"Current directory: {os.getcwd()}")
logger.debug(f"Alembic directory: {os.path.dirname(__file__)}")
logger.debug(f"Versions directory: {os.path.join(os.path.dirname(__file__), 'versions')}")
logger.debug(f"Database URL: {config.get_main_option('sqlalchemy.url')}")
logger.debug(f"Metadata tables: {Base.metadata.tables.keys()}")

# Check if the problematic revision exists in any file
for root, dirs, files in os.walk(os.getcwd()):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                if 'b352902318c9' in content:
                    logger.debug(f"Found problematic revision in file: {os.path.join(root, file)}")

print("Current directory:", os.getcwd())
print("Alembic directory:", os.path.dirname(__file__))
print("Versions directory:", os.path.join(os.path.dirname(__file__), 'versions'))
print("Database URL:", config.get_main_option("sqlalchemy.url"))
print("Metadata tables:", Base.metadata.tables.keys())

# Check if the problematic revision exists in any file
for root, dirs, files in os.walk(os.getcwd()):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                if 'b352902318c9' in content:
                    print(f"Found problematic revision in file: {os.path.join(root, file)}")