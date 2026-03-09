#!/usr/bin/env python3
"""Shared policy constants for contract benchmark tooling."""

from __future__ import annotations

MIN_REPORTABLE_CASES = 60
MIN_CONSECUTIVE_REPORTABLE_RELEASES = 2

# benchmark_contract_skills.py returns these codes in __main__.
BENCHMARK_GATE_FAILURE_EXIT_CODE = 1
BENCHMARK_RUNTIME_ERROR_EXIT_CODE = 2
