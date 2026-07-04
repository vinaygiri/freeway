from __future__ import annotations

from providers.key_pool import KeyPool


def test_single_key_always_returns_same():
    pool = KeyPool(["only"])
    assert [pool.select() for _ in range(3)] == ["only", "only", "only"]


def test_round_robin_rotation():
    pool = KeyPool(["a", "b", "c"])
    assert [pool.select() for _ in range(7)] == ["a", "b", "c", "a", "b", "c", "a"]


def test_dedupes_and_drops_empty_keys():
    pool = KeyPool(["a", "", "a", "b", ""])
    assert pool.keys() == ["a", "b"]
    assert len(pool) == 2


def test_empty_pool_selects_empty_string():
    pool = KeyPool([])
    assert len(pool) == 0
    assert pool.select() == ""
