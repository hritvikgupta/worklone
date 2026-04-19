#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-3000}"

wait_for_docker() {
  # Fast path
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  # macOS Docker Desktop recovery
  if [[ "$OSTYPE" == darwin* ]]; then
    echo "Docker daemon is not reachable. Starting Docker Desktop..."
    open -a Docker || true
    for _ in {1..60}; do
      if docker info >/dev/null 2>&1; then
        echo "Docker daemon is ready."
        return 0
      fi
      sleep 2
    done
  fi

  echo "Docker daemon is not reachable. Start Docker Desktop and retry."
  exit 1
}

free_port() {
  local port="$1"
  echo "Checking port ${port}..."

  # Clean up stale compose/orphan containers first.
  docker compose down --remove-orphans >/dev/null 2>&1 || true

  # If a Docker container is publishing this port, stop it cleanly first.
  if docker info >/dev/null 2>&1; then
    docker_ids="$(docker ps --filter "publish=${port}" -q)"
    if [[ -n "${docker_ids:-}" ]]; then
      echo "Stopping Docker container(s) using port ${port}: ${docker_ids}"
      docker stop ${docker_ids} >/dev/null 2>&1 || true
    fi
  fi

  # Final fallback for any remaining non-Docker process
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN -ti >/dev/null 2>&1; then
    echo "Force-killing remaining process(es) on port ${port}..."
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -ti | xargs kill -9
    sleep 1
  fi

  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN -ti >/dev/null 2>&1; then
    echo "Port ${port} is still occupied after cleanup. Please free it manually and retry."
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN
    exit 1
  fi

  echo "Port ${port} is free."
}

wait_for_docker
free_port "${PORT}"

echo "Starting Docker services..."
docker compose up --build --remove-orphans
