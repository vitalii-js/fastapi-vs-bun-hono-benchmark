<!-- Plain text: LinkedIn posts don't render markdown. Attach img/cover.png (or all 4 charts as a carousel). ~1,650 characters. -->

FastAPI vs Hono on Bun: I load-tested both against a real Postgres database. Hono won on throughput in every scenario, but not on every metric.

Same API in both: a static JSON endpoint, plus POST with validation and an INSERT into Postgres 17.
Same Docker CPU limits, same connection pool, best-practice setup on both sides (uvicorn + uvloop + orjson + asyncpg vs Bun.serve + Bun.SQL).
3 × 30 s runs per scenario, 0 errors, and every insert checked against the DB row count.

The results:

→ Static JSON: Hono 2.2–2.9× more req/s (214k vs 85k on 4 CPUs)
→ Inserts on 1 CPU: 27.3k/s vs 8.6k/s, or 3.2×
→ One Hono process on 1 CPU did more inserts than FastAPI with 4 workers on 4 CPUs
→ p99 at 256 connections (1 CPU inserts): 25 ms vs 208 ms
→ Memory: 1.5–2.5× lower for Hono

The part I found most interesting: with 4 CPUs the insert gap shrank to 1.3–1.8×.
FastAPI was still using its full CPU limit, while Hono sat partly idle, waiting on Postgres.
Once your app is fast enough, the database becomes the ceiling.

Where FastAPI did better:
→ Median (p50) latency when overloaded: 4.1 ms vs 8.6 ms (Hono spreads the wait evenly, FastAPI has a long tail)
→ Far steadier throughput between runs (±1.5% vs up to ±15%)

So:
• Throughput per CPU (gateways, BFFs, high-traffic CRUD): Bun + Hono
• ML, data, the Python ecosystem, or a DB-bound API: FastAPI is still a great choice

Full write-up with charts and limitations, plus the open-source repo to rerun it yourself: https://github.com/vitalii-js/fastapi-vs-bun-hono-benchmark

What stack are you running in production, and have you measured where your bottleneck actually is?

#FastAPI #Bun #Hono #Python #TypeScript #Backend #Performance #PostgreSQL
