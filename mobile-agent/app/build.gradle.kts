plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android {
    namespace = "uk.mandocloud.proxaagent"
    compileSdk = 35
    defaultConfig { applicationId = "uk.mandocloud.proxaagent"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "0.1.0" }
}
