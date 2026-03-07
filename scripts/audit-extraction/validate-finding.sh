#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <finding.json>" >&2
  exit 1
fi

FILE="$1"

required=(
  finding_id
  source_audit
  severity
  file_path
  function_name
  root_cause
  exploit_path
  vulnerable_pattern
  fixed_pattern
  detection_rule
  false_positive_caveat
  required_test
  provenance
  confidence
)

for key in "${required[@]}"; do
  jq -e --arg k "$key" 'has($k) and .[$k] != null and .[$k] != ""' "$FILE" >/dev/null || {
    echo "Missing required field: $key" >&2
    exit 1
  }
done

echo "OK: $FILE"
