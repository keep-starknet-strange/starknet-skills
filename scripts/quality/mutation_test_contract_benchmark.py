#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Mutation:
    mutation_id: str
    path: str
    pattern: str
    replacement: str
    description: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        mutation_id="remove_split_half_owner_guard",
        path="evals/contracts/secure_owned_vault/src/lib.cairo",
        pattern=(
            r"fn split_half\(ref self: ContractState, amount: u128\) \{\n"
            r"\s*assert_only_owner\(@self\);\n"
        ),
        replacement="fn split_half(ref self: ContractState, amount: u128) {\n",
        description="remove owner guard from split_half",
    ),
    Mutation(
        mutation_id="replace_block_timestamp_with_constant",
        path="evals/contracts/secure_upgrade_controller/src/lib.cairo",
        pattern=r"let now = get_block_timestamp\(\);",
        replacement="let now = 0_u64;",
        description="replace timelock time source with constant",
    ),
    Mutation(
        mutation_id="remove_schedule_hash_nonzero_guard",
        path="evals/contracts/secure_upgrade_controller/src/lib.cairo",
        pattern=r'assert!\(new_class_hash != 0, "class_hash_zero"\);',
        replacement="// mutation: removed class hash non-zero guard",
        description="remove non-zero class hash assertion from schedule path",
    ),
    Mutation(
        mutation_id="remove_schedule_eta_nonzero_guard",
        path="evals/contracts/secure_upgrade_controller/src/lib.cairo",
        pattern=r'assert!\(executable_after > 0_u64, "eta_zero"\);',
        replacement="// mutation: removed eta non-zero guard",
        description="remove non-zero eta assertion from schedule path",
    ),
    Mutation(
        mutation_id="replace_divrem_with_div_mod_in_secure_math",
        path="evals/contracts/secure_math_patterns/src/lib.cairo",
        pattern=r"let \(half, rem\) = DivRem::div_rem\(value, 2\);",
        replacement="let half = value / 2;\n        let rem = value % 2;",
        description="replace DivRem with standalone division/modulus",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply deterministic mutations to secure fixtures and assert contract benchmark fails."
    )
    parser.add_argument(
        "--cases",
        default="evals/cases/contract_skill_benchmark.jsonl",
        help="Contract benchmark case pack",
    )
    parser.add_argument("--min-precision", type=float, default=1.0, help="Benchmark precision gate")
    parser.add_argument("--min-recall", type=float, default=1.0, help="Benchmark recall gate")
    parser.add_argument("--min-evaluated", type=int, default=60, help="Benchmark minimum evaluated gate")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Timeout passed through to benchmark runner",
    )
    parser.add_argument(
        "--process-timeout-seconds",
        type=int,
        default=1800,
        help="Maximum wall-clock timeout for each benchmark subprocess",
    )
    return parser.parse_args()


def run_benchmark(
    *,
    repo_root: Path,
    cases: str,
    min_precision: float,
    min_recall: float,
    min_evaluated: int,
    timeout_seconds: int,
    process_timeout_seconds: int,
) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile(prefix="mutation-contract-bench-", suffix=".md") as handle:
        cmd = [
            sys.executable,
            str(repo_root / "scripts/quality/benchmark_contract_skills.py"),
            "--cases",
            cases,
            "--output",
            handle.name,
            "--version",
            "mutation-check",
            "--title",
            "Mutation Contract Skill Benchmark",
            "--min-precision",
            str(min_precision),
            "--min-recall",
            str(min_recall),
            "--min-evaluated",
            str(min_evaluated),
            "--enforce-min-evaluated",
            "--require-tools",
            "--timeout-seconds",
            str(timeout_seconds),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=process_timeout_seconds,
            )
            output = ((proc.stdout or "") + (proc.stderr or "")).strip()
            return proc.returncode, output
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") + (exc.stderr or "")).strip()
            timeout_note = (
                f"FAIL: benchmark subprocess timed out after {process_timeout_seconds}s"
            )
            combined = f"{timeout_note}\n{output}".strip()
            return 124, combined


def apply_mutation(original_text: str, mutation: Mutation) -> str:
    mutated_text, count = re.subn(
        mutation.pattern,
        mutation.replacement,
        original_text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(
            f"mutation {mutation.mutation_id}: pattern not found in {mutation.path}"
        )
    return mutated_text


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]

    failures: list[str] = []
    for mutation in MUTATIONS:
        target = repo_root / mutation.path
        original_text = target.read_text(encoding="utf-8")
        mutated_text = apply_mutation(original_text, mutation)

        try:
            target.write_text(mutated_text, encoding="utf-8")
            code, output = run_benchmark(
                repo_root=repo_root,
                cases=args.cases,
                min_precision=args.min_precision,
                min_recall=args.min_recall,
                min_evaluated=args.min_evaluated,
                timeout_seconds=args.timeout_seconds,
                process_timeout_seconds=args.process_timeout_seconds,
            )
            if code == 0:
                failures.append(
                    f"{mutation.mutation_id}: benchmark unexpectedly passed ({mutation.description})"
                )
            else:
                print(f"OK: mutation caught: {mutation.mutation_id}")
                if output:
                    print(f"  {output.splitlines()[-1]}")
        finally:
            target.write_text(original_text, encoding="utf-8")

    if failures:
        print("FAIL: mutation coverage gaps detected")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"OK: mutation suite passed ({len(MUTATIONS)} mutations all detected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
