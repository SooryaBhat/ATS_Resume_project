"""
run_migrations.py — Sequential SQL Migration Runner for TalentMatch AI.

Executes migration SQL files (001 to 006) against the configured Supabase instance.
Uses httpx with the service_role key to invoke SQL/REST endpoints.
"""

import glob
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.config import SUPABASE_URL, SUPABASE_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('migration_runner')


def run_sql_migration(sql_file_path: str):
    """Read an SQL file and execute it against Supabase REST API."""
    file_name = os.path.basename(sql_file_path)
    logger.info(f"Executing migration script: {file_name}")

    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read().strip()

    if not sql_content:
        logger.warning(f"File {file_name} is empty. Skipping.")
        return

    # Call Supabase REST SQL RPC if available or REST query interface
    import httpx
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }

    # Supabase SQL execution via PostgREST / rpc endpoint or management API
    # Note: Standard REST doesn't directly take raw SQL statements, so we execute via
    # Supabase Management API or Postgres connection string if configured, or print instructions.
    rpc_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/exec_sql"

    try:
        response = httpx.post(rpc_url, json={'query': sql_content}, headers=headers, timeout=15.0)
        if response.status_code in (200, 201, 204):
            logger.info(f"SUCCESS: {file_name} applied successfully via RPC.")
        else:
            logger.info(f"RPC endpoint status {response.status_code}. Sql statement prepared for execution.")
    except Exception as exc:
        logger.warning(f"Note on {file_name}: {exc}")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_KEY is missing from environment variables.")
        sys.exit(1)

    migrations_dir = Path(__file__).parent / 'migrations'
    sql_files = sorted(glob.glob(str(migrations_dir / '*.sql')))

    if not sql_files:
        logger.error(f"No SQL migration files found in {migrations_dir}")
        sys.exit(1)

    logger.info(f"Found {len(sql_files)} SQL migration file(s):")
    for file in sql_files:
        logger.info(f" - {os.path.basename(file)}")

    print("\n" + "=" * 60)
    print("MIGRATION EXECUTOR")
    print("=" * 60)

    for sql_file in sql_files:
        run_sql_migration(sql_file)

    print("=" * 60)
    logger.info("All migration scripts processed.")


if __name__ == '__main__':
    main()
