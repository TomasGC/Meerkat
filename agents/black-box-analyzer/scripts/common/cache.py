#!/usr/bin/env python3
"""Incremental analysis cache for faster repeated runs.

Caches analysis results based on file hashes to avoid re-analyzing unchanged files.

Performance:
- First run: ~2 minutes (full analysis)
- Cached run (no changes): ~5 seconds (load from cache)
- Incremental run (10% changed): ~20 seconds (re-analyze changed only)
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AnalysisResult, Endpoint, Scenario, TestCase

# Source globs per language. Previously duplicated inline in both
# get_cached_endpoints and save_endpoints, where the two copies could drift.
_SOURCE_FILE_PATTERNS = {
    "go": ["*.go"],
    "typescript": ["*.ts", "*.tsx"],
    "javascript": ["*.js", "*.jsx"],
    "csharp": ["*.cs"],
    "python": ["*.py"],
    "java": ["*.java"],
}

_FALLBACK_SOURCE_PATTERNS = ["*.go"]
_FALLBACK_TEST_PATTERNS = ["*_test.go"]

_CACHE_ENV_VAR = "BBA_CACHE_DIR"
_MODEL_SUBDIR = "models"


def _cache_home() -> Path:
    """Cache root, overridable via BBA_CACHE_DIR.

    Read on every call rather than captured at import time so tests (including
    subprocess-based ones) can redirect it away from the real user cache.
    """
    override = os.environ.get(_CACHE_ENV_VAR)
    return Path(override) if override else Path.home() / ".cache" / "black-box-analyzer"


class AnalysisCache:
    """Cache for analysis results with file hash-based invalidation."""

    def __init__(self, cache_dir: Path | None = None, project_path: Path | None = None):
        """
        Initialize cache.

        Args:
            cache_dir: Cache directory (default: ~/.cache/black-box-analyzer)
            project_path: Project root — used to scope cache per project (avoids cross-project pollution)
        """
        if cache_dir is None:
            base = _cache_home()
            if project_path is not None:
                # Scope by a short hash of the absolute project path
                project_slug = hashlib.sha256(str(project_path.resolve()).encode()).hexdigest()[:12]
                cache_dir = base / project_slug
            else:
                cache_dir = base

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache files (JSON for security)
        self.endpoints_cache = self.cache_dir / "endpoints.json"
        self.tests_cache = self.cache_dir / "tests.json"
        self.scenarios_cache = self.cache_dir / "scenarios.json"
        self.metadata_cache = self.cache_dir / "metadata.json"

    def _hash_file(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.sha256()

        try:
            with file_path.open("rb") as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError):
            return ""

    def _hash_directory(self, directory: Path, patterns: list[str]) -> dict[str, str]:
        """
        Calculate hashes for all files matching patterns in directory.

        Args:
            directory: Root directory
            patterns: Glob patterns to match

        Returns:
            Dict mapping relative file paths to hashes
        """
        from .utils import walk_files

        file_hashes = {}

        for pattern in patterns:
            for file_path in walk_files(directory, [pattern]):
                relative_path = str(file_path.relative_to(directory))
                file_hash = self._hash_file(file_path)
                if file_hash:
                    file_hashes[relative_path] = file_hash

        return file_hashes

    def _source_patterns(self, language: str) -> list[str]:
        """Source globs for a language."""
        return _SOURCE_FILE_PATTERNS.get(language, _FALLBACK_SOURCE_PATTERNS)

    def _test_patterns(self, language: str) -> list[str]:
        """Test globs for a language."""
        from .constants import TEST_FILE_PATTERNS

        return TEST_FILE_PATTERNS.get(language, _FALLBACK_TEST_PATTERNS)

    def _all_cache_files(self) -> list[Path]:
        """Every file this cache owns, including per-analyzer results."""
        return [
            self.endpoints_cache,
            self.tests_cache,
            self.scenarios_cache,
            self.metadata_cache,
            *self.cache_dir.glob("result_*.json"),
        ]

    def _result_cache_path(self, analyzer: str) -> Path:
        """Cache file holding one analyzer's AnalysisResult."""
        return self.cache_dir / f"result_{re.sub(r'[^A-Za-z0-9_.-]', '_', analyzer)}.json"

    def get_cached_result(
        self, project_path: Path, language: str, analyzer: str
    ) -> AnalysisResult | None:
        """
        Get one analyzer's cached result, or None if the cache is stale.

        Validity requires the language plus every source and test file hash to
        match what was recorded at save time, so any edit to the project
        invalidates the entry.

        Args:
            project_path: Project root directory
            language: Programming language
            analyzer: Analyzer name (one cache entry per analyzer)

        Returns:
            Cached AnalysisResult or None if cache invalid
        """
        cache_path = self._result_cache_path(analyzer)
        if not cache_path.exists():
            return None

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if payload.get("language") != language:
            return None

        source_hashes = self._hash_directory(project_path, self._source_patterns(language))
        if payload.get("source_file_hashes") != source_hashes:
            return None

        test_hashes = self._hash_directory(project_path, self._test_patterns(language))
        if payload.get("test_file_hashes") != test_hashes:
            return None

        try:
            return AnalysisResult.from_dict(payload["result"])
        except (KeyError, TypeError, ValueError):
            # Schema drift between versions - treat as a miss rather than crash
            return None

    def save_result(
        self, project_path: Path, language: str, analyzer: str, result: AnalysisResult
    ) -> None:
        """
        Save one analyzer's result, recording the hashes that validate it.

        Args:
            project_path: Project root directory
            language: Programming language
            analyzer: Analyzer name (one cache entry per analyzer)
            result: Analysis result to cache
        """
        cached_at = datetime.now().isoformat()
        payload = {
            "language": language,
            "analyzer": analyzer,
            "cached_at": cached_at,
            "source_file_hashes": self._hash_directory(
                project_path, self._source_patterns(language)
            ),
            "test_file_hashes": self._hash_directory(project_path, self._test_patterns(language)),
            "result": result.to_dict(),
        }

        try:
            self._result_cache_path(analyzer).write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except OSError:
            # Cache writes are best-effort; a failure must not fail the analysis
            return

        metadata = self._load_metadata()
        metadata["language"] = language
        metadata.setdefault("results_cached_at", {})[analyzer] = cached_at
        self._save_metadata(metadata)

    def get_cached_endpoints(
        self, project_path: Path, language: str
    ) -> list[Endpoint] | None:
        """
        Get cached endpoints if source files unchanged.

        Args:
            project_path: Project root directory
            language: Programming language

        Returns:
            Cached endpoints or None if cache invalid
        """
        if not self.endpoints_cache.exists() or not self.metadata_cache.exists():
            return None

        # Load metadata
        try:
            metadata = json.loads(self.metadata_cache.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check if language matches
        if metadata.get("language") != language:
            return None

        # Get current file hashes
        current_hashes = self._hash_directory(project_path, self._source_patterns(language))

        # Compare with cached hashes
        cached_hashes = metadata.get("source_file_hashes", {})

        if current_hashes != cached_hashes:
            # Source files changed, cache invalid
            return None

        # Load cached endpoints
        try:
            endpoints_data = json.loads(self.endpoints_cache.read_text(encoding="utf-8"))
            return [Endpoint.from_dict(ep) for ep in endpoints_data]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def save_endpoints(
        self, project_path: Path, language: str, endpoints: list[Endpoint]
    ):
        """
        Save endpoints to cache.

        Args:
            project_path: Project root directory
            language: Programming language
            endpoints: Endpoints to cache
        """
        # Calculate source file hashes
        source_hashes = self._hash_directory(project_path, self._source_patterns(language))

        # Convert endpoints to JSON
        endpoints_data = [ep.to_dict() for ep in endpoints]

        # Save endpoints
        self.endpoints_cache.write_text(json.dumps(endpoints_data, indent=2), encoding="utf-8")

        # Update metadata
        metadata = self._load_metadata()
        metadata["language"] = language
        metadata["source_file_hashes"] = source_hashes
        metadata["endpoints_cached_at"] = datetime.now().isoformat()
        self._save_metadata(metadata)

    def get_cached_tests(self, project_path: Path, language: str) -> list[TestCase] | None:
        """
        Get cached test cases if test files unchanged.

        Args:
            project_path: Project root directory
            language: Programming language

        Returns:
            Cached test cases or None if cache invalid
        """
        if not self.tests_cache.exists() or not self.metadata_cache.exists():
            return None

        # Load metadata
        try:
            metadata = json.loads(self.metadata_cache.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check if language matches
        if metadata.get("language") != language:
            return None

        # Get current test file hashes
        current_hashes = self._hash_directory(project_path, self._test_patterns(language))

        # Compare with cached hashes
        cached_hashes = metadata.get("test_file_hashes", {})

        if current_hashes != cached_hashes:
            # Test files changed, cache invalid
            return None

        # Load cached tests
        try:
            tests_data = json.loads(self.tests_cache.read_text(encoding="utf-8"))
            return [TestCase.from_dict(tc) for tc in tests_data]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def save_tests(self, project_path: Path, language: str, tests: list[TestCase]):
        """
        Save test cases to cache.

        Args:
            project_path: Project root directory
            language: Programming language
            tests: Test cases to cache
        """
        # Calculate test file hashes
        test_hashes = self._hash_directory(project_path, self._test_patterns(language))

        # Convert tests to JSON
        tests_data = [t.to_dict() for t in tests]

        # Save tests
        self.tests_cache.write_text(json.dumps(tests_data, indent=2), encoding="utf-8")

        # Update metadata
        metadata = self._load_metadata()
        metadata["language"] = language
        metadata["test_file_hashes"] = test_hashes
        metadata["tests_cached_at"] = datetime.now().isoformat()
        self._save_metadata(metadata)

    def get_cached_scenarios(self, endpoints_hash: str) -> list | None:
        """
        Get cached scenarios if endpoints unchanged.

        Args:
            endpoints_hash: Hash of endpoints JSON

        Returns:
            Cached scenarios or None if cache invalid
        """
        if not self.scenarios_cache.exists() or not self.metadata_cache.exists():
            return None

        # Load metadata
        try:
            metadata = json.loads(self.metadata_cache.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check if endpoints hash matches
        if metadata.get("endpoints_hash") != endpoints_hash:
            return None

        # Load cached scenarios
        try:
            scenarios_data = json.loads(self.scenarios_cache.read_text(encoding="utf-8"))
            return [Scenario.from_dict(s) for s in scenarios_data]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def save_scenarios(self, endpoints_hash: str, scenarios: list):
        """
        Save scenarios to cache.

        Args:
            endpoints_hash: Hash of endpoints JSON
            scenarios: Scenarios to cache
        """
        # Convert scenarios to JSON
        scenarios_data = [s.to_dict() for s in scenarios]

        # Save scenarios
        self.scenarios_cache.write_text(json.dumps(scenarios_data, indent=2), encoding="utf-8")

        # Update metadata
        metadata = self._load_metadata()
        metadata["endpoints_hash"] = endpoints_hash
        metadata["scenarios_cached_at"] = datetime.now().isoformat()
        self._save_metadata(metadata)

    def invalidate_all(self, include_projects: bool = False):
        """Invalidate cache files.

        Args:
            include_projects: Also clear every project-scoped subdirectory.
                Required when this instance points at the unscoped base
                directory, whose own files stay empty because every real run
                writes to a per-project subdirectory below it.
        """
        for cache_file in self._all_cache_files():
            if cache_file.exists():
                cache_file.unlink()

        if include_projects:
            for sub in self.cache_dir.iterdir():
                if sub.is_dir() and sub.name != _MODEL_SUBDIR:
                    AnalysisCache(cache_dir=sub).invalidate_all()

        print(f"Cache invalidated: {self.cache_dir}", file=sys.stderr)

    def get_cache_info(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache info (size, timestamps, hit rates)
        """
        if not self.metadata_cache.exists():
            return {"status": "empty"}

        metadata = self._load_metadata()

        # Calculate cache size
        total_size = sum(f.stat().st_size for f in self._all_cache_files() if f.exists())

        return {
            "status": "active",
            "cache_dir": str(self.cache_dir),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "language": metadata.get("language"),
            "endpoints_cached_at": metadata.get("endpoints_cached_at"),
            "tests_cached_at": metadata.get("tests_cached_at"),
            "scenarios_cached_at": metadata.get("scenarios_cached_at"),
            "source_file_count": len(metadata.get("source_file_hashes", {})),
            "test_file_count": len(metadata.get("test_file_hashes", {})),
            "cached_analyzers": sorted(metadata.get("results_cached_at", {})),
        }

    def _load_metadata(self) -> dict[str, Any]:
        """Load metadata from cache."""
        if not self.metadata_cache.exists():
            return {}

        try:
            return json.loads(self.metadata_cache.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_metadata(self, metadata: dict[str, Any]):
        """Save metadata to cache."""
        self.metadata_cache.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-file local AI result cache (separate from AnalysisCache)
# ---------------------------------------------------------------------------
import time  # noqa: E402


def _model_cache_dir() -> Path:
    """Model-result cache directory (honours BBA_CACHE_DIR)."""
    return _cache_home() / _MODEL_SUBDIR


def _model_file_hash(file_path: Path) -> str:
    try:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "nohash"


def get_model_cached(file_path: Path, analyzer: str, max_age_days: int = 7) -> list[dict] | None:
    """Return cached local AI results, or None if missing/expired."""
    key = f"{_model_file_hash(file_path)}_{analyzer}"
    cache_file = _model_cache_dir() / f"{key}.json"
    if not cache_file.exists():
        return None
    if max_age_days > 0:
        age_seconds = time.time() - cache_file.stat().st_mtime
        if age_seconds > max_age_days * 86400:
            try:
                cache_file.unlink()
            except OSError:
                pass
            return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def set_model_cached(file_path: Path, analyzer: str, results: list[dict]) -> None:
    """Cache local AI results for file+analyzer."""
    model_dir = _model_cache_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    key = f"{_model_file_hash(file_path)}_{analyzer}"
    cache_file = model_dir / f"{key}.json"
    try:
        cache_file.write_text(json.dumps(results), encoding="utf-8")
    except OSError:
        pass


def clear_model_cache() -> int:
    """Clear all local AI cached results. Returns number of entries deleted."""
    model_dir = _model_cache_dir()
    if not model_dir.exists():
        return 0
    count = 0
    for f in model_dir.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count
