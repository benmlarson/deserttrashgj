#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CREDS_FILE="$SCRIPT_DIR/.local-credentials.json"

if [ $# -ne 1 ] || [[ ! "$1" =~ ^(admin|user)$ ]]; then
  echo "Usage: $0 <admin|user>" >&2
  exit 1
fi

if [ ! -f "$CREDS_FILE" ]; then
  echo "Error: $CREDS_FILE not found" >&2
  exit 1
fi

ROLE="$1"
EMAIL=$(python3 -c "import json,sys; creds=json.load(open('$CREDS_FILE')); print(next(c['email'] for c in creds if c['role']=='$ROLE'))")
PASS=$(python3 -c "import json,sys; creds=json.load(open('$CREDS_FILE')); print(next(c['password'] for c in creds if c['role']=='$ROLE'))")

echo "$EMAIL / $PASS"
