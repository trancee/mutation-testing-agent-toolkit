package ch.trancee.mutation

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class MutationResultsSerializerTest {

    companion object {
        val testJson = Json { ignoreUnknownKeys = true }
    }

    @Test
    fun `serializes killed mutation with both killer fields`() {
        val mutations = listOf(
            MutationResult(
                sourceLocation = "(Calculator.kt:7)",
                originalOperator = ">",
                variantOperator = ">=",
                result = MutationResultType.Killed,
                killedByTest = "testIsPositive",
                killedByTests = listOf("testIsPositive", "testIsPositiveBoundary"),
            ),
        )
        val results = MutationResultsParser.assembleResults(
            mutations = mutations,
            testMethods = listOf("testIsPositive", "testIsPositiveBoundary"),
            generatedAt = 1700000000000L,
        )

        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject

        // Verify backward-compatible field names
        assertNotNull(parsed["generatedAt"])
        assertNotNull(parsed["mutationScore"])
        assertNotNull(parsed["qualityBand"])
        assertNotNull(parsed["confidence"])
        assertNotNull(parsed["totalMutations"])
        assertNotNull(parsed["killed"])
        assertNotNull(parsed["survived"])
        assertNotNull(parsed["timedOut"])
        assertNotNull(parsed["testMethods"])
        assertNotNull(parsed["testKillerMatrix"])
        assertNotNull(parsed["mutations"])

        // Verify mutation fields
        val firstMutation = parsed["mutations"]!!.jsonArray[0].jsonObject
        assertEquals("(Calculator.kt:7)", firstMutation["sourceLocation"]!!.jsonPrimitive.content)
        assertEquals(">", firstMutation["originalOperator"]!!.jsonPrimitive.content)
        assertEquals(">=", firstMutation["variantOperator"]!!.jsonPrimitive.content)
        assertEquals("Killed", firstMutation["result"]!!.jsonPrimitive.content)
        assertEquals("testIsPositive", firstMutation["killedByTest"]!!.jsonPrimitive.content)
        val killedByTests = firstMutation["killedByTests"]!!.jsonArray.map { it.jsonPrimitive.content }
        assertEquals(2, killedByTests.size)
        assertTrue(killedByTests.contains("testIsPositive"))
        assertTrue(killedByTests.contains("testIsPositiveBoundary"))
    }

    @Test
    fun `serializes survived mutation with null killer fields`() {
        val mutations = listOf(
            MutationResult(
                sourceLocation = "(Calculator.kt:8)",
                originalOperator = ">=",
                variantOperator = ">",
                result = MutationResultType.Survived,
            ),
        )
        val results = MutationResultsParser.assembleResults(mutations, listOf("testFoo"))

        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject
        val firstMutation = parsed["mutations"]!!.jsonArray[0].jsonObject

        assertEquals("Survived", firstMutation["result"]!!.jsonPrimitive.content)
        assertEquals(JsonNull, firstMutation["killedByTest"])
        assertTrue(firstMutation["killedByTests"]!!.jsonArray.isEmpty())
    }

    @Test
    fun `testKillerMatrix maps test names to mutation source locations`() {
        val mutations = listOf(
            MutationResult(
                sourceLocation = "(Calculator.kt:7)",
                originalOperator = ">",
                variantOperator = ">=",
                result = MutationResultType.Killed,
                killedByTests = listOf("testIsPositive"),
            ),
            MutationResult(
                sourceLocation = "(Calculator.kt:24)",
                originalOperator = ">",
                variantOperator = ">=",
                result = MutationResultType.Killed,
                killedByTests = listOf("testIsPositive", "testPositiveNumbers"),
            ),
        )
        val results = MutationResultsParser.assembleResults(mutations, listOf("testIsPositive", "testPositiveNumbers"))

        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject
        val matrix = parsed["testKillerMatrix"]!!.jsonObject

        assertTrue(matrix.containsKey("testIsPositive"))
        val testIsPositiveLocations = matrix["testIsPositive"]!!.jsonArray.map { it.jsonPrimitive.content }
        assertTrue(testIsPositiveLocations.contains("(Calculator.kt:7)"))
        assertTrue(testIsPositiveLocations.contains("(Calculator.kt:24)"))
        assertTrue(matrix.containsKey("testPositiveNumbers"))
    }

    @Test
    fun `quality band and confidence are serialized as strings`() {
        val mutations = (1..20).map {
            MutationResult(
                sourceLocation = "(Calculator.kt:$it)",
                originalOperator = ">",
                variantOperator = ">=",
                result = MutationResultType.Killed,
                killedByTest = "test",
                killedByTests = listOf("test"),
            )
        }
        val results = MutationResultsParser.assembleResults(mutations, listOf("test"))

        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject

        assertEquals("Excellent", parsed["qualityBand"]!!.jsonPrimitive.content)
        assertEquals("Medium", parsed["confidence"]!!.jsonPrimitive.content)
        assertEquals(20, parsed["totalMutations"]!!.jsonPrimitive.int)
        assertEquals(20, parsed["killed"]!!.jsonPrimitive.int)
    }
    @Test
    fun `serializes gaps and confidence interval fields`() {
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Killed, "testA", listOf("testA")),
            MutationResult("(Calc.kt:8)", ">=", ">", MutationResultType.Survived),
        )
        val results = MutationResultsParser.assembleResults(
            mutations = mutations,
            testMethods = listOf("testA"),
            generatedAt = 1700000000000L,
            gaps = listOf(ExecutionGap(type = "NO_OUTPUT", reason = "test class skipped")),
        )
        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject

        assertNotNull(parsed["gaps"])
        assertEquals(1, parsed["gaps"]!!.jsonPrimitive.int)
        assertNotNull(parsed["mutationsEvaluated"])
        assertEquals(2, parsed["mutationsEvaluated"]!!.jsonPrimitive.int)
        assertEquals(2, parsed["schemaVersion"]!!.jsonPrimitive.int)
        assertEquals(JsonNull, parsed["mutationScore"])
        assertNotNull(parsed["confidenceIntervalLow"])
        assertNotNull(parsed["confidenceIntervalHigh"])
        assertNotNull(parsed["executionGaps"])
        assertEquals("NO_OUTPUT", parsed["executionGaps"]!!.jsonArray[0].jsonObject["type"]!!.jsonPrimitive.content)
    }

    @Test
    fun `serializes redundantGroups`() {
        val mutations = List(6) { i ->
            MutationResult("(Calc.kt:$i)", ">", ">=", MutationResultType.Killed, null,
                listOf("testA", "testB", "testC", "testD", "testE", "testF"))
        }
        val results = MutationResultsParser.assembleResults(
            mutations = mutations,
            testMethods = listOf("testA", "testB", "testC", "testD", "testE", "testF"),
            generatedAt = 1700000000000L,
        )
        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject

        assertNotNull(parsed["redundantGroups"])
        assertEquals(1, parsed["redundantGroups"]!!.jsonArray.size)
        val group = parsed["redundantGroups"]!!.jsonArray[0].jsonObject
        assertEquals(6, group["count"]!!.jsonPrimitive.int)
        assertEquals(6, group["tests"]!!.jsonArray.size)
    }

    @Test
    fun `budgeted schema two report serializes untested counts and qualified session identity`() {
        val mutation = MutationResult(
            "Calc.kt:1", ">", ">=", MutationResultType.Killed,
            "example.CalcTest::boundary()", listOf("example.CalcTest::boundary()"),
            testClass = "example.CalcTest",
        )
        val results = MutationResultsParser.assembleResults(
            listOf(mutation), listOf("example.CalcTest::boundary()"),
            generatedAt = 1700000000000L, discoveredMutations = 4,
        )

        val parsed = testJson.parseToJsonElement(MutationResultsSerializer.toJson(results)).jsonObject

        assertEquals(2, parsed["schemaVersion"]!!.jsonPrimitive.int)
        assertEquals(4, parsed["totalMutations"]!!.jsonPrimitive.int)
        assertEquals(1, parsed["mutationsEvaluated"]!!.jsonPrimitive.int)
        assertEquals(3, parsed["untestedMutations"]!!.jsonPrimitive.int)
        assertEquals("example.CalcTest",
            parsed["mutations"]!!.jsonArray.single().jsonObject["testClass"]!!.jsonPrimitive.content)
        assertEquals(listOf("Calc.kt:1"),
            parsed["testKillerMatrix"]!!.jsonObject["example.CalcTest::boundary()"]!!
                .jsonArray.map { it.jsonPrimitive.content })
    }

    @Test
    fun `null mutationScore when all mutations are gaps`() {
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Survived),
        )
        val results = MutationResultsParser.assembleResults(
            mutations = mutations,
            testMethods = listOf("testA"),
            generatedAt = 1700000000000L,
            gaps = listOf(ExecutionGap(type = "COMPILATION_FAILURE", reason = "IR transform error")),
        )
        val json = MutationResultsSerializer.toJson(results)
        val parsed = testJson.parseToJsonElement(json).jsonObject

        // Gaps invalidate the score, not recorded mutation outcomes.
        assertEquals(JsonNull, parsed["mutationScore"])
        assertEquals(1, parsed["mutationsEvaluated"]!!.jsonPrimitive.int)
        assertEquals(1, parsed["gaps"]!!.jsonPrimitive.int)
    }
}
