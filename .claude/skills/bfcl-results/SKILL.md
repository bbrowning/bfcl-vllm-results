---
name: Interpreting BFCL Results
description: Use when analyzing Berkeley Function Calling Leaderboard (BFCL) benchmark results. Explains BFCL's two-file structure (result and score files), how to interpret accuracy metrics, compare runs, categorize test stability across multiple runs, identify regressions, and understand multi-turn test failures. Essential for correctly interpreting pass/fail counts, analyzing flaky tests, and finding example test cases.
---

# Interpreting BFCL Results

This skill provides expert knowledge for analyzing Berkeley Function Calling Leaderboard (BFCL) benchmark results.

## BFCL File Structure

BFCL produces **two types of files** for each test category:

### 1. Result Files (e.g., `BFCL_v4_multi_turn_base_result.json`)
- **Contains**: ALL tests that were run, with raw model outputs
- **Format**: One JSON object per line (JSONL)
- **Size**: Typically large (1-2MB+)
- **Content**: Model responses, token counts, latency, inference logs

### 2. Score Files (e.g., `BFCL_v4_multi_turn_base_score.json`)
- **Contains**: ONLY tests that FAILED, plus a summary line
- **Format**: JSONL with summary as first line
- **Line 1**: Summary - `{"accuracy": 0.6, "correct_count": 120, "total_count": 200}`
- **Lines 2+**: Failed test details with `"valid": false` and error information
- **CRITICAL**: Passing tests are NOT included in this file

## Understanding the Numbers

When you see a summary line like:
```json
{"accuracy": 0.6, "correct_count": 120, "total_count": 200}
```

Here's what it means:
- `total_count`: Total tests in the suite (from result file)
- `correct_count`: Tests that PASSED (not in score file)
- Number of lines in score file - 1 = Tests that FAILED
- **Passed tests**: `total_count - (score file lines - 1)`

### Example Calculation
```bash
# Count tests in files
wc -l result.json  # 200 lines = 200 total tests
wc -l score.json   # 81 lines = 1 summary + 80 failures

# Therefore:
# - 200 total tests ran
# - 80 tests failed (in score file)
# - 120 tests passed (NOT in score file)
# - Accuracy: 120/200 = 60%
```

## Common Confusion: "Where are the passing tests?"

**They're only in the result file, not in the score file.**

To find a passing test:
1. Get test IDs from result file: `jq -r '.id' result.json`
2. Check if in score file: `grep "test_id" score.json`
3. If NOT found in score file → test passed
4. If found in score file → test failed

## Comparing Two Runs

When comparing baseline vs modified runs:

### 1. Check Test Completion
```bash
wc -l baseline/result.json     # Total tests that ran
wc -l modified/result.json     # May differ if timeouts occurred
```

Different result file sizes mean:
- Modified run completed more/fewer tests (timeouts, crashes)
- Can't directly compare if different tests ran

### 2. Identify Test Differences
```bash
# Tests in both runs
comm -12 <(jq -r '.id' baseline/result.json | sort) \
         <(jq -r '.id' modified/result.json | sort)

# Tests only in baseline
comm -23 <(jq -r '.id' baseline/result.json | sort) \
         <(jq -r '.id' modified/result.json | sort)
```

### 3. Find Regressions
A regression = test passed in baseline, failed in modified

**Process**:
1. Get IDs from baseline result file
2. Get IDs from baseline score file
3. Baseline passing = result IDs - score IDs
4. Get IDs from modified score file
5. Regressions = (baseline passing) ∩ (modified failures)

### 4. Find Improvements
Improvement = test failed in baseline, passed in modified

**Process**:
1. Get baseline failures (from score file)
2. Get modified failures (from score file)
3. Improvements = (baseline failures) - (modified failures)

## Multi-Turn Test Structure

Multi-turn tests simulate conversations with multiple user requests:

```json
{
  "id": "multi_turn_base_104",
  "valid": false,
  "error": {
    "error_type": "multi_turn:execution_response_mismatch",
    "error_message": "Model response execution results..."
  },
  "prompt": {
    "question": [
      [{"role": "user", "content": "Turn 1 request..."}],
      [{"role": "user", "content": "Turn 2 request..."}]
    ]
  },
  "model_result_decoded": [...],  // What model did
  "possible_answer": [...]         // What was expected
}
```

### Common Error Types

**`multi_turn:instance_state_mismatch`**
- Model's final state doesn't match expected state
- Example: File has wrong content, watchlist has wrong items

**`multi_turn:execution_response_mismatch`**
- Model called wrong functions or missed required calls
- Example: Should call `get_watchlist()` then `add_to_watchlist()`, but only called `add_to_watchlist()`

**`multi_turn:force_terminated`**
- Test timed out or crashed before completing all turns
- Check: `len(model_result) != len(ground_truth_turns)`

## Quick Reference Commands

```bash
# Count total tests that ran
wc -l result.json

# Count failed tests
wc -l score.json  # Subtract 1 for summary line

# Get test IDs from result file
jq -r '.id' result.json

# Get test IDs from score file (failures only)
tail -n +2 score.json | jq -r '.id'

# Check if specific test passed or failed
test_id="multi_turn_base_104"
if grep -q "\"$test_id\"" score.json; then
  echo "Failed"
else
  echo "Passed (or didn't run)"
fi

# Count valid vs invalid in score file
tail -n +2 score.json | jq -r '.valid' | sort | uniq -c
# Should show all "false" since score file only has failures
```

## Finding Example Test Cases

### To find a test that failed in modified but passed in baseline:

```python
import json

# Load files
with open('baseline/result.json') as f:
    baseline_results = {json.loads(line)['id']: json.loads(line) for line in f}
with open('baseline/score.json') as f:
    lines = f.readlines()
    baseline_failures = {json.loads(line)['id'] for line in lines[1:]}

with open('modified/score.json') as f:
    lines = f.readlines()
    modified_failures = {json.loads(line)['id'] for line in lines[1:]}

# Passed in baseline = in result but not in score
baseline_passed = set(baseline_results.keys()) - baseline_failures

# Regressions = passed in baseline, failed in modified
regressions = baseline_passed & modified_failures

print(f"Regressions: {regressions}")
```

### To show a specific test's details:

```bash
# From score file (if it failed)
grep '"id": "multi_turn_base_104"' score.json | jq .

# From result file (if it passed)
grep '"id": "multi_turn_base_0"' result.json | jq .
```

## Key Insights Summary

1. **Score files only contain failures** - don't expect all tests to be there
2. **Passing tests are only in result files** - check there to verify a test ran
3. **Summary line accuracy = correct_count / total_count** from result file
4. **Different line counts between runs** indicate different test completion rates
5. **A test missing from score file** could mean it passed OR didn't run (check result file)
6. **Multi-turn tests are complex** - read the full error details to understand failures

## Categorizing Tests Across Multiple Runs

When analyzing test stability across multiple BFCL runs, categorize tests into three groups:

1. **Stable passes**: Tests passing in ALL runs where executed
2. **Flaky tests**: Tests with mixed results (pass in some runs, fail in others)
3. **Stable failures**: Tests failing in ALL runs where executed

### Analysis Script Pattern

Create a script that:
1. Discovers all score-*/result-* directory pairs automatically
2. For each test category, identifies which runs have results
3. Tracks pass/fail status for each test across all runs
4. Categorizes tests based on consistency
5. Outputs both console summary and JSON files

### Required JSON Output Format

Generate three JSON files with tests grouped by category:

**stable_tests.json**:
```json
{
  "multi_turn_base": ["multi_turn_base_0", "multi_turn_base_1"],
  "live_simple": ["live_simple_0", "live_simple_1"]
}
```

**flaky_tests.json**: Same format, lists tests with inconsistent results

**failing_tests.json**: Same format, lists tests that always fail

### Key Implementation Details

```python
# For each run and category combination:
all_tests = get_test_ids_from_result(result_file)
failed_tests = get_failed_test_ids_from_score(score_file)
passed_tests = all_tests - failed_tests

# Track status across runs
for test_id in all_tests:
    if test_id in passed_tests:
        test_status[test_id]["passed"] += 1
    else:
        test_status[test_id]["failed"] += 1
    test_status[test_id]["total_runs"] += 1

# Categorize based on consistency
if passed == total_runs:
    # Stable pass
elif failed == total_runs:
    # Stable failure
else:
    # Flaky test
```

### Console Output Format

Provide both category-level and overall summaries:

```
Category: multi_turn_base
  Runs analyzed: 6 (baseline, blah, chat-multi-turn, ...)
  Total tests: 200
  Stable passes:   80 ( 40.0%)
  Flaky tests:     74 ( 37.0%)
  Stable fails:    46 ( 23.0%)

OVERALL SUMMARY
Total unique tests: 2111
  Stable passes: 1203 ( 57.0%)
  Flaky tests:    367 ( 17.4%)
  Stable fails:   541 ( 25.6%)
```

### Typical Findings

- Live tests typically show 70-76% stability
- Multi-turn tests show 21-40% stability
- Multi-turn miss_func category is often most flaky (40-50%)
- Flaky tests indicate non-determinism or environment sensitivity

## Automation Scripts

This skill includes helper scripts for common analysis tasks in the [scripts/](scripts/) directory.

### categorize_tests.py

Analyzes test stability across ALL runs in the directory, categorizing tests as stable passes, flaky, or stable failures.

**Usage**: Run from the root directory containing score-*/result-* folders:

```bash
./categorize_tests.py
```

**Output**:
- Console summary with category-level and overall statistics
- `stable_tests.json`: Tests passing in all runs, grouped by category
- `flaky_tests.json`: Tests with inconsistent results, grouped by category
- `failing_tests.json`: Tests failing in all runs, grouped by category
- Top insights identifying most flaky and most stable categories

**When to use**: When you need to understand test stability patterns across multiple runs, identify flaky tests to investigate, or track progress as you fix issues.

### compare_runs.py

Compares two BFCL test runs to identify regressions and improvements.

**Usage**: Run [scripts/compare_runs.py](scripts/compare_runs.py) with baseline directory, modified directory, and test category:

```bash
scripts/compare_runs.py <baseline_dir> <modified_dir> <test_category>
```

**Example**:
```bash
.claude/skills/bfcl-results/scripts/compare_runs.py \
  result-non-strict-parser \
  result-chat-tool-fix \
  multi_turn
```

**Output**:
- Summary statistics for both runs
- List of regressed test IDs (passed → failed)
- List of improved test IDs (failed → passed)
- Regressions categorized by error type

### extract_test.py

Extracts detailed information about a specific test.

**Usage**: Run [scripts/extract_test.py](scripts/extract_test.py) with result directory and test ID:

```bash
scripts/extract_test.py <result_dir> <test_id>
```

**Example**:
```bash
.claude/skills/bfcl-results/scripts/extract_test.py \
  result-chat-tool-fix \
  multi_turn_base_104
```

**Output**:
- Test status (passed/failed)
- Error details if failed
- Full prompt
- Model response
- Expected answer

## Validation Steps

When analyzing BFCL results:
1. ✓ Count lines in both result and score files
2. ✓ Verify: (result lines) = (summary total_count)
3. ✓ Verify: (score lines - 1) = (total_count - correct_count)
4. ✓ Check all entries in score file have `"valid": false`
5. ✓ Confirm passing tests exist in result file but not score file
