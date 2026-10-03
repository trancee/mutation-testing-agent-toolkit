package ch.trancee.mutation

import java.nio.file.Files
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class JUnitMutationReportTest {
    private fun read(xml: String): JUnitMutationReport {
        val file = Files.createTempFile("mutflow-junit-", ".xml").toFile()
        try {
            file.writeText(xml)
            return JUnitMutationReportReader.read(file)
        } finally {
            file.delete()
        }
    }

    @Test
    fun `CDATA and escaped XML preserve qualified killer identities`() {
        val xml = """
            <testsuite name="example.CalcTest">
              <testcase name="handles &amp; boundaries()" />
              <system-out><![CDATA[
            MUTATION TESTING SUMMARY
            Total mutations discovered: 2
            Tested this run: 1
            Remaining untested: 1
            ✓ (Calc.kt:1) && → ||
                killed by: handles & boundaries()
              ]]></system-out>
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertEquals(listOf("example.CalcTest::handles & boundaries()"), report.testMethods)
        assertEquals(report.testMethods, report.mutations.single().killedByTests)
        assertEquals("&&", report.mutations.single().originalOperator)
        assertEquals(2, report.discoveredMutations)
        assertTrue(report.gaps.isEmpty())
    }

    @Test
    fun `ordinary failures are gaps even alongside valid mutation output`() {
        val xml = """
            <testsuite name="example.BrokenTest">
              <testcase name="baseline"><failure type="org.opentest4j.AssertionFailedError">broken</failure></testcase>
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertEquals("TEST_FAILURE", report.gaps.single().type)
        assertEquals("example.BrokenTest", report.gaps.single().testClass)
    }

    @Test
    fun `strict survivors and mutation timeouts are outcomes not infrastructure gaps`() {
        val xml = """
            <testsuite name="example.WeakTest">
              <testcase name="survivor"><failure type="io.github.anschnapp.mutflow.MutantSurvivedException" /></testcase>
              <testcase name="timeout"><failure type="io.github.anschnapp.mutflow.MutationTimedOutException" /></testcase>
              <system-out><![CDATA[
            MUTATION TESTING SUMMARY
            Total mutations discovered: 2
            Tested this run: 2
            Remaining untested: 0
            ✗ (Calc.kt:1) > → >=
            ⏱ (Calc.kt:2) < → >
              ]]></system-out>
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertTrue(report.gaps.isEmpty())
        assertEquals(listOf(MutationResultType.Survived, MutationResultType.TimedOut), report.mutations.map { it.result })
    }

    @Test
    fun `missing mutation summary is a gap`() {
        val xml = """<testsuite name="example.PartialTest"><system-out>[mutflow] Starting baseline run</system-out></testsuite>"""

        val report = read(xml)

        assertTrue(report.gaps.any { it.type == "NO_OUTPUT" })
    }

    @Test
    fun `missing discovered counter never becomes a complete report`() {
        val xml = """
            <testsuite name="example.PartialTest"><system-out><![CDATA[
            MUTATION TESTING SUMMARY
            Tested this run: 1
            ✓ (Calc.kt:1) > → >=
                killed by: boundary()
            ]]></system-out></testsuite>
        """.trimIndent()

        val report = read(xml)

        assertTrue(report.gaps.any { it.type == "PARTIAL_RUN" })
    }

    @Test
    fun `ordinary passing tests do not require a mutation summary`() {
        val xml = """<testsuite name="example.OrdinaryTest"><testcase name="passes()" /></testsuite>"""

        val report = read(xml)

        assertTrue(report.gaps.isEmpty())
        assertTrue(report.mutations.isEmpty())
        assertEquals(listOf("example.OrdinaryTest::passes()"), report.testMethods)
    }

    @Test
    fun `contradictory summary counters invalidate the score without losing outcomes`() {
        val xml = """
            <testsuite name="example.PartialTest"><system-out><![CDATA[
            MUTATION TESTING SUMMARY
            Total mutations discovered: 0
            Tested this run: 1
            Remaining untested: 0
            ✓ (Calc.kt:1) > → >=
                killed by: boundary()
            ]]></system-out></testsuite>
        """.trimIndent()

        val report = read(xml)
        val results = MutationResultsParser.assembleResults(
            report.mutations, report.testMethods, gaps = report.gaps,
            discoveredMutations = report.discoveredMutations,
        )

        assertTrue(report.gaps.any { it.type == "PARTIAL_RUN" })
        assertEquals(1, results.mutationsEvaluated)
        assertEquals(1, results.totalMutations)
        assertNull(results.mutationScore)
    }

    @Test
    fun `ordinary XML errors set failure status and exclude synthetic test identities`() {
        val xml = """
            <testsuite name="example.BrokenTest">
              <testcase name="executionError"><error type="java.lang.IllegalStateException" /></testcase>
              <testcase name="passes()" />
              <testcase name="passes()" />
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertTrue(report.hasTestFailures)
        assertEquals(listOf("example.BrokenTest::passes()"), report.testMethods)
        assertEquals("TEST_FAILURE", report.gaps.single().type)
    }

    @Test
    fun `strict survivor without captured summary is not a complete run`() {
        val xml = """
            <testsuite name="example.WeakTest">
              <testcase name="executionError"><failure type="io.github.anschnapp.mutflow.MutantSurvivedException" /></testcase>
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertTrue(report.hasTestFailures)
        assertTrue(report.testMethods.isEmpty())
        assertTrue(report.gaps.any { it.type == "NO_OUTPUT" })
    }

    @Test
    fun `escaped system output is parsed without CDATA`() {
        val xml = """
            <testsuite name="example.CalcTest">
              <testcase name="less &lt; than()" />
              <system-out>MUTATION TESTING SUMMARY
            Total mutations discovered: 1
            Tested this run: 1
            Remaining untested: 0
            ✓ (Calc.kt:1) &lt; → &lt;=
                killed by: less &lt; than()
              </system-out>
            </testsuite>
        """.trimIndent()

        val report = read(xml)

        assertEquals("<", report.mutations.single().originalOperator)
        assertEquals("<=", report.mutations.single().variantOperator)
        assertEquals(listOf("example.CalcTest::less < than()"), report.mutations.single().killedByTests)
        assertTrue(report.gaps.isEmpty())
    }

    @Test
    fun `missing suite identity is rejected`() {
        val failure = assertThrows(IllegalArgumentException::class.java) {
            read("""<testsuite><testcase name="passes()" /></testsuite>""")
        }

        assertTrue(failure.message!!.contains("Missing test suite name"))
    }

    @Test
    fun `external entity documents are rejected`() {
        val xml = """<!DOCTYPE testsuite [<!ENTITY secret SYSTEM "file:///nonexistent">]><testsuite name="Test">&secret;</testsuite>"""

        assertThrows(org.xml.sax.SAXParseException::class.java) { read(xml) }
    }
}
