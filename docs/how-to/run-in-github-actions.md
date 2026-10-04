# How to run mutation testing in GitHub Actions

Use this guide to run an already-configured mutation test suite on pull requests, enforce a minimum mutation score, and retain the full report as a workflow artifact.

## Prerequisites

- Mutation testing is configured in the project. If it is not, complete the [bootstrap tutorial](../tutorials/bootstrap-existing-project.md).
- The project includes a Gradle wrapper.
- Business logic and its tests have the mutflow annotations described in the bootstrap tutorial.

This example intentionally uses upstream `LENIENT` verification so surviving
mutations reach the score gate. Default `STRICT` verification fails on any
survivor before an 80% threshold can accept the run. Lenient mode does not
excuse ordinary test failures, timeouts, execution gaps, or incomplete budgets.

## Add the workflow

Create `.github/workflows/mutation-testing.yml`:

```yaml
name: Mutation testing

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  mutation-testing:
    runs-on: ubuntu-latest
    env:
      MIN_MUTATION_SCORE: '0.80'
      MUTFLOW_VERIFICATION_MODE: LENIENT
    steps:
      - uses: actions/checkout@v7.0.1

      - uses: actions/setup-java@v6.0.1
        with:
          distribution: temurin
          java-version: '26'

      - uses: gradle/actions/setup-gradle@v6.4.0

      - name: Generate mutation results
        run: ./gradlew mutationResults --rerun-tasks --no-daemon --console=plain

      - name: Enforce mutation quality
        run: |
          python3 - <<'PY'
          import json
          import os
          from pathlib import Path

          report_path = Path("build/reports/mutation-results.json")
          if not report_path.is_file():
              raise SystemExit(f"Mutation report not found: {report_path}")

          results = json.loads(report_path.read_text())
          if results.get("schemaVersion") != 2:
              raise SystemExit("Expected mutation results schema 2")

          gap_count = results["gaps"]
          if gap_count:
              gap_types = ", ".join(
                  gap["type"] for gap in results["executionGaps"]
              )
              raise SystemExit(
                  f"Mutation run has {gap_count} execution gap(s): {gap_types}"
              )

          score = results["mutationScore"]
          if score is None or results["mutationsEvaluated"] == 0:
              raise SystemExit("Mutation run produced no evaluable mutations")

          if results["untestedMutations"]:
              raise SystemExit("Mutation run left discovered mutations untested")

          minimum = float(os.environ["MIN_MUTATION_SCORE"])
          if score < minimum:
              raise SystemExit(
                  f"Mutation score {score:.1%} is below the {minimum:.1%} minimum"
              )

          print(f"Mutation score {score:.1%} meets the {minimum:.1%} minimum")
          PY

      - name: Upload mutation results
        if: always()
        uses: actions/upload-artifact@v7.0.1
        with:
          name: mutation-results
          path: |
            build/reports/mutation-results.json
            build/reports/mutation-results.md
            build/test-results/
          if-no-files-found: warn
          retention-days: 14
```

Set `MIN_MUTATION_SCORE` to the threshold your project enforces. The value is a fraction, so `0.80` means 80%.

The example enforces a full discovered run: omit plain JVM annotation limits,
or use KMP `maxMutationRuns = Int.MAX_VALUE`, and remove ambient
`MUTFLOW_MAX_RUNS` limits. If your policy intentionally permits budgeted runs,
change the untested check explicitly and label the score as partial.

The `mutationResults` task also appends its Markdown results table to the
GitHub Actions job summary. The same human-readable report is written to
`build/reports/mutation-results.md`, while the JSON, Markdown, and JUnit XML
remain available in the uploaded artifact.

The wrapper owns the Gradle version; keep it at the validated compatible
baseline. `--rerun-tasks` avoids reusing XML generated under another environment
override. For strict all-survivors-fail policy, use `STRICT` instead and retain
the report upload. See the [results reference](../reference/mutation-results-format.md)
for fields and quality bands.

## Adjust a multi-module build

If the mutflow plugin and `mutationResults` task belong to a subproject, use its qualified Gradle task and report path. For a subproject named `service`:

```yaml
- name: Generate mutation results
  run: ./gradlew :service:mutationResults --rerun-tasks --no-daemon --console=plain
```

Change `report_path` to `service/build/reports/mutation-results.json` and
include `service/build/reports/mutation-results.json`,
`service/build/reports/mutation-results.md`, and the test-results directory
under `service/build/` in the uploaded artifact.

Apply mutflow and the shared results script in that subproject, with the typed
results module available from root `buildSrc`. There is no built-in
cross-subproject aggregate score. For KMP JVM, the adapter chooses
`mutflow<Target>Test`; uploading the entire `build/test-results/` directory
retains its XML as well as ordinary test reports.

## Check the workflow

Open a pull request or start the workflow from the Actions page. The `mutation-testing` job should:

1. Run the annotated tests and their generated mutations.
2. Print the mutation score and configured minimum.
3. Show the mutation summary table on the workflow run's job summary page.
4. Upload `mutation-results.json`, `mutation-results.md`, and the JUnit XML
   files, including when the quality check fails.

If the quality check fails, download the `mutation-results` artifact and follow [How to interpret and act on mutation testing results](interpret-results.md).
