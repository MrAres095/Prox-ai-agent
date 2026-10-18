# Prox AI Chat (Android)

Minimal Android client for the existing Prox AI Agent web UI. It keeps the agent's existing login/session and offers a configurable server URL (default: `http://192.168.1.129:8088`). File chooser support is enabled for image inputs exposed by the server UI.

## Build
Open `android-chat` in Android Studio and build the debug APK, or use the repository workflow. This first client wraps the existing web chat; image analysis requires the backend chat UI/API to accept image attachments and a vision-capable model.
