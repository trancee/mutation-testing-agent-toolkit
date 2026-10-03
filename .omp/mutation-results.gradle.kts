/**
 * Custom Gradle task: mutationResults
 *
 * Thin adapter that delegates to the typed MutationResults module in buildSrc.
 *
 * Usage in build.gradle.kts:
 *   apply(plugin = "io.github.anschnapp.mutflow")
 *   apply(from = rootProject.file(".omp/mutation-results.gradle.kts"))
 *
 * Output: build/reports/mutation-results.json
 *
 * mutflow's @MutFlowTest JUnit extension runs baseline (run 0) + mutation runs (run 1+)
 * internally. Each mutation run prints MutationTestingSummary to stdout.
 * Gradle captures stdout in JUnit XML's <system-out> elements.
 *
 * The typed data model, pure parsing functions, and JSON serialization live in
 * buildSrc (see .omp/mutation-results-src/). This task only collects JUnit XML
 * files, delegates to the parser, and writes the JSON output.
 */

import io.omp.mutation.MutationResultsParser
import io.omp.mutation.MutationResultsSerializer
import io.omp.mutation.MutationResults
import org.gradle.api.DefaultTask
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.OutputFile
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction
import org.gradle.api.tasks.testing.Test
import java.io.File
import java.util.regex.Pattern

val mutationTestIncludes = providers.gradleProperty("mutationTest.includes")
    .orNull
    ?.split(',')
    ?.map(String::trim)
    ?.filter(String::isNotEmpty)
    .orEmpty()

// Configure test to capture stdout in JUnit XML (mutflow prints to stdout)
tasks.withType<Test>().configureEach {
    testLogging {
        showStandardStreams = true
        events("passed", "skipped", "failed")
    }
    reports {
        junitXml.required.set(true)
    }
    if (mutationTestIncludes.isNotEmpty()) {
        filter {
            mutationTestIncludes.forEach { includeTestsMatching(it) }
        }
    }
}

tasks.register<MutationResultsTask>("mutationResults") {
    group = "verification"
    description = "Runs mutflow mutation tests and outputs structured JSON results"
    dependsOn(tasks.matching { it.name == "test" })
    project.gradle.taskGraph.whenReady {
        val testTask = project.tasks.findByName("test")
        if (testTask is Test) {
            testTask.ignoreFailures = true
        }
    }
}

open class MutationResultsTask : DefaultTask() {

    @get:OutputFile
    val resultsFile: RegularFileProperty = project.objects.fileProperty()
        .convention(project.layout.buildDirectory.file("reports/mutation-results.json"))

    @get:Input
    val testTaskName: Property<String> = project.objects.property(String::class.java)
        .convention("test")


    @TaskAction
    fun generateResults() {
        val buildDir = project.layout.buildDirectory.get().asFile
        val resultsDir = File(buildDir, "test-results/test")

        // Collect all JUnit XML files — they contain <system-out> with mutflow output
        val allStdout = StringBuilder()
        val testMethods = mutableSetOf<String>()

        val xmlFiles = if (resultsDir.exists()) {
            resultsDir.walkTopDown()
                .filter { it.isFile && it.name.startsWith("TEST-") && it.extension == "xml" }
                .onEach { xmlFile ->
                    val content = xmlFile.readText()
                    val testcasePattern = Pattern.compile("""<testcase[^>]*\bname="([^"]+)""")
                    val tcMatcher = testcasePattern.matcher(content)
                    while (tcMatcher.find()) {
                        testMethods.add(tcMatcher.group(1))
                    }
                    val sysoutPattern = Pattern.compile("<system-out>(.*?)</system-out>", Pattern.DOTALL)
                    val soMatcher = sysoutPattern.matcher(content)
                    while (soMatcher.find()) {
                        allStdout.append(soMatcher.group(1)).append("\n")
                    }
                }
                .toList()
        } else {
            emptyList()
        }

        val stdout = allStdout.toString()

        // Detect build-level gaps (compilation failure, IR transform error, etc.)
        val buildLevelGaps = mutableListOf<io.omp.mutation.ExecutionGap>()
        if (xmlFiles.isEmpty()) {
            val testTask = project.tasks.findByName(testTaskName.get())
            val gradleExitCode = if (testTask?.state?.failure != null) 1 else null
            buildLevelGaps.add(io.omp.mutation.ExecutionGap(
                type = "COMPILATION_FAILURE",
                reason = "No JUnit XML files found — likely compilation error or IR transformation error",
                gradleExitCode = gradleExitCode,
            ))
        }

        // Delegate to typed module — pure functions, no Gradle dependency
        val mutations = MutationResultsParser.parseMutflowSummary(stdout)
        val gaps = MutationResultsParser.detectGaps(stdout, mutations, buildLevelGaps)
        val sortedTestMethods = testMethods.sorted()
        val results = MutationResultsParser.assembleResults(
            mutations = mutations,
            testMethods = sortedTestMethods,
            gaps = gaps,
        )
        val json = MutationResultsSerializer.toJson(results)

        resultsFile.get().asFile.parentFile.mkdirs()
        resultsFile.get().asFile.writeText(json)

        logger.lifecycle("Mutation results written to: ${resultsFile.get().asFile}")
        val scoreStr = results.mutationScore?.let { String.format("%.1f%%", it * 100) } ?: "N/A"
        logger.lifecycle("  Score: $scoreStr (${results.qualityBand}, ${results.confidence} confidence)")
        logger.lifecycle("  Killed: ${results.killed}, Survived: ${results.survived}, Timed out: ${results.timedOut}")
        if (results.gaps > 0) {
            logger.lifecycle("  Gaps: ${results.gaps} (${results.executionGaps.joinToString { it.type }})")
        }
    }
}
