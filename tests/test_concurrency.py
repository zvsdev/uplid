"""Test thread safety of UPLID generation."""

from __future__ import annotations

import threading
from collections import Counter
from typing import Literal

from uplid import UPLID

from .conftest import UserIdFactory


class TestConcurrentGeneration:
    """Test that concurrent ID generation is thread-safe."""

    def test_concurrent_generation_produces_unique_ids(self) -> None:
        """Multiple threads generating IDs should never produce duplicates."""
        num_threads = 10
        ids_per_thread = 1000
        all_ids: list[str] = []
        lock = threading.Lock()

        def generate_ids() -> None:
            thread_ids = [str(UserIdFactory()) for _ in range(ids_per_thread)]
            with lock:
                all_ids.extend(thread_ids)

        threads = [threading.Thread(target=generate_ids) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have generated exactly num_threads * ids_per_thread IDs
        assert len(all_ids) == num_threads * ids_per_thread

        # All IDs should be unique
        unique_ids = set(all_ids)
        assert len(unique_ids) == len(all_ids), "Duplicate IDs detected in concurrent generation"

    def test_concurrent_generation_with_different_prefixes(self) -> None:
        """Concurrent generation with different prefixes should all be unique."""
        num_per_type = 500
        all_ids: list[str] = []
        lock = threading.Lock()

        def generate_user_ids() -> None:
            ids = [str(UPLID.generate("usr")) for _ in range(num_per_type)]
            with lock:
                all_ids.extend(ids)

        def generate_org_ids() -> None:
            ids = [str(UPLID.generate("org")) for _ in range(num_per_type)]
            with lock:
                all_ids.extend(ids)

        def generate_api_key_ids() -> None:
            ids = [str(UPLID.generate("api_key")) for _ in range(num_per_type)]
            with lock:
                all_ids.extend(ids)

        threads = [
            threading.Thread(target=generate_user_ids),
            threading.Thread(target=generate_user_ids),
            threading.Thread(target=generate_org_ids),
            threading.Thread(target=generate_org_ids),
            threading.Thread(target=generate_api_key_ids),
            threading.Thread(target=generate_api_key_ids),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All IDs should be unique (different prefixes make them distinct anyway,
        # but the underlying UUIDs should also be unique)
        assert len(all_ids) == 6 * num_per_type
        assert len(set(all_ids)) == len(all_ids)

    def test_concurrent_generation_maintains_ordering(self) -> None:
        """IDs generated in sequence within a thread should be chronologically ordered."""
        num_ids = 100
        ids_in_order: list[UPLID[Literal["usr"]]] = []
        lock = threading.Lock()

        def generate_sequential() -> None:
            # Generate IDs one at a time and record them in order
            local_ids = [UserIdFactory() for _ in range(num_ids)]
            with lock:
                ids_in_order.extend(local_ids)

        # Single thread to verify ordering within one thread
        t = threading.Thread(target=generate_sequential)
        t.start()
        t.join()

        # Within the thread, IDs should be in chronological order
        for i in range(len(ids_in_order) - 1):
            assert ids_in_order[i].timestamp <= ids_in_order[i + 1].timestamp

    def test_no_duplicate_uuids_under_contention(self) -> None:
        """Stress test: high contention should not produce duplicate UUIDs."""
        num_threads = 50
        ids_per_thread = 200
        all_uuids: list[str] = []
        lock = threading.Lock()
        barrier = threading.Barrier(num_threads)

        def generate_with_barrier() -> None:
            # Wait for all threads to be ready, then generate simultaneously
            barrier.wait()
            thread_uuids = [str(UPLID.generate("usr").uid) for _ in range(ids_per_thread)]
            with lock:
                all_uuids.extend(thread_uuids)

        threads = [threading.Thread(target=generate_with_barrier) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for duplicates
        uuid_counts = Counter(all_uuids)
        duplicates = {uuid: count for uuid, count in uuid_counts.items() if count > 1}
        assert not duplicates, f"Duplicate UUIDs found: {duplicates}"
