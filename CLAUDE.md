# BFCL Results Repository

This repository contains Berkeley Function Calling Leaderboard (BFCL) benchmark results for gpt-oss-120b model testing.

## What's Here

BFCL benchmark results from multiple test runs comparing different configurations:
- `result-baseline/` - Raw model outputs from baseline run
- `result-chat-tool-fix/` - Raw model outputs from chat-tool-fix variant
- `result-non-strict-parser/` - Raw model outputs from non-strict-parser variant
- `score-baseline/` - Evaluation scores from baseline run
- `score-chat-tool-fix/` - Evaluation scores from chat-tool-fix variant
- `score-non-strict-parser/` - Evaluation scores from non-strict-parser variant

## Analyzing Results

**IMPORTANT**: Always use the `bfcl-results` skill when analyzing these results.

The BFCL result format is counter-intuitive and easy to misinterpret. The skill provides essential knowledge about:
- BFCL's two-file structure (result files vs score files)
- Why passing tests don't appear in score files
- How to correctly interpret accuracy metrics
- How to compare runs and identify regressions
- Understanding multi-turn test failures

## Quick Start

To analyze or compare these results:

1. Invoke the `bfcl-results` skill before starting analysis
2. Use the commands and workflows from the skill
3. Remember: score files ONLY contain failures, passing tests are in result files only

## Test Categories

- **multi_turn_base**: Multi-turn conversation scenarios
- **live_simple**: Simple live API calls
- **live_multiple**: Complex live API scenarios

Each category has both result files (all tests) and score files (failures only).
