package ch.trancee.mutation

import java.io.File
import javax.xml.XMLConstants
import javax.xml.parsers.DocumentBuilderFactory
import org.w3c.dom.Element

data class JUnitMutationReport(
    val mutations: List<MutationResult>,
    val testMethods: List<String>,
    val gaps: List<ExecutionGap>,
    val discoveredMutations: Int,
    val hasTestFailures: Boolean,
)

object JUnitMutationReportReader {
    fun read(file: File): JUnitMutationReport {
        val factory = DocumentBuilderFactory.newInstance().apply {
            setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
            setFeature("http://xml.org/sax/features/external-general-entities", false)
            setFeature("http://xml.org/sax/features/external-parameter-entities", false)
            setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "")
            setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "")
        }
        val suite = factory.newDocumentBuilder().parse(file).documentElement
        val testClass = suite.getAttribute("name")
        require(testClass.isNotBlank()) { "Missing test suite name in $file" }
        val stdout = suite.getElementsByTagName("system-out").let { nodes ->
            (0 until nodes.length).joinToString("\n") { nodes.item(it).textContent }
        }
        val mutations = MutationResultsParser.parseMutflowSummary(stdout).map { mutation ->
            mutation.copy(
                testClass = testClass,
                killedByTest = mutation.killedByTest?.let { "$testClass::$it" },
                killedByTests = mutation.killedByTests.map { "$testClass::$it" },
            )
        }
        val failures = listOf("failure", "error").flatMap { tag ->
            val nodes = suite.getElementsByTagName(tag)
            (0 until nodes.length).map { nodes.item(it) as Element }
        }
        val unexpectedFailures = failures.filterNot { failure ->
            val type = failure.getAttribute("type")
            type == "io.github.anschnapp.mutflow.MutantSurvivedException" ||
                type == "io.github.anschnapp.mutflow.MutationTimedOutException"
        }
        val gaps = mutableListOf<ExecutionGap>()
        if (unexpectedFailures.isNotEmpty()) {
            gaps.add(ExecutionGap(
                type = "TEST_FAILURE",
                reason = "${unexpectedFailures.size} baseline or ordinary test failures in $file",
                testClass = testClass,
            ))
        }
        // Ordinary test suites need no mutation summary, but annotated suites do.
        val cases = suite.getElementsByTagName("testcase")
        val testMethods = (0 until cases.length).mapNotNull { index ->
            val testcase = cases.item(index) as Element
            if (testcase.getAttribute("name") == "executionError") return@mapNotNull null
            "$testClass::${testcase.getAttribute("name")}"
        }.distinct().sorted()
        val isMutationSuite = stdout.contains("[mutflow]") || stdout.contains("MUTATION TESTING SUMMARY") ||
            failures.size != unexpectedFailures.size
        if (isMutationSuite) {
            gaps += MutationResultsParser.detectGaps(stdout, mutations)
                .map { it.copy(testClass = testClass) }
            if (listOf("Total mutations discovered:", "Tested this run:", "Remaining untested:")
                    .any { !stdout.contains(it) }) {
                gaps.add(ExecutionGap("PARTIAL_RUN", "Missing mutflow summary in $file", testClass))
            }
        }
        return JUnitMutationReport(
            mutations, testMethods, gaps,
            (MutationResultsParser.discoveredCount(stdout) ?: mutations.size).coerceAtLeast(mutations.size),
            failures.isNotEmpty(),
        )
    }
}
