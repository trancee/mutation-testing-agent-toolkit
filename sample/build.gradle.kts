plugins {
    kotlin("jvm") version "2.4.20"
    id("io.github.anschnapp.mutflow") version "1.6.1"
}

apply(from = rootProject.file("../.mutation-testing/mutation-results.gradle.kts"))

kotlin {
    jvmToolchain(26)
}

repositories {
    mavenCentral()
}
dependencies {
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.6.1")
    testImplementation("junit:junit:4.13.2")
}

extra["mutationTest.junitFramework"] = "junit4"

tasks.test {
    testLogging {
        showStandardStreams = true
        events("passed", "skipped", "failed")
    }
}

mutflow {
    enabled = true
    targets = listOf("example.Calculator")
}
