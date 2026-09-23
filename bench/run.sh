#!/usr/bin/env bash
# Runs the full benchmark matrix. Results go to results/raw/.
# Override for a quick trial: DURATION=5s WARMUP=2s REPS=1 ./bench/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

DURATION=${DURATION:-30s}
WARMUP=${WARMUP:-10s}
REPS=${REPS:-3}
APPS=${APPS:-"fastapi hono"}
ROUNDS=${ROUNDS:-"A B"}
ENDPOINTS=${ENDPOINTS:-"static insert"}
CONCURRENCY=${CONCURRENCY:-"50 256"}

RAW=results/raw
# KEEP_RAW=1 resumes a partial run without deleting earlier results.
[[ ${KEEP_RAW:-0} == 1 ]] || rm -rf "$RAW"
mkdir -p "$RAW"

log() { echo "[$(date +%H:%M:%S)] $*"; }
psql_q() { docker compose exec -T postgres psql -U bench -d bench -tAc "$1"; }

url_for() { [[ $1 == fastapi ]] && echo "http://fastapi:8000" || echo "http://hono:3000"; }

oha_run() { # app endpoint concurrency duration [output]
  local url; url="$(url_for "$1")"
  local args=(-z "$4" -c "$3" --no-tui -w --output-format json)
  if [[ $2 == insert ]]; then
    args+=(-m POST -H "content-type: application/json" -D /bench/payload.json "$url/items")
  else
    args+=("$url/static")
  fi
  docker compose exec -T oha oha "${args[@]}" > "${5:-/dev/null}"
}

sample_stats() { # container outfile  (runs until killed)
  while true; do
    docker stats --no-stream --format '{{json .}}' "$1" "$(docker compose ps -q oha)" "$(docker compose ps -q postgres)" >> "$2" 2>/dev/null || true
  done
}

# Never leave a stats sampler running if the script dies.
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

docker compose up -d --wait postgres oha
{
  echo "date: $(date -u +%FT%TZ)"
  echo "host: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m)"
  echo "docker: $(docker version --format '{{.Server.Version}}') vm_cpus=$(docker info --format '{{.NCPU}}')"
  echo "duration=$DURATION warmup=$WARMUP reps=$REPS"
} > results/env.txt.new && { [[ ${KEEP_RAW:-0} == 1 && -f results/env.txt ]] && rm results/env.txt.new || mv results/env.txt.new results/env.txt; }

for round in $ROUNDS; do
  if [[ $round == A ]]; then export WORKERS=1 APP_CPUS=1 APP_MEM=1g
  else                        export WORKERS=4 APP_CPUS=4 APP_MEM=2g; fi

  for app in $APPS; do
    docker compose stop fastapi hono >/dev/null 2>&1 || true
    log "round $round: starting $app (workers=$WORKERS cpus=$APP_CPUS)"
    docker compose up -d --force-recreate --wait "$app" >/dev/null 2>&1
    cid="$(docker compose ps -q "$app")"

    for ep in $ENDPOINTS; do
      for c in $CONCURRENCY; do
        name="${app}_${round}_${ep}_c${c}"
        log "$name: warmup $WARMUP"
        oha_run "$app" "$ep" "$c" "$WARMUP"

        for rep in $(seq 1 "$REPS"); do
          psql_q "TRUNCATE items RESTART IDENTITY" >/dev/null
          sample_stats "$cid" "$RAW/${name}_r${rep}.stats.jsonl" &
          spid=$!
          oha_run "$app" "$ep" "$c" "$DURATION" "$RAW/${name}_r${rep}.json"
          kill "$spid" 2>/dev/null; wait "$spid" 2>/dev/null || true

          summary=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); s=d['summary']; print(f\"{s['requestsPerSec']:.0f} rps, p99 {d['latencyPercentiles']['p99']*1000:.2f} ms, ok {s['successRate']*100:.2f}%\")" "$RAW/${name}_r${rep}.json")
          if [[ $ep == insert ]]; then
            rows=$(psql_q "SELECT count(*) FROM items")
            ok=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['statusCodeDistribution'].get('201',0))" "$RAW/${name}_r${rep}.json")
            echo "{\"rows\": $rows, \"http_201\": $ok}" > "$RAW/${name}_r${rep}.check.json"
            summary="$summary, rows=$rows 201s=$ok"
          fi
          log "$name r$rep: $summary"
        done
      done
    done
  done
done

docker compose stop fastapi hono >/dev/null 2>&1 || true
log "done. Now run: uv run analysis/report.py"
