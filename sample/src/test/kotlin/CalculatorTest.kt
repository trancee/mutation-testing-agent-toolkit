package example

import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit4.MutFlowRunner
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Tests for [Calculator] use MutFlowRunner to run baseline (run 0) and
 * one mutation per run (run 1+).
 *
 * Each test wraps business logic calls in MutFlow.underTest { } so
 * mutflow can activate mutations during mutation runs.
 */
@RunWith(MutFlowRunner::class)
class CalculatorTest {

    private val calc = Calculator()

    @Test
    fun testIsPositive() {
        assertTrue(MutFlow.underTest { calc.isPositive(5) })
        assertFalse(MutFlow.underTest { calc.isPositive(-1) })
        assertFalse(MutFlow.underTest { calc.isPositive(0) }) // kills >→>=
        assertTrue(MutFlow.underTest { calc.isPositive(1) })  // kills 0→1
    }

    @Test
    fun testIsInRange() {
        assertTrue(MutFlow.underTest { calc.isInRange(5, 1, 10) })
        assertFalse(MutFlow.underTest { calc.isInRange(0, 1, 10) })
        assertFalse(MutFlow.underTest { calc.isInRange(11, 1, 10) })
        assertTrue(MutFlow.underTest { calc.isInRange(1, 1, 10) })
        assertTrue(MutFlow.underTest { calc.isInRange(10, 1, 10) })
    }

    @Test
    fun testAdd() {
        assertEquals(7, MutFlow.underTest { calc.add(3, 4) })
        assertEquals(0, MutFlow.underTest { calc.add(-5, 5) })
        assertEquals(-8, MutFlow.underTest { calc.add(-3, -5) })
    }

    @Test
    fun testMultiply() {
        assertEquals(12, MutFlow.underTest { calc.multiply(3, 4) })
        assertEquals(0, MutFlow.underTest { calc.multiply(0, 5) })
        assertEquals(-15, MutFlow.underTest { calc.multiply(-3, 5) })
    }

    @Test
    fun testIsValid() {
        assertTrue(MutFlow.underTest { calc.isValid(50) })
        assertFalse(MutFlow.underTest { calc.isValid(-1) })
        assertFalse(MutFlow.underTest { calc.isValid(150) })
        assertFalse(MutFlow.underTest { calc.isValid(0) })  // kills >→>= + 0→-1
        assertTrue(MutFlow.underTest { calc.isValid(1) })   // kills 0→1
        assertTrue(MutFlow.underTest { calc.isValid(99) })  // kills 100→99
        assertFalse(MutFlow.underTest { calc.isValid(100) }) // kills 100→101 + <→<=
    }

    @Test
    fun testHasDiscount() {
        assertTrue(MutFlow.underTest { calc.hasDiscount(isMember = true, total = 0.0) })
        assertFalse(MutFlow.underTest { calc.hasDiscount(isMember = false, total = 10.0) })
        assertTrue(MutFlow.underTest { calc.hasDiscount(isMember = false, total = 50.0) })
        assertFalse(MutFlow.underTest { calc.hasDiscount(isMember = false, total = 49.0) }) // kills 50→49
    }

    @Test
    fun testGreet() {
        assertEquals("Hello, World", MutFlow.underTest { calc.greet("World") })
        assertEquals("Hello, stranger", MutFlow.underTest { calc.greet(null) })
    }

    @Test
    fun testIsEmpty() {
        assertTrue(MutFlow.underTest { calc.isEmpty(0) })
        assertFalse(MutFlow.underTest { calc.isEmpty(5) })
    }

    /**
     * Tests validateInput — throws `IllegalArgumentException` for negative values.
     * ExceptionTypeSwapOperator swaps IllegalArgumentException →
     * IllegalStateException on this test.
     */
    @Test
    fun testValidateInput() {
        assertEquals(5, MutFlow.underTest { calc.validateInput(5) })
        assertEquals(0, MutFlow.underTest { calc.validateInput(0) })

        val exception = try {
            MutFlow.underTest { calc.validateInput(-1) }
            "no-exception"
        } catch (e: IllegalArgumentException) {
            "IllegalArgumentException"
        }
        assertEquals(
            "validateInput(-1) should throw IllegalArgumentException",
            "IllegalArgumentException",
            exception,
        )
    }

    /**
     * Exercises isPositive through a different path — overlaps with testIsPositive
     * on line 24 mutations (>→>=, 0→1, 0→-1), creating multi-killer scenarios
     * that verify mutflow records every test that kills a mutation.
     */
    @Test
    fun testIsPositiveBoundary() {
        assertTrue(MutFlow.underTest { calc.isPositive(5) })    // kills >→>= via 0
        assertFalse(MutFlow.underTest { calc.isPositive(0) })   // kills >→>= via 0
        assertFalse(MutFlow.underTest { calc.isPositive(-3) }) // kills >→<
        assertTrue(MutFlow.underTest { calc.isPositive(1) })    // kills 0→1
    }

    /**
     * Exercises isPositive indirectly — also overlaps with testIsPositive
     * on line 24, further verifying multi-killer tracking.
     */
    @Test
    fun testPositiveNumbers() {
        assertTrue(MutFlow.underTest { calc.isPositive(10) })
        assertFalse(MutFlow.underTest { calc.isPositive(0) })
        assertTrue(MutFlow.underTest { calc.isPositive(1) })
    }

}
