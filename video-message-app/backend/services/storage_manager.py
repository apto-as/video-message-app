"""
Storage Manager with Automatic Cleanup Policies

Features:
- Multi-tier storage: Uploads, Processed, Videos
- Retention policies: 7/3/30 days
- Scheduled cleanup: Automatic removal of expired files
- Disk space monitoring: Alerts when storage is low
- Transaction safety: Atomic operations with rollback
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum
import asyncio
import shutil
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Storage Tiers & Retention Policies
# ============================================================================

class StorageTier(str, Enum):
    """Storage tier with different retention policies"""
    UPLOADS = "uploads"           # User uploads: 7 days
    PROCESSED = "processed"       # Intermediate files: 3 days
    VIDEOS = "videos"             # Final videos: 30 days
    TEMP = "temp"                 # Temporary files: 1 hour


# Retention policies in days (0 = no automatic cleanup)
RETENTION_POLICIES = {
    StorageTier.UPLOADS: 7,
    StorageTier.PROCESSED: 3,
    StorageTier.VIDEOS: 30,
    StorageTier.TEMP: 1/24,  # 1 hour
}


@dataclass
class FileMetadata:
    """File metadata for tracking"""
    file_path: Path
    tier: StorageTier
    created_at: datetime
    size_bytes: int
    user_id: Optional[str] = None  # User isolation
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "tier": self.tier.value,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "metadata": self.metadata or {}
        }

    def is_expired(self, retention_days: float) -> bool:
        """Check if file has expired based on retention policy"""
        if retention_days == 0:
            return False
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        return self.created_at < cutoff_time


# ============================================================================
# Storage Manager
# ============================================================================

class StorageManager:
    """
    Centralized storage management with automatic cleanup and user isolation

    Directory Structure (User-Isolated):
    storage_root/
    ├── users/
    │   ├── user_123/
    │   │   ├── uploads/      # User uploads (7 days)
    │   │   ├── processed/    # Intermediate files (3 days)
    │   │   ├── videos/       # Generated videos (30 days)
    │   │   └── temp/         # Temporary files (1 hour)
    │   └── user_456/
    │       └── ...
    └── metadata.json         # File tracking metadata

    Legacy Structure (Backward Compatible):
    storage_root/
    ├── uploads/
    ├── processed/
    ├── videos/
    └── temp/

    Security:
    - User isolation prevents cross-user file access
    - Files stored in user-specific directories
    - Metadata tracks user_id for audit trails
    """

    def __init__(
        self,
        storage_root: Path,
        min_free_space_gb: float = 5.0,
        cleanup_interval_minutes: int = 60
    ):
        self.storage_root = Path(storage_root)
        self.min_free_space_gb = min_free_space_gb
        self.cleanup_interval_minutes = cleanup_interval_minutes

        # Initialize directory structure
        for tier in StorageTier:
            tier_dir = self.storage_root / tier.value
            tier_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file
        self.metadata_file = self.storage_root / "metadata.json"
        self._metadata: Dict[str, FileMetadata] = {}
        self._load_metadata()

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        logger.info(f"StorageManager initialized: root={storage_root}")

    def _load_metadata(self):
        """Load file metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._metadata[key] = FileMetadata(
                            file_path=Path(value["file_path"]),
                            tier=StorageTier(value["tier"]),
                            created_at=datetime.fromisoformat(value["created_at"]),
                            size_bytes=value["size_bytes"],
                            user_id=value.get("user_id"),
                            task_id=value.get("task_id"),
                            metadata=value.get("metadata")
                        )
                logger.info(f"Loaded metadata for {len(self._metadata)} files")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self._metadata = {}

    def _save_metadata(self):
        """Save file metadata to disk"""
        try:
            data = {key: meta.to_dict() for key, meta in self._metadata.items()}
            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    async def start(self):
        """Start background cleanup tasks"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("StorageManager background tasks started")

    async def stop(self):
        """Stop background cleanup tasks"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("StorageManager background tasks stopped")

    def get_tier_path(self, tier: StorageTier, user_id: Optional[str] = None) -> Path:
        """
        Get directory path for storage tier (with optional user isolation)

        Args:
            tier: Storage tier
            user_id: User ID for isolation (if None, uses legacy path)

        Returns:
            Path to tier directory
        """
        if user_id:
            # User-isolated path: storage_root/users/{user_id}/{tier}/
            user_path = self.storage_root / "users" / user_id / tier.value
            user_path.mkdir(parents=True, exist_ok=True)
            return user_path
        else:
            # Legacy path: storage_root/{tier}/
            return self.storage_root / tier.value

    async def store_file(
        self,
        source_path: Path,
        tier: StorageTier,
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        move: bool = False
    ) -> Path:
        """
        Store file in specified tier (with user isolation)

        Args:
            source_path: Source file path
            tier: Storage tier
            filename: Optional custom filename
            user_id: User ID for isolation (recommended for multi-tenant security)
            task_id: Associated task ID
            metadata: Additional metadata
            move: If True, move file instead of copy

        Returns:
            Path to stored file
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Determine destination (user-isolated or legacy)
        dest_filename = filename or source_path.name
        dest_path = self.get_tier_path(tier, user_id) / dest_filename

        # Ensure unique filename
        counter = 1
        while dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = self.get_tier_path(tier, user_id) / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            # Copy or move file
            if move:
                shutil.move(str(source_path), str(dest_path))
            else:
                shutil.copy2(str(source_path), str(dest_path))

            # Record metadata (with user_id for isolation)
            file_meta = FileMetadata(
                file_path=dest_path,
                tier=tier,
                created_at=datetime.utcnow(),
                size_bytes=dest_path.stat().st_size,
                user_id=user_id,
                task_id=task_id,
                metadata=metadata
            )

            async with self._lock:
                self._metadata[str(dest_path)] = file_meta
                self._save_metadata()

            logger.info(f"Stored file: {dest_path} ({tier.value})")
            return dest_path

        except Exception as e:
            logger.error(f"Failed to store file: {e}")
            # Cleanup on failure
            if dest_path.exists():
                dest_path.unlink()
            raise

    async def delete_file(self, file_path: Path, remove_metadata: bool = True) -> bool:
        """
        Delete file and optionally remove metadata

        Args:
            file_path: File to delete
            remove_metadata: Remove from metadata tracking

        Returns:
            True if file was deleted
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted file: {file_path}")

            if remove_metadata:
                async with self._lock:
                    self._metadata.pop(str(file_path), None)
                    self._save_metadata()

            return True
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False

    def get_user_files(self, user_id: str, tier: Optional[StorageTier] = None) -> List[FileMetadata]:
        """
        Get all files for a specific user (user isolation helper)

        Args:
            user_id: User ID
            tier: Optional storage tier filter

        Returns:
            List of FileMetadata for user's files
        """
        user_files = [
            meta for meta in self._metadata.values()
            if meta.user_id == user_id
        ]

        if tier:
            user_files = [f for f in user_files if f.tier == tier]

        return user_files

    def verify_user_access(self, file_path: Path, user_id: str) -> bool:
        """
        Verify that a user has access to a file (security check)

        Args:
            file_path: File path to check
            user_id: User ID requesting access

        Returns:
            True if user owns the file, False otherwise
        """
        file_key = str(file_path)
        if file_key not in self._metadata:
            # File not tracked, deny by default
            return False

        meta = self._metadata[file_key]
        # Allow access if:
        # 1. User owns the file (user_id matches)
        # 2. File has no user_id (legacy/shared file)
        return meta.user_id == user_id or meta.user_id is None

    async def cleanup_tier(self, tier: StorageTier) -> Dict[str, Any]:
        """
        Clean up expired files in a tier

        Args:
            tier: Storage tier to clean

        Returns:
            Cleanup statistics
        """
        retention_days = RETENTION_POLICIES[tier]
        if retention_days == 0:
            return {"tier": tier.value, "policy": "no_cleanup", "deleted": 0}

        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0
        freed_bytes = 0

        async with self._lock:
            expired_files = [
                (path, meta) for path, meta in self._metadata.items()
                if meta.tier == tier and meta.created_at < cutoff_time
            ]

        for file_path_str, meta in expired_files:
            file_path = Path(file_path_str)
            if await self.delete_file(file_path, remove_metadata=True):
                deleted_count += 1
                freed_bytes += meta.size_bytes

        logger.info(
            f"Cleaned {tier.value}: {deleted_count} files, "
            f"{freed_bytes / (1024**2):.2f} MB freed"
        )

        return {
            "tier": tier.value,
            "retention_days": retention_days,
            "deleted_files": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024**2), 2)
        }

    async def cleanup_all(self) -> Dict[str, Any]:
        """
        Run cleanup on all tiers

        Returns:
            Combined cleanup statistics
        """
        results = {}
        total_deleted = 0
        total_freed_bytes = 0

        for tier in StorageTier:
            result = await self.cleanup_tier(tier)
            results[tier.value] = result
            total_deleted += result.get("deleted_files", 0)
            total_freed_bytes += result.get("freed_bytes", 0)

        logger.info(
            f"Total cleanup: {total_deleted} files, "
            f"{total_freed_bytes / (1024**2):.2f} MB freed"
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_deleted_files": total_deleted,
            "total_freed_bytes": total_freed_bytes,
            "total_freed_mb": round(total_freed_bytes / (1024**2), 2),
            "tier_details": results
        }

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get current storage statistics"""
        stats = {
            "storage_root": str(self.storage_root),
            "tiers": {},
            "total_files": 0,
            "total_size_bytes": 0
        }

        for tier in StorageTier:
            tier_files = [m for m in self._metadata.values() if m.tier == tier]
            tier_size = sum(m.size_bytes for m in tier_files)
            stats["tiers"][tier.value] = {
                "file_count": len(tier_files),
                "size_bytes": tier_size,
                "size_mb": round(tier_size / (1024**2), 2),
                "retention_days": RETENTION_POLICIES[tier]
            }
            stats["total_files"] += len(tier_files)
            stats["total_size_bytes"] += tier_size

        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024**2), 2)

        # Disk space
        disk_usage = shutil.disk_usage(self.storage_root)
        stats["disk"] = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "percent_used": round((disk_usage.used / disk_usage.total) * 100, 2)
        }

        return stats

    def is_low_storage(self) -> bool:
        """Check if storage space is low"""
        disk_usage = shutil.disk_usage(self.storage_root)
        free_gb = disk_usage.free / (1024**3)
        return free_gb < self.min_free_space_gb

    async def _cleanup_loop(self):
        """Background cleanup task"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)

                logger.info("Running scheduled storage cleanup...")
                result = await self.cleanup_all()

                # Check storage space
                if self.is_low_storage():
                    stats = self.get_storage_stats()
                    logger.warning(
                        f"Low storage space: {stats['disk']['free_gb']} GB free "
                        f"(threshold: {self.min_free_space_gb} GB)"
                    )

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# ============================================================================
# Singleton Instance
# ============================================================================

# Initialize with default storage path
storage_manager = StorageManager(
    storage_root=Path("/app/storage") if Path("/app").exists() else Path("./data/backend/storage")
)
