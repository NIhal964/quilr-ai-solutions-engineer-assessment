import time
import aiosqlite


class SQLiteTokenSlidingWindow:
    def __init__(self, db_path: str, limit: int = 50_000, window_seconds: int = 60):
        self.db_path = db_path
        self.limit = limit
        self.window_seconds = window_seconds

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    tenant_key TEXT NOT NULL,
                    ts REAL NOT NULL,
                    tokens INTEGER NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_token_usage_tenant_ts ON token_usage(tenant_key, ts)"
            )
            await db.commit()

    async def reserve(self, tenant_key: str, tokens: int) -> tuple[bool, int]:
        if tokens <= 0:
            return True, 0

        now = time.time()
        cutoff = now - self.window_seconds

        # BEGIN IMMEDIATE serializes writers, preventing concurrent requests from
        # both observing the same remaining quota and oversubscribing it.
        async with aiosqlite.connect(self.db_path, timeout=5) as db:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("DELETE FROM token_usage WHERE ts < ?", (cutoff,))

            cursor = await db.execute(
                "SELECT COALESCE(SUM(tokens), 0) FROM token_usage WHERE tenant_key = ? AND ts >= ?",
                (tenant_key, cutoff),
            )
            used = int((await cursor.fetchone())[0])
            remaining = max(0, self.limit - used)

            if tokens > remaining:
                await db.rollback()
                return False, remaining

            await db.execute(
                "INSERT INTO token_usage (tenant_key, ts, tokens) VALUES (?, ?, ?)",
                (tenant_key, now, tokens),
            )
            await db.commit()
            return True, remaining - tokens
