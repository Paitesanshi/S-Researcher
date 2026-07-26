"""
Paradigm Migration Tool: Legacy → Unified

Provides backward compatibility for migrating from 4 legacy paradigms to
the 3 unified paradigms.
"""

import json
from enum import Enum
from typing import Dict, Optional
from pathlib import Path
from loguru import logger


class LegacyParadigm(Enum):
    """Legacy paradigms (4 types)"""
    THEORY_VALIDATION = "theory_validation"
    MECHANISM_DISCOVERY = "mechanism_discovery"
    ATTRIBUTION_ANALYSIS = "attribution_analysis"
    BOUNDARY_EXPLORATION = "boundary_exploration"


class NewParadigm(Enum):
    """Unified paradigms (3 types)"""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"


# Migration mapping
PARADIGM_MIGRATION_MAP = {
    LegacyParadigm.THEORY_VALIDATION: NewParadigm.DEDUCTIVE,
    LegacyParadigm.MECHANISM_DISCOVERY: NewParadigm.INDUCTIVE,
    LegacyParadigm.ATTRIBUTION_ANALYSIS: NewParadigm.ABDUCTIVE,
    LegacyParadigm.BOUNDARY_EXPLORATION: NewParadigm.ABDUCTIVE,
}


def migrate_paradigm(old_paradigm: str) -> str:
    """
    Migrate legacy paradigm name to unified paradigm name.

    Args:
        old_paradigm: Legacy paradigm string (e.g., 'theory_validation')

    Returns:
        Unified paradigm string (e.g., 'deductive')

    Examples:
        >>> migrate_paradigm('theory_validation')
        'deductive'
        >>> migrate_paradigm('mechanism_discovery')
        'inductive'
        >>> migrate_paradigm('deductive')
        'deductive'
    """
    # If already unified paradigm, return as-is
    if old_paradigm in ["deductive", "inductive", "abductive"]:
        return old_paradigm

    # Check legacy mapping
    for legacy, new in PARADIGM_MIGRATION_MAP.items():
        if old_paradigm == legacy.value:
            logger.info(
                f"Migrated paradigm: '{old_paradigm}' → '{new.value}'"
            )
            return new.value

    # Unknown paradigm - default to deductive
    logger.warning(f"Unknown paradigm '{old_paradigm}', defaulting to 'deductive'")
    return "deductive"


def migrate_config_file(config_path: str) -> Dict:
    """
    Migrate configuration file from legacy to unified paradigms.

    Reads JSON configuration file, replaces legacy paradigm names with
    unified paradigm names, and saves back to file.

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Updated configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    path = Path(config_path)

    if not path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Read existing config
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Migrate paradigm field if present
    if "research_paradigm" in config:
        old = config["research_paradigm"]
        new = migrate_paradigm(old)

        if old != new:
            config["research_paradigm"] = new
            logger.info(f"✓ Migrated config file: {old} → {new}")

            # Save updated config
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ Saved updated config to: {path}")
        else:
            logger.info(f"Config already uses unified paradigm: {new}")

    return config


def batch_migrate_configs(directory: str, recursive: bool = True) -> Dict[str, int]:
    """
    Batch migrate all configuration files in a directory.

    Args:
        directory: Directory path containing config files
        recursive: Whether to search subdirectories recursively

    Returns:
        Dictionary with migration statistics:
        {
            "total_files": int,
            "migrated": int,
            "already_unified": int,
            "errors": int
        }
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return {"total_files": 0, "migrated": 0, "already_unified": 0, "errors": 0}

    # Find all JSON files
    pattern = "**/*.json" if recursive else "*.json"
    json_files = list(dir_path.glob(pattern))

    stats = {
        "total_files": 0,
        "migrated": 0,
        "already_unified": 0,
        "errors": 0
    }

    logger.info(f"Found {len(json_files)} JSON files in {directory}")

    for json_file in json_files:
        stats["total_files"] += 1

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Check if config has research_paradigm field
            if "research_paradigm" not in config:
                continue

            old = config["research_paradigm"]
            new = migrate_paradigm(old)

            if old != new:
                # Migrate
                config["research_paradigm"] = new

                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                stats["migrated"] += 1
                logger.info(f"✓ Migrated {json_file.name}: {old} → {new}")
            else:
                stats["already_unified"] += 1

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_file}: {e}")
            stats["errors"] += 1
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            stats["errors"] += 1

    logger.info(f"\n=== Migration Summary ===")
    logger.info(f"Total files scanned: {stats['total_files']}")
    logger.info(f"Migrated: {stats['migrated']}")
    logger.info(f"Already unified: {stats['already_unified']}")
    logger.info(f"Errors: {stats['errors']}")

    return stats


def get_migration_info(paradigm: str) -> Dict[str, str]:
    """
    Get migration information for a paradigm.

    Args:
        paradigm: Paradigm name (legacy or unified)

    Returns:
        Dictionary with migration info:
        {
            "original": str,
            "migrated": str,
            "is_legacy": bool,
            "formula": str,
            "description": str
        }
    """
    migrated = migrate_paradigm(paradigm)
    is_legacy = paradigm != migrated

    formulas = {
        "deductive": "M + C → O*",
        "inductive": "O_real + C → M*",
        "abductive": "M + {C_i} → R*"
    }

    descriptions = {
        "deductive": "Predict outcomes from theory and conditions",
        "inductive": "Infer mechanisms from real observations",
        "abductive": "Quantify causal relationships through experiments"
    }

    return {
        "original": paradigm,
        "migrated": migrated,
        "is_legacy": is_legacy,
        "formula": formulas.get(migrated, "Unknown"),
        "description": descriptions.get(migrated, "Unknown paradigm")
    }


if __name__ == "__main__":
    """CLI interface for migration tool"""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python paradigm_migration.py <config_file>        # Migrate single file")
        print("  python paradigm_migration.py <directory> --batch  # Migrate all JSON in directory")
        print("  python paradigm_migration.py <paradigm> --info    # Get paradigm info")
        sys.exit(1)

    target = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else None

    if mode == "--info":
        # Show paradigm info
        info = get_migration_info(target)
        print(f"\n=== Paradigm Migration Info ===")
        print(f"Original: {info['original']}")
        print(f"Migrated: {info['migrated']}")
        print(f"Is Legacy: {info['is_legacy']}")
        print(f"Formula: {info['formula']}")
        print(f"Description: {info['description']}")

    elif mode == "--batch":
        # Batch migrate directory
        stats = batch_migrate_configs(target, recursive=True)
        print(f"\n✓ Migration complete: {stats['migrated']} files updated")

    else:
        # Migrate single file
        try:
            config = migrate_config_file(target)
            print(f"\n✓ Migration complete")
            print(f"Updated paradigm: {config.get('research_paradigm', 'N/A')}")
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            sys.exit(1)
