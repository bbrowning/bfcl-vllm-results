#!/usr/bin/env python3
"""
Extract detailed information about a specific test from BFCL result and score files.

Usage:
    python extract_test.py <result_dir> <test_id> [--model <model_name>]

Examples:
    python extract_test.py result-chat-tool-fix multi_turn_base_104
    python extract_test.py result-baseline live_simple_12 --model openai_gpt-oss-120b
"""

import json
import sys
from pathlib import Path


def find_test_category(test_id):
    """Determine test category from test ID."""
    if "multi_turn" in test_id:
        return "multi_turn"
    elif "live_simple" in test_id:
        return "live"
    elif "live_multiple" in test_id:
        return "live"
    elif "live_irrelevance" in test_id:
        return "live"
    else:
        # Try to infer from other patterns
        for category in ["simple", "multiple", "parallel", "relevance", "rest", "sql", "java"]:
            if category in test_id:
                return category
    return None


def load_test_from_files(base_dir, test_id, model="openai_gpt-oss-120b"):
    """Search for test in result and score files."""
    category = find_test_category(test_id)

    if not category:
        print(f"Could not determine test category from ID: {test_id}")
        print("Searching all files...")

    # Search in possible locations
    search_paths = []
    if category:
        search_paths.append(Path(base_dir) / model / category)

    # Also search common locations
    search_paths.extend([
        Path(base_dir) / model / "multi_turn",
        Path(base_dir) / model / "live",
    ])

    test_data = None
    found_in = None

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for result_file in search_path.glob("*_result.json"):
            with open(result_file) as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('id') == test_id:
                        test_data = data
                        found_in = str(result_file)
                        break
            if test_data:
                break

        if test_data:
            break

    if not test_data:
        return None, None, None

    # Check if test failed (in score file)
    score_file = Path(found_in.replace('result-', 'score-').replace('_result.json', '_score.json'))
    failure_data = None

    if score_file.exists():
        with open(score_file) as f:
            lines = f.readlines()
            for line in lines[1:]:  # Skip summary line
                data = json.loads(line)
                if data.get('id') == test_id:
                    failure_data = data
                    break

    return test_data, failure_data, found_in


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    result_dir = sys.argv[1]
    test_id = sys.argv[2]
    model = "openai_gpt-oss-120b"

    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]

    test_data, failure_data, found_in = load_test_from_files(result_dir, test_id, model)

    if not test_data:
        print(f"Test not found: {test_id}")
        sys.exit(1)

    print(f"Test ID: {test_id}")
    print(f"Found in: {found_in}")
    print("=" * 80)

    if failure_data:
        print(f"\nStatus: FAILED")
        print(f"\nError Type: {failure_data['error']['error_type']}")
        print(f"Error Message: {failure_data['error']['error_message']}")

        if 'prompt' in failure_data:
            print(f"\nPrompt:")
            print(json.dumps(failure_data['prompt'], indent=2))

        if 'model_result_decoded' in failure_data:
            print(f"\nModel Result (decoded):")
            print(json.dumps(failure_data['model_result_decoded'], indent=2))

        if 'possible_answer' in failure_data:
            print(f"\nExpected Answer:")
            print(json.dumps(failure_data['possible_answer'], indent=2))
    else:
        print(f"\nStatus: PASSED")

        if 'prompt' in test_data:
            print(f"\nPrompt:")
            print(json.dumps(test_data['prompt'], indent=2))

        if 'model_result_decoded' in test_data:
            print(f"\nModel Result (decoded):")
            print(json.dumps(test_data['model_result_decoded'], indent=2))


if __name__ == "__main__":
    main()
