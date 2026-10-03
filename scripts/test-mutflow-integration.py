#!/usr/bin/env python3
"""Exercise bootstrap and reporting against the real published mutflow plugin."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def write(project: Path, path: str, content: str) -> None:
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def run(command: list[str], *, success: bool = True) -> subprocess.CompletedProcess:
    environment = {name: value for name, value in os.environ.items() if not name.startswith("MUTFLOW_")}
    result = subprocess.run(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=300, env=environment,
    )
    if (result.returncode == 0) != success:
        raise AssertionError(f"Unexpected exit status {result.returncode}: {command}\n{result.stdout}")
    return result


def report(project: Path) -> dict:
    data = json.loads((project / "build/reports/mutation-results.json").read_text())
    assert data["schemaVersion"] == 2, data
    assert data["mutationsEvaluated"] == data["killed"] + data["survived"] + data["timedOut"], data
    assert data["totalMutations"] == data["mutationsEvaluated"] + data["untestedMutations"], data
    assert data["mutationScore"] is None or 0 <= data["mutationScore"] <= 1, data
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle", default="gradle", help="Gradle executable")
    args = parser.parse_args()
    bootstrap = str(ROOT / ".omp/bootstrap-mutation-testing.sh")

    with tempfile.TemporaryDirectory(prefix="mutflow-integration-") as temporary:
        base = Path(temporary)
        jvm = base / "jvm"
        write(jvm, "build.gradle.kts", """
plugins {
    kotlin("jvm") version "2.4.20"
}
repositories { mavenCentral() }
kotlin { jvmToolchain(26) }
""")
        write(jvm, "src/main/kotlin/Decision.kt", """
package fixture
import io.github.anschnapp.mutflow.MutationTarget
@MutationTarget
class Decision {
    fun positive(value: Int): Boolean = value > 0
}
@MutationTarget
class Loop {
    fun count(): Int {
        var count = 0
        while (count != 1) { count = count + 1 }
        return count
    }
}
""")
        write(jvm, "src/test/kotlin/DecisionTest.kt", """
package fixture
import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit.MutFlowTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

@MutFlowTest
class StrongTest {
    @Test fun sameName() {
        assertTrue(MutFlow.underTest { Decision().positive(1) })
        assertFalse(MutFlow.underTest { Decision().positive(0) })
        assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
@MutFlowTest
class WeakTest {
    @Test fun sameName() {
        assertNotNull(MutFlow.underTest { Decision().positive(1) })
    }
}
@MutFlowTest(maxRuns = 2)
class BudgetTest {
    @Test fun boundary() {
        assertTrue(MutFlow.underTest { Decision().positive(1) })
        assertFalse(MutFlow.underTest { Decision().positive(0) })
        assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
class BrokenTest {
    @Test fun baselineFailure() { assertEquals(2, 1) }
}
@MutFlowTest(timeoutMs = 20, testBudgetFactor = 0)
class TimeoutTest {
    @Test fun loopCompletes() { assertEquals(1, MutFlow.underTest { Loop().count() }) }
}
""")
        run(["bash", bootstrap, str(jvm)])
        write(jvm, "build.gradle.kts.bak", "user-owned backup\n")
        run(["bash", bootstrap, str(jvm)])  # Repeat setup must preserve an installed project.
        assert (jvm / "build.gradle.kts.bak").read_text() == "user-owned backup\n"
        gradle = [args.gradle, "-p", str(jvm), "--console=plain"]
        run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"])
        strong = report(jvm)
        assert strong["killed"] == strong["totalMutations"] == 4, strong
        assert strong["gaps"] == 0 and strong["mutationScore"] == 1, strong
        assert all(name.startswith("fixture.StrongTest::") for name in strong["testKillerMatrix"]), strong

        repeated = run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"])
        assert ":test UP-TO-DATE" in repeated.stdout, repeated.stdout
        refreshed = report(jvm)
        assert refreshed["generatedAt"] != strong["generatedAt"], (strong, refreshed)
        assert refreshed["mutations"] == strong["mutations"], (strong, refreshed)

        run(gradle + ["-PmutationTest.includes=fixture.BudgetTest", "mutationResults"])
        budgeted = report(jvm)
        assert budgeted["totalMutations"] == 4 and budgeted["mutationsEvaluated"] == 1, budgeted
        assert budgeted["untestedMutations"] == 3 and budgeted["gaps"] == 0, budgeted

        run(gradle + ["-PmutationTest.includes=fixture.WeakTest", "mutationResults"], success=False)
        weak = report(jvm)
        assert weak["survived"] == 4 and weak["killed"] == 0 and weak["gaps"] == 0, weak
        assert weak["testMethods"] == ["fixture.WeakTest::sameName()"], weak
        assert weak["generatedAt"] != strong["generatedAt"], (strong, weak)

        run(gradle + ["-PmutationTest.includes=fixture.StrongTest,fixture.BrokenTest", "mutationResults"], success=False)
        broken = report(jvm)
        assert broken["mutationScore"] is None and broken["mutationsEvaluated"] == 4, broken
        assert any(g["type"] == "TEST_FAILURE" for g in broken["executionGaps"]), broken

        run(gradle + ["-PmutationTest.includes=fixture.StrongTest,fixture.WeakTest", "mutationResults"], success=False)
        multi = report(jvm)
        assert multi["totalMutations"] == 8 and multi["killed"] == multi["survived"] == 4, multi
        assert {m["testClass"] for m in multi["mutations"]} == {"fixture.StrongTest", "fixture.WeakTest"}, multi
        run(gradle + ["-PmutationTest.includes=fixture.TimeoutTest", "mutationResults"], success=False)
        timed_out = report(jvm)
        assert timed_out["timedOut"] > 0 and timed_out["gaps"] == 0, timed_out

        run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults", "jar"])
        jar = next((jvm / "build/libs").glob("*.jar"))
        with zipfile.ZipFile(jar) as archive:
            assert not any(b"MutationRegistry" in archive.read(name)
                           for name in archive.namelist() if name.endswith(".class")), jar
        mutated = jvm / "build/classes/kotlin/mutatedMain/fixture/Decision.class"
        assert b"MutationRegistry" in mutated.read_bytes(), mutated
        run(gradle + ["-PmutationTest.includes=fixture.MissingTest", "mutationResults"], success=False)
        assert not (jvm / "build/reports/mutation-results.json").exists()
        run(gradle + ["-PmutationTest.includes=,", "help"], success=False)
        write(jvm, "src/main/kotlin/Broken.kt", "this is not valid Kotlin")
        run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"], success=False)
        assert not (jvm / "build/reports/mutation-results.json").exists()

        kmp = base / "kmp"
        write(kmp, "build.gradle.kts", """
plugins {
    kotlin("multiplatform") version "2.4.20"
}
repositories { mavenCentral() }
kotlin {
    jvm()
    jvmToolchain(26)
    sourceSets {
        commonTest.dependencies { implementation(kotlin("test")) }
    }
}
""")
        write(kmp, "src/commonMain/kotlin/Decision.kt", """
package fixture
import io.github.anschnapp.mutflow.MutationTarget
@MutationTarget
class Decision {
    fun positive(value: Int): Boolean = value > 0
}
""")
        write(kmp, "src/commonTest/kotlin/DecisionTest.kt", """
package fixture
import io.github.anschnapp.mutflow.MutFlow
import kotlin.test.Test
import kotlin.test.assertTrue
import kotlin.test.assertFalse
class DecisionTest {
    @Test fun boundary() {
        assertTrue(MutFlow.underTest { Decision().positive(1) })
        assertFalse(MutFlow.underTest { Decision().positive(0) })
        assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
""")
        run(["bash", bootstrap, str(kmp), "--kmp"])
        kmp_gradle = [args.gradle, "-p", str(kmp), "--console=plain"]
        # DSL budgets count mutations, not the baseline; commonTest has no JUnit annotation.
        with (kmp / "build.gradle.kts").open("a") as build:
            build.write("\nmutflow { maxMutationRuns = 1 }\n")
        result = run(kmp_gradle + ["-PmutationTest.includes=fixture.DecisionTest", "mutationResults"])
        assert ":mutflowJvmTest" in result.stdout, result.stdout
        limited = report(kmp)
        assert limited["totalMutations"] == 4 and limited["mutationsEvaluated"] == 1, limited
        assert limited["untestedMutations"] == 3 and limited["gaps"] == 0, limited
        with (kmp / "build.gradle.kts").open("a") as build:
            build.write("\nmutflow { maxMutationRuns = Int.MAX_VALUE }\n")
        run(kmp_gradle + ["mutationResults"])
        full = report(kmp)
        assert full["totalMutations"] == full["killed"] == 4 and full["untestedMutations"] == 0, full

        build_file = kmp / "build.gradle.kts"
        build_file.write_text(build_file.read_text().replace("jvm()", 'jvm("backend")'))
        named = run(kmp_gradle + ["-PmutationTest.includes=fixture.DecisionTest", "mutationResults"])
        assert ":mutflowBackendTest" in named.stdout, named.stdout
        named_report = report(kmp)
        assert named_report["totalMutations"] == named_report["killed"] == 4, named_report
        assert named_report["gaps"] == 0 and named_report["untestedMutations"] == 0, named_report

        preserved = base / "owned-buildsrc"
        preserved.mkdir()
        shutil.copy(kmp / "build.gradle.kts", preserved / "build.gradle.kts")
        write(preserved, "buildSrc/build.gradle.kts", "// user-owned convention build\n")
        original = (preserved / "build.gradle.kts").read_bytes()
        run(["bash", bootstrap, str(preserved), "--kmp"], success=False)
        assert (preserved / "build.gradle.kts").read_bytes() == original
        assert not (preserved / ".omp").exists()
        assert (preserved / "buildSrc/build.gradle.kts").read_text() == "// user-owned convention build\n"
        incompatible = base / "incompatible"
        write(incompatible, "build.gradle.kts", 'plugins {\n    kotlin("jvm") version "2.3.0"\n}\n')
        rejected = run(["bash", bootstrap, str(incompatible)], success=False)
        assert "requires Kotlin 2.4.20" in rejected.stdout, rejected.stdout
        assert not (incompatible / ".omp").exists()

    print("Real mutflow JVM/KMP integration scenarios passed.")


if __name__ == "__main__":
    main()
