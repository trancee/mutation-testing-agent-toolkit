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


def run(
    command: list[str],
    *,
    success: bool = True,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    environment = {name: value for name, value in os.environ.items() if not name.startswith("MUTFLOW_")}
    environment.update(extra_environment or {})
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
    summary_path = project / "build/reports/mutation-results.md"
    assert summary_path.is_file(), summary_path
    summary = summary_path.read_text()
    assert "| Gradle task | PASSED |" in summary or "| Gradle task | FAILED |" in summary, summary
    assert (
        f"| Outcomes | {data['killed']} killed, {data['survived']} survived, "
        f"{data['timedOut']} timed out |"
    ) in summary, summary
    assert f"| Execution gaps | {data['gaps']} |" in summary, summary
    if data["mutationScore"] is None:
        assert "| Mutation score | Unavailable |" in summary, summary
    else:
        assert f"| Mutation score | {data['mutationScore']:.2%} (" in summary, summary
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle", default="gradle", help="Gradle executable")
    args = parser.parse_args()
    bootstrap_command = str(ROOT / "bootstrap.sh")

    with tempfile.TemporaryDirectory(prefix="mutflow-integration-") as temporary:
        base = Path(temporary)
        jvm = base / "jvm"
        write(jvm, "build.gradle.kts", """
import org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask

plugins {
    kotlin("jvm") version "2.4.20"
    kotlin("plugin.serialization") version "2.4.20"
}
repositories { mavenCentral() }
kotlin { jvmToolchain(26) }
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")
}
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
        write(jvm, "src/main/kotlin/SerializableTarget.kt", """
package fixture
import kotlinx.serialization.Serializable

@Serializable
class SerializableTarget(val name: String, val count: Int = 0) {
    fun isEmpty(): Boolean = count == 0
}
""")
        write(jvm, "src/test/kotlin/SerializableTargetTest.kt", """
package fixture
import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit.MutFlowTest
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

@MutFlowTest
class SerializableTargetTest {
    @Test fun onlyHandWrittenFunctionIsMutated() {
        val isEmpty = MutFlow.underTest {
            val target = SerializableTarget("a", 0)
            val json = Json.encodeToString(SerializableTarget.serializer(), target)
            Json.decodeFromString(SerializableTarget.serializer(), json)
            target.isEmpty()
        }
        assertTrue(isEmpty)
    }
}
""")
        workflow_summary = jvm / "workflow-summary.md"
        write(jvm, "workflow-summary.md", "Prior workflow summary")
        github_environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_STEP_SUMMARY": str(workflow_summary),
        }
        run([bootstrap_command, "install", str(jvm)])
        write(jvm, "build.gradle.kts.bak", "user-owned backup\n")
        run([bootstrap_command, "install", str(jvm)])  # Repeat setup must preserve an installed project.
        assert (jvm / "build.gradle.kts.bak").read_text() == "user-owned backup\n"
        with (jvm / "build.gradle.kts").open("a") as build_file:
            build_file.write("""

tasks.withType<KotlinCompilationTask<*>>().configureEach {
    compilerOptions.freeCompilerArgs.add(
        "-Xcompiler-plugin-order=org.jetbrains.kotlinx.serialization>io.github.anschnapp.mutflow"
    )
}
""")
        gradle = [args.gradle, "-p", str(jvm), "--console=plain"]
        run(
            gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"],
            extra_environment=github_environment,
        )
        strong = report(jvm)
        assert strong["killed"] == strong["totalMutations"] == 4, strong
        assert strong["gaps"] == 0 and strong["mutationScore"] == 1, strong
        assert all(name.startswith("fixture.StrongTest::") for name in strong["testKillerMatrix"]), strong
        successful_summary = workflow_summary.read_text()
        assert successful_summary.startswith("Prior workflow summary\n"), successful_summary
        assert successful_summary.count("## Mutation testing results") == 1, successful_summary
        assert "| Gradle task | PASSED |" in successful_summary, successful_summary

        repeated = run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"])
        assert ":test UP-TO-DATE" in repeated.stdout, repeated.stdout
        refreshed = report(jvm)
        assert refreshed["generatedAt"] != strong["generatedAt"], (strong, refreshed)
        assert refreshed["mutations"] == strong["mutations"], (strong, refreshed)

        run(gradle + ["-PmutationTest.includes=fixture.BudgetTest", "mutationResults"])
        budgeted = report(jvm)
        assert budgeted["totalMutations"] == 4 and budgeted["mutationsEvaluated"] == 1, budgeted
        assert budgeted["untestedMutations"] == 3 and budgeted["gaps"] == 0, budgeted

        run(
            gradle + ["-PmutationTest.includes=fixture.WeakTest", "mutationResults"],
            success=False,
            extra_environment=github_environment,
        )
        weak = report(jvm)
        assert weak["survived"] == 4 and weak["killed"] == 0 and weak["gaps"] == 0, weak
        assert weak["testMethods"] == ["fixture.WeakTest::sameName()"], weak
        assert weak["generatedAt"] != strong["generatedAt"], (strong, weak)
        failed_summary = workflow_summary.read_text()
        assert failed_summary.count("## Mutation testing results") == 2, failed_summary
        assert "| Gradle task | FAILED |" in failed_summary, failed_summary

        run(gradle + ["-PmutationTest.includes=fixture.StrongTest,fixture.BrokenTest", "mutationResults"], success=False)
        broken = report(jvm)
        assert broken["mutationScore"] is None and broken["mutationsEvaluated"] == 4, broken
        assert any(g["type"] == "TEST_FAILURE" for g in broken["executionGaps"]), broken

        run(gradle + ["-PmutationTest.includes=fixture.StrongTest,fixture.WeakTest", "mutationResults"], success=False)
        multi = report(jvm)
        assert multi["totalMutations"] == 8 and multi["killed"] == multi["survived"] == 4, multi
        assert {m["testClass"] for m in multi["mutations"]} == {"fixture.StrongTest", "fixture.WeakTest"}, multi

        with((jvm / "build.gradle.kts").open("a") as build):
            build.write("""

mutflow {
    targets = listOf("fixture.SerializableTarget", "fixture.SerializableTarget.**")
}
""")
        run(gradle + ["-PmutationTest.includes=fixture.SerializableTargetTest", "mutationResults"])
        serialization = report(jvm)
        assert serialization["totalMutations"] == serialization["killed"] == 1, serialization
        assert serialization["gaps"] == 0, serialization
        assert serialization["mutations"][0]["sourceLocation"].startswith("SerializableTarget.kt:"), serialization

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
        assert not (jvm / "build/reports/mutation-results.md").exists()
        run(gradle + ["-PmutationTest.includes=,", "help"], success=False)
        write(jvm, "src/main/kotlin/Broken.kt", "this is not valid Kotlin")
        run(gradle + ["-PmutationTest.includes=fixture.StrongTest", "mutationResults"], success=False)
        assert not (jvm / "build/reports/mutation-results.json").exists()
        assert not (jvm / "build/reports/mutation-results.md").exists()

        junit4 = base / "junit4"
        write(junit4, "build.gradle.kts", """
plugins {
    kotlin("jvm") version "2.4.20"
}
repositories { mavenCentral() }
kotlin { jvmToolchain(26) }
dependencies {
    testImplementation("junit:junit:4.13.2")
}
tasks.withType<org.gradle.api.tasks.testing.Test>().configureEach { useJUnitPlatform() }
""")
        write(junit4, "src/main/kotlin/Decision.kt", """
package fixture
import io.github.anschnapp.mutflow.MutationTarget
@MutationTarget
class Decision {
    fun positive(value: Int): Boolean = value > 0
}
""")
        write(junit4, "src/test/kotlin/DecisionTest.kt", """
package fixture
import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit4.MutFlowRunner
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(MutFlowRunner::class)
class DecisionTest {
    @Test fun boundary() {
        assertTrue(MutFlow.underTest { Decision().positive(1) })
        assertFalse(MutFlow.underTest { Decision().positive(0) })
        assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
""")
        run([bootstrap_command, "install", str(junit4), "--junit4"])
        junit4_gradle = [args.gradle, "-p", str(junit4), "--console=plain"]
        run(junit4_gradle + [
            "-PmutationTest.includes=fixture.DecisionTest", "mutationResults",
        ])
        junit4_report = report(junit4)
        assert junit4_report["totalMutations"] == junit4_report["killed"] == 4, junit4_report
        assert junit4_report["gaps"] == 0, junit4_report

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
        run([bootstrap_command, "install", str(kmp), "--kmp"])
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
        run([bootstrap_command, "install", str(preserved), "--kmp"], success=False)
        assert (preserved / "build.gradle.kts").read_bytes() == original
        assert not (preserved / ".omp").exists()
        assert (preserved / "buildSrc/build.gradle.kts").read_text() == "// user-owned convention build\n"
        incompatible = base / "incompatible"
        write(incompatible, "build.gradle.kts", 'plugins {\n    kotlin("jvm") version "2.3.0"\n}\n')
        rejected = run([bootstrap_command, "install", str(incompatible)], success=False)
        assert "requires Kotlin 2.4.20" in rejected.stdout, rejected.stdout
        assert not (incompatible / ".omp").exists()

        catalog_kmp = base / "catalog-kmp"
        write(catalog_kmp, "settings.gradle.kts", """
pluginManagement {
    repositories { gradlePluginPortal(); mavenCentral() }
}
dependencyResolutionManagement {
    repositories { mavenCentral() }
}
rootProject.name = "catalog-kmp-fixture"
include(":kompact")
""")
        write(catalog_kmp, "gradle/libs.versions.toml", """
[versions]
kotlin = "2.4.20"

[plugins]
kmp = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
""")
        root_build = """
plugins {
    alias(libs.plugins.kmp) apply false
}
"""
        write(catalog_kmp, "build.gradle.kts", root_build)
        write(catalog_kmp, "kompact/build.gradle.kts", """
plugins {
    alias(libs.plugins.kmp)
}
kotlin {
    jvm()
    linuxX64()
    jvmToolchain(26)
    sourceSets {
      commonTest.dependencies { implementation(kotlin("test")) }
    }
}
""")
        write(catalog_kmp, "kompact/src/commonMain/kotlin/Decision.kt", """
package fixture
import io.github.anschnapp.mutflow.MutationTarget
@MutationTarget
class Decision {
    fun positive(value: Int): Boolean = value > 0
}
""")
        write(catalog_kmp, "kompact/src/commonTest/kotlin/DecisionTest.kt", """
package fixture
import io.github.anschnapp.mutflow.MutFlow
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
class DecisionTest {
    @Test fun boundary() {
      assertTrue(MutFlow.underTest { Decision().positive(1) })
      assertFalse(MutFlow.underTest { Decision().positive(0) })
      assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
""")
        root_build_before = (catalog_kmp / "build.gradle.kts").read_bytes()
        run([bootstrap_command, "install", str(catalog_kmp), "--kmp", "--module", ":kompact"])
        assert (catalog_kmp / "build.gradle.kts").read_bytes() == root_build_before
        catalog_gradle = [args.gradle, "-p", str(catalog_kmp), "--console=plain"]
        catalog_result = run(catalog_gradle + [
            "-PmutationTest.includes=fixture.DecisionTest", ":kompact:mutationResults",
        ])
        assert ":kompact:mutflowJvmTest" in catalog_result.stdout, catalog_result.stdout
        assert ":kompact:mutflowLinuxX64Test" not in catalog_result.stdout, catalog_result.stdout
        catalog_report = report(catalog_kmp / "kompact")
        assert catalog_report["totalMutations"] == catalog_report["killed"] == 4, catalog_report
        assert catalog_report["gaps"] == 0, catalog_report

    print("Real mutflow JVM/KMP integration scenarios passed.")


if __name__ == "__main__":
    main()
