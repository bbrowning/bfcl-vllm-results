#!/usr/bin/env python3
"""
Compare two BFCL test runs and identify regressions and improvements.

Usage:
    python compare_runs.py <baseline_dir> <modified_dir> <test_category> [--model <model_name>]

Examples:
    python compare_runs.py result-non-strict-parser result-chat-tool-fix multi_turn
    python compare_runs.py score-baseline score-chat-tool-fix live_simple --model openai_gpt-oss-120b
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_results_and_scores(base_dir, test_category, model="openai_gpt-oss-120b"):
    """Load result and score files for a test category."""
    result_path = Path(base_dir) / model / test_category / f"BFCL_v4_{test_category}_result.json"
    score_path = Path(base_dir.replace('result-', 'score-')) / model / test_category / f"BFCL_v4_{test_category}_score.json"

    # Try alternative naming
    if not result_path.exists():
        result_path = Path(base_dir) / model / test_category / f"BFCL_v4_{test_category}_base_result.json"
    if not score_path.exists():
        score_path = Path(base_dir.replace('result-', 'score-')) / model / test_category / f"BFCL_v4_{test_category}_base_score.json"

    results = {}
    if result_path.exists():
        with open(result_path) as f:
            results = {json.loads(line)['id']: json.loads(line) for line in f}

    summary = None
    failures = {}
    if score_path.exists():
        with open(score_path) as f:
            lines = f.readlines()
            if lines:
                summary = json.loads(lines[0])
                failures = {json.loads(line)['id']: json.loads(line) for line in lines[1:]}

    return results, summary, failures


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    baseline_dir = sys.argv[1]
    modified_dir = sys.argv[2]
    test_category = sys.argv[3]
    model = "openai_gpt-oss-120b"

    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]

    # Load baseline data
    baseline_results, baseline_summary, baseline_failures = load_results_and_scores(
        baseline_dir, test_category, model
    )

    # Load modified data
    modified_results, modified_summary, modified_failures = load_results_and_scores(
        modified_dir, test_category, model
    )

    if not baseline_results or not modified_results:
        print("Error: Could not find result files")
        sys.exit(1)

    # Calculate passing tests
    baseline_passed = set(baseline_results.keys()) - set(baseline_failures.keys())
    modified_passed = set(modified_results.keys()) - set(modified_failures.keys())

    # Find regressions and improvements
    regressions = baseline_passed & set(modified_failures.keys())
    improvements = set(baseline_failures.keys()) - set(modified_failures.keys())

    # Print summary
    print(f"Comparison: {baseline_dir} → {modified_dir}")
    print(f"Test Category: {test_category}")
    print("=" * 80)

    if baseline_summary:
        print(f"\nBaseline: {baseline_summary['correct_count']} passed / {baseline_summary['total_count']} total ({baseline_summary['accuracy']:.1%})")
    else:
        print(f"\nBaseline: {len(baseline_passed)} passed / {len(baseline_results)} total")

    if modified_summary:
        print(f"Modified: {modified_summary['correct_count']} passed / {modified_summary['total_count']} total ({modified_summary['accuracy']:.1%})")
    else:
        print(f"Modified: {len(modified_passed)} passed / {len(modified_results)} total")

    print(f"\nRegressions (passed → failed): {len(regressions)}")
    print(f"Improvements (failed → passed): {len(improvements)}")
    print(f"Net change: {len(improvements) - len(regressions):+d} tests")

    if regressions:
        print(f"\n\nRegressed test IDs:")
        for test_id in sorted(regressions):
            print(f"  - {test_id}")

    if improvements:
        print(f"\n\nImproved test IDs:")
        for test_id in sorted(improvements):
            print(f"  - {test_id}")

    # Categorize regressions by error type
    if regressions:
        error_types = defaultdict(list)
        for test_id in sorted(regressions):
            if test_id in modified_failures:
                error_type = modified_failures[test_id]['error']['error_type']
                error_types[error_type].append(test_id)

        print(f"\n\nRegressions by Error Type:")
        print("=" * 80)
        for error_type, test_ids in sorted(error_types.items()):
            print(f"\n{error_type}: {len(test_ids)} regressions ({len(test_ids)/len(regressions)*100:.1f}%)")
            for test_id in test_ids:
                print(f"  - {test_id}")


if __name__ == "__main__":
    main()
