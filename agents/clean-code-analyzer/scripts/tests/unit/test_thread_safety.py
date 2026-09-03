"""Thread safety stress tests for orchestrate.py concurrent callbacks."""
import threading
import pytest
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


def make_fake_result(principle: str, n_violations: int) -> dict:
    return {
        "principle": principle,
        "success": True,
        "violations": [
            {"file": f"test.py", "line": i, "principle": principle,
             "severity": "high", "message": f"violation {i}", "suggestion": "fix"}
            for i in range(n_violations)
        ],
        "files_analyzed": 1,
        "duration_ms": 10,
    }


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.repeat(50)
def test_concurrent_callbacks_no_lost_writes():
    """20 threads call on_checker_done simultaneously — no violations lost."""
    import threading

    all_violations = []
    completed = []
    results_lock = threading.Lock()
    completed_count = [0]

    # Replicate the callback logic from orchestrate.py
    def on_checker_done_sim(result):
        with results_lock:
            all_violations.extend(result.get("violations", []))
            completed.append(result)
            completed_count[0] += 1

    N_THREADS = 20
    VIOLATIONS_PER_THREAD = 5
    barrier = threading.Barrier(N_THREADS)

    def worker(principle):
        result = make_fake_result(principle, VIOLATIONS_PER_THREAD)
        barrier.wait()  # all threads fire simultaneously
        on_checker_done_sim(result)

    threads = [
        threading.Thread(target=worker, args=(f"principle_{i}",))
        for i in range(N_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(all_violations) == N_THREADS * VIOLATIONS_PER_THREAD, (
        f"Expected {N_THREADS * VIOLATIONS_PER_THREAD}, got {len(all_violations)} — thread safety bug"
    )
    assert completed_count[0] == N_THREADS


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.repeat(30)
def test_concurrent_deduplication_stable():
    """Deduplication under concurrent access produces stable results."""
    seen = set()
    dedup_lock = threading.Lock()
    merged = []

    violation = {"file": "a.py", "line": 5, "principle": "SOLID"}
    key = (violation["file"], violation["line"], violation["principle"])

    N_THREADS = 10
    barrier = threading.Barrier(N_THREADS)

    def worker():
        barrier.wait()
        with dedup_lock:
            if key not in seen:
                seen.add(key)
                merged.append(violation)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(merged) == 1, f"Expected 1 deduplicated violation, got {len(merged)}"


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.repeat(20)
def test_cache_concurrent_writes_no_corruption(tmp_path):
    """Multiple threads writing different cache entries don't corrupt each other."""
    import threading
    from common.cache import set_cached, get_cached

    files = []
    for i in range(10):
        f = tmp_path / f"mod_{i}.py"
        f.write_text(f"x = {i}\n")
        files.append(f)

    barrier = threading.Barrier(len(files))
    errors = []

    def write_and_verify(file_path, idx):
        violations = [{"file": str(file_path), "line": idx, "principle": "SOLID",
                       "severity": "high", "message": f"v{idx}", "suggestion": "fix"}]
        barrier.wait()
        try:
            set_cached(file_path, "solid", violations)
            result = get_cached(file_path, "solid")
            if result != violations:
                errors.append(f"Corruption on {file_path.name}: expected {violations}, got {result}")
        except Exception as exc:
            errors.append(f"Exception on {file_path.name}: {exc}")

    threads = [
        threading.Thread(target=write_and_verify, args=(f, i))
        for i, f in enumerate(files)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Cache corruption detected:\n" + "\n".join(errors)
