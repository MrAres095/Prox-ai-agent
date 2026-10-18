package uk.mandocloud.proxaichat;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.graphics.Color;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_REQUEST = 2417;
    private static final String APK_URL = "https://github.com/MrAres095/Prox-ai-agent/releases/download/android-chat-latest/ProxAiChat.apk";
    private WebView web;
    private ProgressBar progress;
    private ValueCallback<Uri[]> uploadCallback;
    private SharedPreferences prefs;
    private String serverUrl;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("agent", MODE_PRIVATE);
        serverUrl = prefs.getString("url", "http://192.168.1.129:8088");
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(15, 18, 28));
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        bar.setPadding(16, 10, 12, 10);
        TextView title = new TextView(this);
        title.setText("Prox AI Chat");
        title.setTextColor(Color.WHITE);
        title.setTextSize(19);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        bar.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        TextView update = new TextView(this);
        update.setText("↻ Ažuriraj");
        update.setTextColor(Color.rgb(160, 205, 255));
        update.setTextSize(14);
        update.setPadding(10, 12, 12, 12);
        update.setOnClickListener(v -> downloadUpdate());
        bar.addView(update);
        TextView settings = new TextView(this);
        settings.setText("⋮");
        settings.setTextColor(Color.WHITE);
        settings.setTextSize(30);
        settings.setPadding(10, 0, 8, 0);
        settings.setOnClickListener(v -> showServerSettings());
        bar.addView(settings);
        root.addView(bar);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        root.addView(progress, new LinearLayout.LayoutParams(-1, 4));
        web = new WebView(this);
        WebSettings ws = web.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(false);
        ws.setLoadsImagesAutomatically(true);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int value) {
                progress.setProgress(value);
                progress.setVisibility(value >= 100 ? View.GONE : View.VISIBLE);
            }
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (uploadCallback != null) uploadCallback.onReceiveValue(null);
                uploadCallback = callback;
                Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("image/*");
                try { startActivityForResult(Intent.createChooser(pick, "Odaberi sliku"), FILE_CHOOSER_REQUEST); }
                catch (Exception e) { uploadCallback = null; return false; }
                return true;
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        loadServer();
    }

    private void downloadUpdate() {
        new AlertDialog.Builder(this)
            .setTitle("Ažuriranje aplikacije")
            .setMessage("Aplikacija će preuzeti najnoviji APK. Nakon preuzimanja otvori obavijest i potvrdi instalaciju. Android ne dopušta tihu instalaciju bez sistemske potvrde.")
            .setNegativeButton("Odustani", null)
            .setPositiveButton("Preuzmi", (d, w) -> {
                try {
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(APK_URL));
                    request.setTitle("Prox AI Chat — ažuriranje");
                    request.setDescription("Preuzimanje najnovije verzije");
                    request.setMimeType("application/vnd.android.package-archive");
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "ProxAiChat-update.apk");
                    DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    manager.enqueue(request);
                    Toast.makeText(this, "Preuzimanje je pokrenuto. Instalaciju potvrdi iz obavijesti.", Toast.LENGTH_LONG).show();
                } catch (Exception e) {
                    new AlertDialog.Builder(this).setMessage("Nije moguće pokrenuti preuzimanje: " + e.getMessage()).setPositiveButton("OK", null).show();
                }
            }).show();
    }

    private void loadServer() {
        if (!serverUrl.startsWith("http://") && !serverUrl.startsWith("https://")) serverUrl = "http://" + serverUrl;
        web.loadUrl(serverUrl);
    }

    private void showServerSettings() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(serverUrl);
        input.setHint("http://192.168.1.129:8088");
        new AlertDialog.Builder(this).setTitle("Adresa agenta").setMessage("Unesi LAN adresu ili HTTPS domenu agenta.")
            .setView(input).setNegativeButton("Odustani", (d,w) -> {})
            .setPositiveButton("Spremi", (d,w) -> {
                String value = input.getText().toString().trim();
                if (!value.isEmpty() && (value.startsWith("http://") || value.startsWith("https://"))) {
                    serverUrl = value.replaceAll("/+$", "");
                    prefs.edit().putString("url", serverUrl).apply();
                    loadServer();
                } else {
                    new AlertDialog.Builder(this).setMessage("Adresa mora početi s http:// ili https://").setPositiveButton("OK", null).show();
                }
            }).show();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST && uploadCallback != null) {
            Uri[] results = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) results = new Uri[]{data.getData()};
            uploadCallback.onReceiveValue(results);
            uploadCallback = null;
        }
    }

    @Override public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
