import pytest
from task4_rate_limit_router.rate_limiter import SQLiteTokenSlidingWindow


@pytest.mark.asyncio
async def test_sliding_window_rejects_over_limit(tmp_path):
    limiter = SQLiteTokenSlidingWindow(str(tmp_path / "limit.db"), limit=100, window_seconds=60)
    await limiter.initialize()

    ok, remaining = await limiter.reserve("tenant-a", 80)
    assert ok
    assert remaining == 20

    ok, remaining = await limiter.reserve("tenant-a", 21)
    assert not ok
    assert remaining == 20

    ok, remaining = await limiter.reserve("tenant-b", 100)
    assert ok
    assert remaining == 0
