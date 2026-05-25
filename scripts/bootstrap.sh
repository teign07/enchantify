#!/bin/bash
# Compatibility wrapper. The real bootstrap lives at repo root.

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/bootstrap.sh"
