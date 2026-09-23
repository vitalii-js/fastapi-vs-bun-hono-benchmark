# Results

```
date: 2026-09-23T10:52:27Z
host: Apple M4 Pro
docker: 29.7.2 vm_cpus=14
duration=30s warmup=10s reps=3
```

Median of repetitions. Latency in ms, memory = peak RSS of the app container, CPU in % of one core.

| Endpoint | Setup | Conc. | App | RPS | p50 | p95 | p99 | Errors % | App CPU % | PG CPU % | Peak mem MiB | Spread (min–max RPS) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| static | 1 CPU · 1 process | 50 | fastapi | 23,752 | 1.91 | 3.66 | 4.05 | 0.00 | 100 | 2 | 66 | 23,727–24,071 |
| static | 1 CPU · 1 process | 50 | hono | 68,166 | 0.69 | 0.89 | 1.42 | 0.00 | 98 | 0 | 26 | 67,689–68,466 |
| static | 1 CPU · 1 process | 256 | fastapi | 22,822 | 10.62 | 12.92 | 21.05 | 0.00 | 100 | 2 | 67 | 22,767–22,985 |
| static | 1 CPU · 1 process | 256 | hono | 64,030 | 3.85 | 4.70 | 5.53 | 0.00 | 100 | 0 | 35 | 64,021–64,277 |
| static | 4 CPU · 4 processes | 50 | fastapi | 83,641 | 0.50 | 1.00 | 1.15 | 0.00 | 401 | 0 | 214 | 83,484–84,635 |
| static | 4 CPU · 4 processes | 50 | hono | 185,225 | 0.25 | 0.53 | 0.78 | 0.00 | 401 | 0 | 87 | 184,129–185,946 |
| static | 4 CPU · 4 processes | 256 | fastapi | 84,847 | 2.92 | 3.90 | 6.29 | 0.00 | 401 | 0 | 227 | 84,563–85,831 |
| static | 4 CPU · 4 processes | 256 | hono | 214,385 | 1.10 | 1.63 | 2.69 | 0.00 | 353 | 2 | 87 | 212,827–217,103 |
| insert | 1 CPU · 1 process | 50 | fastapi | 8,629 | 4.03 | 13.35 | 21.32 | 0.00 | 99 | 65 | 64 | 8,151–8,712 |
| insert | 1 CPU · 1 process | 50 | hono | 27,343 | 1.74 | 2.42 | 3.01 | 0.00 | 101 | 165 | 41 | 27,198–27,405 |
| insert | 1 CPU · 1 process | 256 | fastapi | 8,401 | 4.06 | 128.27 | 208.32 | 0.00 | 98 | 61 | 68 | 8,186–8,431 |
| insert | 1 CPU · 1 process | 256 | hono | 22,814 | 8.58 | 23.68 | 24.75 | 0.00 | 81 | 138 | 45 | 21,707–29,837 |
| insert | 4 CPU · 4 processes | 50 | fastapi | 22,636 | 2.17 | 3.50 | 4.71 | 0.00 | 413 | 214 | 221 | 21,754–23,063 |
| insert | 4 CPU · 4 processes | 50 | hono | 40,459 | 1.10 | 1.76 | 2.43 | 0.00 | 321 | 280 | 151 | 39,112–45,373 |
| insert | 4 CPU · 4 processes | 256 | fastapi | 22,335 | 11.97 | 23.82 | 32.82 | 0.00 | 414 | 206 | 223 | 22,084–22,469 |
| insert | 4 CPU · 4 processes | 256 | hono | 29,914 | 5.77 | 23.57 | 30.32 | 0.00 | 236 | 204 | 156 | 27,692–33,721 |

## Hono vs FastAPI

| Endpoint | Setup | Conc. | RPS ratio (Hono / FastAPI) | p99 FastAPI | p99 Hono |
|---|---|---|---:|---:|---:|
| static | 1 CPU · 1 process | 50 | **2.87×** | 4.05 ms | 1.42 ms |
| static | 1 CPU · 1 process | 256 | **2.81×** | 21.05 ms | 5.53 ms |
| static | 4 CPU · 4 processes | 50 | **2.21×** | 1.15 ms | 0.78 ms |
| static | 4 CPU · 4 processes | 256 | **2.53×** | 6.29 ms | 2.69 ms |
| insert | 1 CPU · 1 process | 50 | **3.17×** | 21.32 ms | 3.01 ms |
| insert | 1 CPU · 1 process | 256 | **2.72×** | 208.32 ms | 24.75 ms |
| insert | 4 CPU · 4 processes | 50 | **1.79×** | 4.71 ms | 2.43 ms |
| insert | 4 CPU · 4 processes | 256 | **1.34×** | 32.82 ms | 30.32 ms |

Insert integrity: max |rows in DB − HTTP 201 count| across all runs = **0**.

Load generator (oha) peak CPU: 219% of a 600% budget.
