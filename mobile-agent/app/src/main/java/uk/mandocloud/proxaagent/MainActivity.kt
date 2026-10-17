package uk.mandocloud.proxaagent

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var web: WebView
    private val prefs by lazy { getSharedPreferences("agent", MODE_PRIVATE) }
    private val defaultUrl = "http://192.168.1.129:8088"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        CookieManager.getInstance().setAcceptCookie(true)
        showConnectScreen(prefs.getString("url", defaultUrl) ?: defaultUrl)
    }

    private fun showConnectScreen(initial: String) {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 44, 28, 24)
            setBackgroundColor(Color.rgb(15, 23, 42))
        }
        root.addView(TextView(this).apply {
            text = "✦  Prox AI Agent\n\nPoveži se sa svojim privatnim agentom"
            textSize = 25f; setTextColor(Color.WHITE)
        })
        root.addView(TextView(this).apply {
            text = "Unesi LAN adresu ili HTTPS domenu. Zadana je adresa agenta na kućnoj mreži."
            textSize = 15f; setTextColor(Color.LTGRAY); setPadding(0, 20, 0, 18)
        })
        val url = EditText(this).apply {
            setSingleLine(true); setText(initial); textSize = 16f
            hint = "http://192.168.1.129:8088"; setTextColor(Color.WHITE); setHintTextColor(Color.GRAY)
            setPadding(14, 14, 14, 14); setBackgroundColor(Color.rgb(30, 41, 59))
        }
        root.addView(url, LinearLayout.LayoutParams(-1, -2))
        root.addView(Button(this).apply {
            text = "Poveži se"
            setOnClickListener {
                var value = url.text.toString().trim().trimEnd('/')
                if (!value.startsWith("http://") && !value.startsWith("https://")) value = "https://$value"
                if (value.length < 10 || value.contains(' ')) {
                    Toast.makeText(this@MainActivity, "Provjeri adresu agenta.", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                prefs.edit().putString("url", value).apply()
                showAgent(value)
            }
        }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = 18 })
        root.addView(TextView(this).apply {
            text = "Koristi HTTP samo na pouzdanoj privatnoj LAN mreži. Za pristup izvana postavi HTTPS preko Cloudflare Tunnel ili VPN-a."
            textSize = 12f; setTextColor(Color.LTGRAY); setPadding(0, 24, 0, 0)
        })
        setContentView(root)
    }

    private fun showAgent(url: String) {
        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.loadsImagesAutomatically = true
        web.settings.allowFileAccess = false
        web.webChromeClient = WebChromeClient()
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val target = request.url
                val origin = android.net.Uri.parse(url)
                return if (target.host == origin.host) false else {
                    try { startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, target)) } catch (_: Exception) {}
                    true
                }
            }
            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: android.webkit.WebResourceError) {
                if (request.isForMainFrame) Toast.makeText(this@MainActivity, "Agent nije dostupan. Provjeri adresu i mrežu.", Toast.LENGTH_LONG).show()
            }
        }
        web.loadUrl(url)
        setContentView(web)
    }

    override fun onBackPressed() {
        if (::web.isInitialized && web.canGoBack()) web.goBack()
        else showConnectScreen(prefs.getString("url", defaultUrl) ?: defaultUrl)
    }

    override fun onDestroy() {
        if (::web.isInitialized) { web.stopLoading(); web.destroy() }
        super.onDestroy()
    }
}