#!/usr/bin/env python3
"""Execute documented JVM/KMP tutorials and the CI score gate from their source."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith("MUTFLOW_")}


def blocks(path, language):
    return re.findall(rf"```{language}\n(.*?)\n```", (ROOT / path).read_text(), re.S)


def write(project, name, content):
    path = project / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n")


def run(project, command, success=True, environment=None):
    result = subprocess.run(
        command, cwd=project, env=environment or ENVIRONMENT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
    )
    if (result.returncode == 0) != success:
        raise AssertionError(f"Unexpected exit {result.returncode}: {command}\n{result.stdout}")
    return result.stdout


def test_jvm_and_ci(project):
    source = blocks("docs/tutorials/first-mutation-test.md", "kotlin")
    assert len(source) == 5, "Update the tutorial harness for the new snippet layout"
    for name, content in zip(
        ["settings.gradle.kts", "build.gradle.kts", "src/main/kotlin/Calculator.kt",
         "src/test/kotlin/CalculatorTest.kt"], source[:4],
    ):
        write(project, name, content)
    output = run(project, ["gradle", "test", "--console=plain"], success=False)
    assert "SURVIVED" in output, output

    write(project, "src/test/kotlin/CalculatorTest.kt",
          source[3].rsplit("}", 1)[0] + source[4] + "\n}")
    output = run(project, ["gradle", "test", "--console=plain"])
    assert re.search(r"Total mutations discovered:\s*4", output), output
    assert re.search(r"Remaining untested:\s*0", output), output

    run(project, [str(ROOT / "bootstrap.sh"), "install", str(project)])
    run(project, ["gradle", "mutationResults", "--rerun-tasks", "--console=plain"])
    report_file = project / "build/reports/mutation-results.json"
    strong = json.loads(report_file.read_text())
    workflow = blocks("docs/how-to/run-in-github-actions.md", "yaml")[0]
    match = re.search(r"          python3 - <<'PY'\n(.*?)\n          PY", workflow, re.S)
    assert match, "Documented score gate was not found"
    gate = "\n".join(line[10:] for line in match.group(1).splitlines())
    gate_environment = dict(ENVIRONMENT, MIN_MUTATION_SCORE="0.80")
    run(project, ["python3", "-c", gate], environment=gate_environment)

    write(project, "src/test/kotlin/CalculatorTest.kt", source[3])
    run(project, ["gradle", "mutationResults", "--rerun-tasks", "--console=plain"],
        environment=dict(ENVIRONMENT, MUTFLOW_VERIFICATION_MODE="LENIENT"))
    weak = json.loads(report_file.read_text())
    assert weak["survived"] > 0 and weak["gaps"] == 0, weak
    run(project, ["python3", "-c", gate], success=False, environment=gate_environment)

    for invalid in [
        {"schemaVersion": 1},
        {"gaps": 1, "executionGaps": [{"type": "PARTIAL_RUN"}]},
        {"mutationScore": None}, {"mutationsEvaluated": 0}, {"untestedMutations": 1},
    ]:
        report_file.write_text(json.dumps(dict(strong, **invalid)))
        run(project, ["python3", "-c", gate], success=False, environment=gate_environment)
    report_file.unlink()
    run(project, ["python3", "-c", gate], success=False, environment=gate_environment)
    print("JVM tutorial and CI gate: boundary fix and invalid-report rejection passed.")


def test_kmp(project):
    source = blocks("docs/tutorials/kmp-jvm-mutation-test.md", "kotlin")
    assert len(source) == 6, "Update the tutorial harness for the new snippet layout"
    for name, content in zip(
        ["settings.gradle.kts", "build.gradle.kts", "src/commonMain/kotlin/Decision.kt",
         "src/commonTest/kotlin/DecisionTest.kt"], source[:4],
    ):
        write(project, name, content)
    run(project, [str(ROOT / "bootstrap.sh"), "install", str(project), "--kmp"])
    build = project / "build.gradle.kts"
    build.write_text(build.read_text() + "\n" + source[4] + "\n")
    command = ["gradle", "mutationResults", "-PmutationTest.includes=example.DecisionTest", "--console=plain"]
    output = run(project, command)
    assert ":mutflowJvmTest" in output, output
    report_file = project / "build/reports/mutation-results.json"
    limited = json.loads(report_file.read_text())
    expected = {
        "schemaVersion": 2, "totalMutations": 4, "mutationsEvaluated": 1,
        "killed": 1, "untestedMutations": 3, "gaps": 0, "mutationScore": 1.0,
    }
    assert {key: limited[key] for key in expected} == expected, limited

    build.write_text(build.read_text().replace(source[4], source[5]))
    run(project, command)
    full = json.loads(report_file.read_text())
    assert full["totalMutations"] == full["mutationsEvaluated"] == full["killed"] == 4, full
    assert full["untestedMutations"] == full["gaps"] == 0, full
    assert full["testMethods"] == ["example.DecisionTest::boundary()"], full
    print("KMP tutorial: budgeted/full counts and identities passed.")


def main():
    with tempfile.TemporaryDirectory(prefix="toolkit-doc-examples-") as temporary:
        test_jvm_and_ci(Path(temporary) / "jvm")
        test_kmp(Path(temporary) / "kmp")


if __name__ == "__main__":
    main()
