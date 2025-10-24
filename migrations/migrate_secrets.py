"""Migration script to move secrets from .env to secure storage.

This script:
1. Reads secrets from .env file
2. Encrypts them using DPAPI (Windows) or Azure KeyVault
3. Optionally removes secrets from .env file (backup created)

Usage:
    # Dry run (show what would be migrated)
    python migrations/migrate_secrets.py --dry-run
    
    # Migrate secrets (keeps .env file)
    python migrations/migrate_secrets.py
    
    # Migrate and remove from .env (backup created as .env.backup)
    python migrations/migrate_secrets.py --remove-from-env
"""
import argparse
import logging
import shutil
from pathlib import Path

from security.secrets import secrets_manager, DPAPI_AVAILABLE, AZURE_KEYVAULT_AVAILABLE

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# Secrets to migrate (sensitive values that should be encrypted)
SECRETS_TO_MIGRATE = [
    # Authentication
    "JWT_SECRET",
    "ADMIN_PASSWORD",
    "USER_PASSWORD",
    
    # Databases
    "POSTGRES_PASSWORD",
    "NEO4J_PASSWORD",
    "COUCHDB_PASSWORD",
    
    # Optional: API keys, webhooks
    "OPENAI_API_KEY",
    "AZURE_API_KEY",
    "WEBHOOK_SECRET",
]


def read_env_file(env_path: Path) -> dict:
    """Read .env file and parse key=value pairs."""
    env_vars = {}
    
    if not env_path.exists():
        logger.warning(f"ENV file not found: {env_path}")
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    logger.info(f"Read {len(env_vars)} variables from {env_path}")
    return env_vars


def write_env_file(env_path: Path, env_vars: dict, secrets_to_remove: set = None):
    """Write .env file, optionally removing specified secrets."""
    if secrets_to_remove is None:
        secrets_to_remove = set()
    
    lines = []
    
    if env_path.exists():
        # Preserve original file structure (comments, order)
        with open(env_path, 'r') as f:
            for line in f:
                stripped = line.strip()
                
                # Keep comments and empty lines
                if not stripped or stripped.startswith('#'):
                    lines.append(line)
                    continue
                
                # Parse key
                if '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    
                    # Skip secrets that should be removed
                    if key in secrets_to_remove:
                        lines.append(f"# {key}=<MIGRATED_TO_SECURE_STORAGE>\n")
                        continue
                
                lines.append(line)
    
    # Write updated file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    logger.info(f"Updated {env_path} (removed {len(secrets_to_remove)} secrets)")


def migrate_secrets(env_path: Path, dry_run: bool = False, remove_from_env: bool = False):
    """Migrate secrets from .env to secure storage."""
    logger.info("=" * 70)
    logger.info("SECRETS MIGRATION SCRIPT")
    logger.info("=" * 70)
    
    # Check secure backend availability
    if AZURE_KEYVAULT_AVAILABLE:
        backend_name = "Azure KeyVault"
    elif DPAPI_AVAILABLE:
        backend_name = "Windows DPAPI"
    else:
        backend_name = "Environment Variables (NO ENCRYPTION)"
        logger.error("No secure backend available - migration aborted")
        return
    
    logger.info(f"Secure Backend: {backend_name}")
    logger.info(f"ENV File: {env_path}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info(f"Remove from ENV: {remove_from_env}")
    logger.info("=" * 70)
    
    # Read .env file
    env_vars = read_env_file(env_path)
    
    if not env_vars:
        logger.error("No environment variables found - nothing to migrate")
        return
    
    # Find secrets to migrate
    secrets_found = {key: value for key, value in env_vars.items() if key in SECRETS_TO_MIGRATE}
    
    if not secrets_found:
        logger.info("No secrets found for migration")
        logger.info(f"Searched for: {', '.join(SECRETS_TO_MIGRATE)}")
        return
    
    logger.info(f"Found {len(secrets_found)} secrets to migrate:")
    for key in secrets_found:
        value_preview = secrets_found[key][:10] + "..." if len(secrets_found[key]) > 10 else secrets_found[key]
        logger.info(f"  - {key} = {value_preview}")
    
    if dry_run:
        logger.info("")
        logger.info("DRY RUN - No changes made")
        logger.info("Run without --dry-run to perform migration")
        return
    
    # Backup .env file
    if remove_from_env:
        backup_path = env_path.with_suffix('.env.backup')
        shutil.copy2(env_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    # Migrate secrets
    logger.info("")
    logger.info("Migrating secrets...")
    migrated = 0
    failed = 0
    
    for key, value in secrets_found.items():
        try:
            if secrets_manager.set_secret(key, value):
                migrated += 1
                logger.info(f"  ✅ {key} → Encrypted and stored")
            else:
                failed += 1
                logger.error(f"  ❌ {key} → Failed to store")
        except Exception as e:
            failed += 1
            logger.error(f"  ❌ {key} → Error: {e}")
    
    logger.info("")
    logger.info(f"Migration complete: {migrated} succeeded, {failed} failed")
    
    # Remove secrets from .env if requested
    if remove_from_env and migrated > 0:
        logger.info("")
        logger.info("Removing migrated secrets from .env file...")
        migrated_keys = set(secrets_found.keys())
        write_env_file(env_path, env_vars, secrets_to_remove=migrated_keys)
        logger.info(f"Updated {env_path} (secrets moved to secure storage)")
    
    # Verification
    logger.info("")
    logger.info("Verifying migration...")
    verified = 0
    for key in secrets_found.keys():
        stored_value = secrets_manager.get_secret(key)
        if stored_value == secrets_found[key]:
            verified += 1
            logger.info(f"  ✅ {key} → Verified")
        else:
            logger.error(f"  ❌ {key} → Verification failed")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"MIGRATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Backend: {backend_name}")
    logger.info(f"Secrets migrated: {migrated}/{len(secrets_found)}")
    logger.info(f"Verification: {verified}/{migrated}")
    logger.info(f"Status: {'SUCCESS' if verified == migrated else 'FAILED'}")
    logger.info("=" * 70)
    
    if remove_from_env:
        logger.info("")
        logger.info("IMPORTANT: Secrets have been removed from .env file")
        logger.info(f"Backup available at: {env_path.with_suffix('.env.backup')}")
        logger.info("Backends will now load secrets from secure storage")


def main():
    parser = argparse.ArgumentParser(description="Migrate secrets from .env to secure storage")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env.production"),
        help="Path to .env file (default: .env.production)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--remove-from-env",
        action="store_true",
        help="Remove migrated secrets from .env file (backup created)"
    )
    
    args = parser.parse_args()
    
    try:
        migrate_secrets(
            env_path=args.env_file,
            dry_run=args.dry_run,
            remove_from_env=args.remove_from_env
        )
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Migration cancelled by user")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
