plugins {
    kotlin("jvm") version "2.4.20"
    id("io.github.anschnapp.mutflow") version "1.6.0"
}

apply(from = rootProject.file("../.omp/mutation-results.gradle.kts"))

kotlin {
    jvmToolchain(26)
}

repositories {
    mavenCentral()
}
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        showStandardStreams = true
        events("passed", "skipped", "failed")
    }
}

mutflow {
    enabled = true
    targets = listOf("example.Calculator")
}
