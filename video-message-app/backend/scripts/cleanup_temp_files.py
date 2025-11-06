#!/usr/bin/env python3
"""
Temporary File Cleanup Script

Automatically removes temporary files created by OpenVoice service.
Includes security measures against path traversal and symlink attacks.

Usage:
    python cleanup_temp_files.py [--max-age-hours 24] [--dry-run]

Author: Artemis (Technical Perfectionist)
Date: 2025-11-06
"""

import argparse
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CleanupStats:
    """Statistics for cleanup operation."""
    files_deleted: int = 0
    dirs_deleted: int = 0
    bytes_freed: int = 0
    errors: int = 0


class TempFileCleanup:
    """
    Secure temporary file cleanup with performance optimization.

    Security features:
    - Path traversal prevention
    - Symlink attack mitigation
    - Whitelist-based patterns
    """

    # Whitelist of allowed patterns (no path traversal characters)
    ALLOWED_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r'^openvoice_[a-zA-Z0-9_-]+$'),
        re.compile(r'^tmp[a-zA-Z0-9_-]*\.wav$'),
    ]

    # Maximum path depth to prevent traversal
    MAX_PATH_DEPTH: int = 2

    def __init__(
        self,
        base_dir: Path,
        max_age_hours: float,
        dry_run: bool = False
    ) -> None:
        """
        Initialize cleanup handler.

        Args:
            base_dir: Base directory to clean (e.g., /tmp)
            max_age_hours: Delete files older than this many hours
            dry_run: If True, don't actually delete files
        """
        self.base_dir = self._validate_base_dir(base_dir)
        self.max_age_seconds = max_age_hours * 3600
        self.dry_run = dry_run
        self.stats = CleanupStats()

    def _validate_base_dir(self, base_dir: Path) -> Path:
        """
        Validate and resolve base directory.

        Security checks:
        - Must be absolute path
        - Must exist
        - Must be a directory
        - Must not be a symlink

        Args:
            base_dir: Directory to validate

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If validation fails
        """
        if not base_dir.is_absolute():
            raise ValueError(f"Base directory must be absolute: {base_dir}")

        resolved = base_dir.resolve(strict=True)

        if not resolved.exists():
            raise ValueError(f"Base directory does not exist: {resolved}")

        if not resolved.is_dir():
            raise ValueError(f"Base directory is not a directory: {resolved}")

        if resolved.is_symlink():
            raise ValueError(f"Base directory cannot be a symlink: {resolved}")

        return resolved

    def _is_safe_path(self, path: Path) -> bool:
        """
        Check if path is safe to delete.

        Security checks:
        - Must be under base_dir
        - Must not contain path traversal (.. / ~)
        - Must match allowed patterns
        - Must not be a symlink to outside base_dir

        Args:
            path: Path to validate

        Returns:
            True if path is safe to delete
        """
        try:
            # Resolve path and check it's under base_dir
            resolved = path.resolve()
            if not str(resolved).startswith(str(self.base_dir)):
                logger.warning(f"Path outside base directory: {path}")
                return False

            # Check path depth (prevent deep traversal)
            relative = resolved.relative_to(self.base_dir)
            if len(relative.parts) > self.MAX_PATH_DEPTH:
                logger.warning(f"Path too deep: {path}")
                return False

            # Check filename against whitelist patterns
            filename = path.name
            if not any(pattern.match(filename) for pattern in self.ALLOWED_PATTERNS):
                return False

            # If it's a symlink, verify target is also safe
            if path.is_symlink():
                target = path.resolve()
                if not str(target).startswith(str(self.base_dir)):
                    logger.warning(f"Symlink points outside base directory: {path}")
                    return False

            return True

        except (ValueError, OSError) as e:
            logger.warning(f"Error validating path {path}: {e}")
            return False

    def _is_old_enough(self, path: Path) -> bool:
        """
        Check if file/directory is older than max_age_seconds.

        Args:
            path: Path to check

        Returns:
            True if path is old enough to delete
        """
        try:
            mtime = path.stat().st_mtime
            age_seconds = time.time() - mtime
            return age_seconds > self.max_age_seconds
        except OSError as e:
            logger.error(f"Error checking age of {path}: {e}")
            return False

    def _get_size(self, path: Path) -> int:
        """
        Get size of file or directory in bytes.

        Args:
            path: Path to measure

        Returns:
            Size in bytes (0 if error)
        """
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                return sum(
                    f.stat().st_size
                    for f in path.rglob('*')
                    if f.is_file()
                )
            return 0
        except OSError:
            return 0

    def _find_temp_files(self) -> Generator[Path, None, None]:
        """
        Find all matching temporary files and directories.

        Yields:
            Paths matching cleanup patterns
        """
        try:
            # Use iterdir() instead of glob() for better performance
            for item in self.base_dir.iterdir():
                if self._is_safe_path(item):
                    yield item
        except OSError as e:
            logger.error(f"Error scanning directory {self.base_dir}: {e}")

    def _delete_path(self, path: Path) -> bool:
        """
        Safely delete a file or directory.

        Args:
            path: Path to delete

        Returns:
            True if deletion successful
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: {path}")
            return True

        try:
            # Get size before deletion
            size = self._get_size(path)

            if path.is_file() or path.is_symlink():
                path.unlink()
                self.stats.files_deleted += 1
                logger.info(f"Deleted file: {path}")
            elif path.is_dir():
                # Delete directory recursively
                for item in path.rglob('*'):
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                        self.stats.files_deleted += 1
                # Remove empty directories bottom-up
                for item in sorted(path.rglob('*'), reverse=True):
                    if item.is_dir():
                        item.rmdir()
                        self.stats.dirs_deleted += 1
                path.rmdir()
                self.stats.dirs_deleted += 1
                logger.info(f"Deleted directory: {path}")

            self.stats.bytes_freed += size
            return True

        except OSError as e:
            logger.error(f"Failed to delete {path}: {e}")
            self.stats.errors += 1
            return False

    def cleanup(self) -> CleanupStats:
        """
        Execute cleanup operation.

        Returns:
            Statistics about cleanup operation
        """
        start_time = time.time()

        logger.info(f"Starting cleanup in {self.base_dir}")
        logger.info(f"Max age: {self.max_age_seconds / 3600:.1f} hours")
        logger.info(f"Dry run: {self.dry_run}")

        # Find and delete old files
        for path in self._find_temp_files():
            if self._is_old_enough(path):
                self._delete_path(path)

        elapsed = time.time() - start_time

        # Report statistics
        logger.info("=" * 60)
        logger.info("Cleanup Summary:")
        logger.info(f"  Files deleted: {self.stats.files_deleted}")
        logger.info(f"  Directories deleted: {self.stats.dirs_deleted}")
        logger.info(f"  Space freed: {self._format_bytes(self.stats.bytes_freed)}")
        logger.info(f"  Errors: {self.stats.errors}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        logger.info("=" * 60)

        return self.stats

    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """
        Format bytes as human-readable string.

        Args:
            bytes_count: Number of bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Clean up temporary files from OpenVoice service',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--base-dir',
        type=Path,
        default=Path('/tmp'),
        help='Base directory to clean'
    )
    parser.add_argument(
        '--max-age-hours',
        type=float,
        default=24.0,
        help='Delete files older than this many hours'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        cleanup = TempFileCleanup(
            base_dir=args.base_dir,
            max_age_hours=args.max_age_hours,
            dry_run=args.dry_run
        )
        stats = cleanup.cleanup()

        # Exit code: 0 if no errors, 1 if errors occurred
        exit(0 if stats.errors == 0 else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(2)


if __name__ == '__main__':
    main()
