package com.auspoty.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.PowerManager;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private ProgressBar progressBar;
    private Handler keepAliveHandler;
    private Runnable keepAliveRunnable;
    private PowerManager.WakeLock webViewWakeLock;
    private static final int REQ_LOGIN = 102;

    private static final String APP_URL = "file:///android_asset/index.html";
    private static final String API_HOST = "clone2-iyrr-git-master-yusrilrizky121-codes-projects.vercel.app";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);
        swipeRefresh = findViewById(R.id.swipe_refresh);
        progressBar = findViewById(R.id.progress_bar);

        // WebView settings
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setUserAgentString(settings.getUserAgentString() + " AuspotyApp/1.0");

        // Daftarkan Android Bridge — buka LoginActivity saat user klik login
        webView.addJavascriptInterface(new Object() {
            @android.webkit.JavascriptInterface
            public void openGoogleLogin() {
                Intent intent = new Intent(MainActivity.this, LoginActivity.class);
                startActivityForResult(intent, REQ_LOGIN);
            }
            @android.webkit.JavascriptInterface
            public boolean isLoggedIn() {
                SharedPreferences prefs = getSharedPreferences("auspoty_login", MODE_PRIVATE);
                return prefs.getBoolean("isLoggedIn", false);
            }
            @android.webkit.JavascriptInterface
            public String getAccountName() {
                SharedPreferences prefs = getSharedPreferences("auspoty_login", MODE_PRIVATE);
                return prefs.getString("accountName", "");
            }
            @android.webkit.JavascriptInterface
            public void logout() {
                SharedPreferences prefs = getSharedPreferences("auspoty_login", MODE_PRIVATE);
                prefs.edit().clear().apply();
                runOnUiThread(() -> webView.evaluateJavascript(
                    "localStorage.removeItem('auspotyGoogleUser'); if(typeof updateProfileUI==='function') updateProfileUI();", null));
            }
            @android.webkit.JavascriptInterface
            public boolean isAndroid() { return true; }

            // Dipanggil dari JS saat lagu mulai diputar
            @android.webkit.JavascriptInterface
            public void onMusicPlay(String title, String artist) {
                // Acquire WakeLock agar layar/CPU tidak sleep
                if (webViewWakeLock != null && !webViewWakeLock.isHeld()) {
                    webViewWakeLock.acquire(4 * 60 * 60 * 1000L);
                }
                // Update foreground service dengan info lagu
                Intent svc = new Intent(MainActivity.this, MusicService.class);
                svc.putExtra(MusicService.EXTRA_TITLE, title != null ? title : "Auspoty");
                svc.putExtra(MusicService.EXTRA_ARTIST, artist != null ? artist : "Sedang diputar...");
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(svc);
                } else {
                    startService(svc);
                }
            }

            // Dipanggil dari JS saat lagu pause/stop
            @android.webkit.JavascriptInterface
            public void onMusicPause() {
                if (webViewWakeLock != null && webViewWakeLock.isHeld()) {
                    webViewWakeLock.release();
                }
            }
        }, "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                // Izinkan semua request dari dalam WebView (fetch/XHR/iframe)
                if (!request.hasGesture()) {
                    return false;
                }
                // Navigasi user: izinkan file://, API, YouTube
                if (url.startsWith("file://") || url.contains(API_HOST)) {
                    return false;
                }
                if (url.contains("youtube.com") || url.contains("youtu.be") || url.contains("ytimg.com")) {
                    return false;
                }
                // Link eksternal lain buka di browser
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                } catch (Exception e) {}
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                swipeRefresh.setRefreshing(false);
                progressBar.setVisibility(View.GONE);
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });

        // Swipe to refresh
        swipeRefresh.setColorSchemeColors(0xFF1ed760);
        swipeRefresh.setProgressBackgroundColorSchemeColor(0xFF282828);
        swipeRefresh.setOnRefreshListener(() -> webView.reload());

        webView.loadUrl(APP_URL);

        // Cegah WebView di-throttle saat background
        webView.setKeepScreenOn(false); // jangan paksa layar nyala, tapi...
        // ...pastikan rendering tetap aktif
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            webView.getSettings().setOffscreenPreRaster(true);
        }

        // WakeLock untuk WebView — cegah CPU sleep saat musik background
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm != null) {
            webViewWakeLock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "Auspoty::WebViewWakeLock"
            );
            webViewWakeLock.setReferenceCounted(false);
        }

        // Keep-alive: ping WebView setiap 1 detik supaya tidak di-throttle saat background
        keepAliveHandler = new Handler();
        keepAliveRunnable = new Runnable() {
            @Override
            public void run() {
                if (webView != null) {
                    // Cek state player dan trigger next song jika ended
                    webView.evaluateJavascript(
                        "(function(){" +
                        "  if(typeof ytPlayer!=='undefined'&&ytPlayer&&typeof ytPlayer.getPlayerState==='function'){" +
                        "    var s=ytPlayer.getPlayerState();" +
                        "    if(s===0){" + // ENDED
                        "      if(typeof isRepeat!=='undefined'&&isRepeat){ytPlayer.seekTo(0);ytPlayer.playVideo();}" +
                        "      else if(typeof playNextSimilarSong==='function'){playNextSimilarSong();}" +
                        "    } else if(s===2&&typeof isPlaying!=='undefined'&&isPlaying){" + // PAUSED tapi harusnya playing
                        "      ytPlayer.playVideo();" +
                        "    }" +
                        "  }" +
                        "  if(typeof _bgAudioCtx!=='undefined'&&_bgAudioCtx&&_bgAudioCtx.state==='suspended'){" +
                        "    _bgAudioCtx.resume();" +
                        "  }" +
                        "  return 1;" +
                        "})()", null);
                }
                keepAliveHandler.postDelayed(this, 1000);
            }
        };
    }

    private long lastBackPressTime = 0;

    // View utama yang trigger double-back (home, search, library)
    // Settings → kembali ke home, bukan exit
    private static final String[] DOUBLE_BACK_VIEWS = {"view-home", "view-search", "view-library"};

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            // Langsung cek view aktif via JS (tidak pakai canGoBack karena history dikelola JS)
            webView.evaluateJavascript(
                "(function(){ " +
                "  var active = document.querySelector('.view-section.active');" +
                "  return active ? active.id : 'view-home';" +
                "})()",
                result -> {
                    if (result == null) result = ""view-home"";
                    // Hapus tanda kutip dari hasil JS
                    final String viewId = result.replace(""", "").trim();

                    // Cek apakah ini view yang trigger double-back
                    boolean isDoubleBackView = false;
                    for (String v : DOUBLE_BACK_VIEWS) {
                        if (v.equals(viewId)) { isDoubleBackView = true; break; }
                    }

                    if (isDoubleBackView) {
                        // Di home/search/library — double back to exit
                        long now = System.currentTimeMillis();
                        if (now - lastBackPressTime < 2000) {
                            // Tekan 2x → minimize app (bukan kill)
                            runOnUiThread(() -> moveTaskToBack(true));
                        } else {
                            lastBackPressTime = now;
                            runOnUiThread(() ->
                                android.widget.Toast.makeText(
                                    MainActivity.this,
                                    "Tekan sekali lagi untuk keluar",
                                    android.widget.Toast.LENGTH_SHORT
                                ).show()
                            );
                        }
                    } else {
                        // Di settings atau view sub → kembali ke home
                        runOnUiThread(() ->
                            webView.evaluateJavascript(
                                "if(typeof switchView==='function') switchView('home');", null)
                        );
                    }
                }
            );
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        webView.resumeTimers();
        // Start foreground service supaya musik tetap jalan di background
        Intent serviceIntent = new Intent(this, MusicService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
        // Mulai keep-alive
        keepAliveHandler.post(keepAliveRunnable);
        // Resume AudioContext dan player jika perlu
        webView.evaluateJavascript(
            "(function(){" +
            "  if(typeof _bgAudioCtx!=='undefined'&&_bgAudioCtx&&_bgAudioCtx.state==='suspended'){_bgAudioCtx.resume();}" +
            "  if(typeof ytPlayer!=='undefined'&&ytPlayer&&typeof ytPlayer.getPlayerState==='function'){" +
            "    var s=ytPlayer.getPlayerState();" +
            "    if(s===2&&typeof isPlaying!=='undefined'&&isPlaying){ytPlayer.playVideo();}" +
            "  }" +
            "})()", null);
    }

    @Override
    protected void onPause() {
        super.onPause();
        // JANGAN panggil webView.onPause() atau webView.pauseTimers()
        // supaya YouTube player tidak berhenti saat background
        // WebView tetap aktif, WakeLock menjaga CPU tetap jalan
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (keepAliveHandler != null) keepAliveHandler.removeCallbacks(keepAliveRunnable);
        if (webViewWakeLock != null && webViewWakeLock.isHeld()) webViewWakeLock.release();
        stopService(new Intent(this, MusicService.class));
        webView.destroy();
    }

    // Terima hasil dari LoginActivity
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_LOGIN && resultCode == RESULT_OK && data != null) {
            String accountName = data.getStringExtra("accountName");
            if (accountName == null) accountName = "Pengguna Google";
            final String name = accountName;
            final String email = name.contains("@") ? name : name + "@gmail.com";
            // Inject user data ke localStorage WebView
            webView.evaluateJavascript(
                "(function(){" +
                "var user={name:'" + name.replace("'", "\\'") + "'," +
                "email:'" + email.replace("'", "\\'") + "'," +
                "picture:'',sub:'" + email.replace("'", "\\'") + "'};" +
                "localStorage.setItem('auspotyGoogleUser',JSON.stringify(user));" +
                "if(typeof updateProfileUI==='function') updateProfileUI();" +
                "if(typeof showToast==='function') showToast('Selamat datang, " + name.replace("'", "\\'") + "!');" +
                "})()", null);
        }
    }
}
