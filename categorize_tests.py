#!/usr/bin/env python3
"""
Analyze BFCL test results across multiple runs to categorize test stability.

Produces:
- Console summary of stable passes, flaky tests, and stable failures
- stable_tests.json: Tests passing in ALL runs, grouped by category
- flaky_tests.json: Tests with mixed results, grouped by category
- failing_tests.json: Tests failing in ALL runs, grouped by category

Usage:
    ./categorize_tests.py <run1> <run2> [run3 ...]

Examples:
    ./categorize_tests.py baseline v0.11.0
    ./categorize_tests.py results/baseline results/v0.11.0
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple

def get_test_ids_from_result(result_file: Path) -> Set[str]:
    """Extract all test IDs from a result file."""
    test_ids = set()
    if not result_file.exists():
        return test_ids

    with open(result_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if 'id' in data:
                        test_ids.add(data['id'])
                except json.JSONDecodeError:
                    continue
    return test_ids

def get_failed_test_ids_from_score(score_file: Path) -> Set[str]:
    """Extract failing test IDs from a score file (skip first summary line)."""
    failed_ids = set()
    if not score_file.exists():
        return failed_ids

    with open(score_file, 'r') as f:
        next(f, None)  # Skip first line (summary)
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if 'id' in data:
                        failed_ids.add(data['id'])
                except json.JSONDecodeError:
                    continue
    return failed_ids

def normalize_run_name(run_path: str) -> str:
    """
    Normalize run name by stripping 'results/' prefix if present.

    Examples:
        'baseline' -> 'baseline'
        'results/baseline' -> 'baseline'
        'results/v0.11.0' -> 'v0.11.0'
    """
    run_path = run_path.rstrip('/')
    if run_path.startswith('results/'):
        return run_path.replace('results/', '', 1)
    return run_path

def find_categories_for_runs(run_names: List[str]) -> Dict[str, List[str]]:
    """
    Find all test categories for the specified runs.

    Args:
        run_names: List of run names to analyze

    Returns:
        Dict mapping category -> [list of run names that have that category]
    """
    categories = defaultdict(list)
    results_dir = Path('results')

    for run_name in run_names:
        score_dir = results_dir / f'score-{run_name}'

        if not score_dir.exists():
            print(f"Warning: Score directory not found: {score_dir}")
            continue

        for score_file in score_dir.rglob('*_score.json'):
            filename = score_file.name
            category = filename.replace('BFCL_v4_', '').replace('_score.json', '')

            result_dir = results_dir / f'result-{run_name}'
            result_file = result_dir / score_file.relative_to(score_dir).parent / filename.replace('_score.json', '_result.json')

            if result_file.exists():
                categories[category].append(run_name)

    return dict(categories)

def analyze_category(category: str, runs: List[str]) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Analyze a test category across all runs.

    Returns:
        (stable_passes, flaky_tests, stable_failures)
    """
    test_status = defaultdict(lambda: {"passed": 0, "failed": 0, "total_runs": 0})
    results_dir = Path('results')

    for run in runs:
        result_pattern = f"results/result-{run}/**/BFCL_v4_{category}_result.json"
        score_pattern = f"results/score-{run}/**/BFCL_v4_{category}_score.json"

        result_files = list(Path('.').glob(result_pattern))
        score_files = list(Path('.').glob(score_pattern))

        if not result_files or not score_files:
            continue

        result_file = result_files[0]
        score_file = score_files[0]

        all_tests = get_test_ids_from_result(result_file)
        failed_tests = get_failed_test_ids_from_score(score_file)
        passed_tests = all_tests - failed_tests

        for test_id in all_tests:
            test_status[test_id]["total_runs"] += 1
            if test_id in passed_tests:
                test_status[test_id]["passed"] += 1
            else:
                test_status[test_id]["failed"] += 1

    stable_passes = set()
    flaky_tests = set()
    stable_failures = set()

    for test_id, status in test_status.items():
        total = status["total_runs"]
        passed = status["passed"]
        failed = status["failed"]

        if passed == total:
            stable_passes.add(test_id)
        elif failed == total:
            stable_failures.add(test_id)
        else:
            flaky_tests.add(test_id)

    return stable_passes, flaky_tests, stable_failures

def save_json_output(stable_by_category: Dict[str, List[str]],
                    flaky_by_category: Dict[str, List[str]],
                    failing_by_category: Dict[str, List[str]]):
    """Save categorized tests to JSON files."""

    with open('stable_tests.json', 'w') as f:
        json.dump(stable_by_category, f, indent=2, sort_keys=True)

    with open('flaky_tests.json', 'w') as f:
        json.dump(flaky_by_category, f, indent=2, sort_keys=True)

    with open('failing_tests.json', 'w') as f:
        json.dump(failing_by_category, f, indent=2, sort_keys=True)

    print("JSON files created:")
    print("  - stable_tests.json")
    print("  - flaky_tests.json")
    print("  - failing_tests.json")
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: ./categorize_tests.py <run1> <run2> [run3 ...]")
        print()
        print("Examples:")
        print("  ./categorize_tests.py baseline v0.11.0")
        print("  ./categorize_tests.py results/baseline results/v0.11.0")
        print()
        sys.exit(1)

    # Normalize run names (strip 'results/' prefix if present)
    run_names = [normalize_run_name(arg) for arg in sys.argv[1:]]

    print("=" * 80)
    print("BFCL Test Categorization Analysis")
    print("=" * 80)
    print(f"Analyzing runs: {', '.join(run_names)}")
    print()

    categories = find_categories_for_runs(run_names)

    if not categories:
        print("No test categories found!")
        print("Make sure the following directories exist:")
        for run_name in run_names:
            print(f"  - results/score-{run_name}")
            print(f"  - results/result-{run_name}")
        return

    stable_by_category = {}
    flaky_by_category = {}
    failing_by_category = {}

    all_stable_count = 0
    all_flaky_count = 0
    all_failing_count = 0

    print("Analyzing categories:")
    print("-" * 80)

    for category in sorted(categories.keys()):
        runs = categories[category]
        stable_passes, flaky, stable_failures = analyze_category(category, runs)

        stable_by_category[category] = sorted(list(stable_passes))
        flaky_by_category[category] = sorted(list(flaky))
        failing_by_category[category] = sorted(list(stable_failures))

        all_stable_count += len(stable_passes)
        all_flaky_count += len(flaky)
        all_failing_count += len(stable_failures)

        total_tests = len(stable_passes) + len(flaky) + len(stable_failures)

        print(f"\n{category}")
        print(f"  Runs analyzed: {len(runs)} ({', '.join(runs)})")
        print(f"  Total tests: {total_tests}")
        print(f"  Stable passes: {len(stable_passes):4d} ({len(stable_passes)/total_tests*100:5.1f}%)")
        print(f"  Flaky tests:   {len(flaky):4d} ({len(flaky)/total_tests*100:5.1f}%)")
        print(f"  Stable fails:  {len(stable_failures):4d} ({len(stable_failures)/total_tests*100:5.1f}%)")

    print()
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    total_all = all_stable_count + all_flaky_count + all_failing_count
    print(f"Total unique tests across all categories: {total_all}")
    print(f"  Stable passes: {all_stable_count:4d} ({all_stable_count/total_all*100:5.1f}%)")
    print(f"  Flaky tests:   {all_flaky_count:4d} ({all_flaky_count/total_all*100:5.1f}%)")
    print(f"  Stable fails:  {all_failing_count:4d} ({all_failing_count/total_all*100:5.1f}%)")
    print()

    save_json_output(stable_by_category, flaky_by_category, failing_by_category)

    print("=" * 80)
    print("Top insights:")
    print("-" * 80)

    most_flaky = max(categories.keys(),
                     key=lambda c: len(flaky_by_category[c]) / max(1, len(stable_by_category[c]) + len(flaky_by_category[c]) + len(failing_by_category[c])))
    most_stable = max(categories.keys(),
                      key=lambda c: len(stable_by_category[c]) / max(1, len(stable_by_category[c]) + len(flaky_by_category[c]) + len(failing_by_category[c])))

    print(f"Most flaky category: {most_flaky}")
    print(f"  {len(flaky_by_category[most_flaky])} flaky tests")
    print()
    print(f"Most stable category: {most_stable}")
    print(f"  {len(stable_by_category[most_stable])} stable passing tests")
    print()

if __name__ == "__main__":
    main()
