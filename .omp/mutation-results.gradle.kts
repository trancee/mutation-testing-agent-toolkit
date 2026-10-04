import ch.trancee.mutation.ExecutionGap
import ch.trancee.mutation.JUnitMutationReportReader
import ch.trancee.mutation.MutationResultsParser
import ch.trancee.mutation.MutationResultsSerializer
import ch.trancee.mutation.MutationResultsSummary
import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.file.ConfigurableFileCollection
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFiles
import org.gradle.api.tasks.OutputFile
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction
import org.gradle.api.tasks.testing.Test

val includesProperty = providers.gradleProperty("mutationTest.includes").orNull
val mutationTestIncludes = includesProperty?.split(',')?.map(String::trim).orEmpty()
require(includesProperty == null || mutationTestIncludes.all { it.isNotEmpty() }) {
    "mutationTest.includes must contain nonempty comma-separated Gradle test patterns"
}

val mutationResults = tasks.register<MutationResultsTask>("mutationResults") {
    group = "verification"
    description = "Writes schema 2 mutation results and a readable summary from current JVM JUnit reports"
}
val prepareMutationResults = tasks.register("prepareMutationResults") {
    doLast {
        delete(
            mutationResults.get().resultsFile.get().asFile,
            mutationResults.get().summaryFile.get().asFile,
        )
    }
}
tasks.matching { it.name.startsWith("compile") }.configureEach {
    mustRunAfter(prepareMutationResults)
}

// KMP creates its dedicated mutation tasks after evaluation.
afterEvaluate {
    val mutationTestFramework = findProperty("mutationTest.junitFramework")?.toString() ?: "junit6"
    require(mutationTestFramework in setOf("junit4", "junit6")) {
        "mutationTest.junitFramework must be 'junit4' or 'junit6'"
    }
    val isKmp = plugins.hasPlugin("org.jetbrains.kotlin.multiplatform")
    val selectedTests = tasks.withType<Test>().matching {
        if (isKmp) it.name.startsWith("mutflow") && it.name.endsWith("Test") else it.name == "test"
    }
    require(!selectedTests.isEmpty()) {
        "No supported JVM mutation test task found; enable mutflow and configure a JVM target"
    }
    selectedTests.configureEach {
        dependsOn(prepareMutationResults)
        if (mutationTestFramework == "junit6") {
            useJUnitPlatform()
        } else {
            useJUnit()
        }
        reports.junitXml.required.set(true)
        testLogging.showStandardStreams = true
        mutationTestIncludes.forEach { filter.includeTestsMatching(it) }
    }
    gradle.taskGraph.whenReady {
        if (hasTask(mutationResults.get())) {
            // Allow XML collection, then restore the failure exit status after writing JSON.
            selectedTests.forEach { it.ignoreFailures = true }
        }
    }
    mutationResults.configure {
        dependsOn(selectedTests)
        junitReports.from(selectedTests.map { it.reports.junitXml.outputLocation.get().asFile })
    }
}

open class MutationResultsTask : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    val junitReports: ConfigurableFileCollection = project.objects.fileCollection()

    @get:OutputFile
    val resultsFile: RegularFileProperty = project.objects.fileProperty()
        .convention(project.layout.buildDirectory.file("reports/mutation-results.json"))

    @get:OutputFile
    val summaryFile: RegularFileProperty = project.objects.fileProperty()
        .convention(project.layout.buildDirectory.file("reports/mutation-results.md"))

    @TaskAction
    fun generateResults() {
        val xmlFiles = junitReports.files.flatMap { directory ->
            directory.walkTopDown().filter {
                it.isFile && it.name.startsWith("TEST-") && it.extension == "xml"
            }.toList()
        }.sortedBy { it.absolutePath }
        val reports = xmlFiles.map(JUnitMutationReportReader::read)
        val gaps = reports.flatMap { it.gaps }.toMutableList()
        if (xmlFiles.isEmpty()) {
            gaps += ExecutionGap("NO_OUTPUT", "No current JUnit XML reports were produced")
        }
        val results = MutationResultsParser.assembleResults(
            mutations = reports.flatMap { it.mutations },
            testMethods = reports.flatMap { it.testMethods }.distinct().sorted(),
            gaps = gaps,
            discoveredMutations = reports.sumOf { it.discoveredMutations },
        )
        val runFailed = reports.any { it.hasTestFailures } || gaps.isNotEmpty()
        val summary = MutationResultsSummary.render(results, runFailed)
        resultsFile.get().asFile.apply {
            parentFile.mkdirs()
            writeText(MutationResultsSerializer.toJson(results))
        }
        summaryFile.get().asFile.apply {
            parentFile.mkdirs()
            writeText("$summary\n")
        }
        logger.lifecycle(summary)
        logger.lifecycle("Readable report written to: ${summaryFile.get().asFile}")
        logger.lifecycle("JSON report written to: ${resultsFile.get().asFile}")
        appendGithubStepSummary(summary)
        if (runFailed) {
            throw GradleException(
                "Mutation run failed or was incomplete; inspect mutation-results.md, mutation-results.json, and JUnit XML",
            )
        }
    }

    private fun appendGithubStepSummary(summary: String) {
        if (System.getenv("GITHUB_ACTIONS") != "true") return

        val summaryPath = System.getenv("GITHUB_STEP_SUMMARY")
        if (summaryPath.isNullOrBlank()) {
            logger.warn(
                "GITHUB_STEP_SUMMARY is unavailable; the readable mutation report is at ${summaryFile.get().asFile}",
            )
            return
        }

        val githubSummaryFile = java.io.File(summaryPath)
        if (!githubSummaryFile.isAbsolute || !githubSummaryFile.isFile) {
            logger.warn(
                "GITHUB_STEP_SUMMARY must be an existing absolute file; " +
                    "the readable mutation report is at ${summaryFile.get().asFile}",
            )
            return
        }

        try {
            val separator = if (githubSummaryFile.length() == 0L) "" else "\n"
            githubSummaryFile.appendText("$separator$summary\n\n")
            logger.lifecycle("Mutation results added to the GitHub Actions job summary")
        } catch (failure: java.io.IOException) {
            logger.warn(
                "Could not update the GitHub Actions job summary; " +
                    "the readable mutation report is at ${summaryFile.get().asFile}",
                failure,
            )
        }
    }
}
