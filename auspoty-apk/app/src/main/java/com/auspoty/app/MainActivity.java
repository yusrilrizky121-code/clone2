package com.auspoty.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private ProgressBar progressBar;
    private Handler keepAliveHandler;
    private Runnable keepAliveRunnable;
    private static final int REQ_ACCOUNTS = 101;

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

        // Daftarkan Android Bridge untuk login Google via AccountManager
        webView.addJavascriptInterface(new GoogleLoginBridge(this, webView), "AndroidBridge");

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

        // Keep-alive: ping WebView setiap 5 detik supaya tidak di-throttle saat background
        keepAliveHandler = new Handler();
        keepAliveRunnable = new Runnable() {
            @Override
            public void run() {
                if (webView != null) {
                    webView.evaluateJavascript("(function(){ return typeof ytPlayer !== 'undefined' ? 1 : 0; })()", null);
                }
                keepAliveHandler.postDelayed(this, 5000);
            }
        };
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        webView.resumeTimers();
        // Minta permission GET_ACCOUNTS untuk login Google via AccountManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.GET_ACCOUNTS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.GET_ACCOUNTS}, REQ_ACCOUNTS);
            }
        }
        // Start foreground service supaya musik tetap jalan di background
        Intent serviceIntent = new Intent(this, MusicService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
        // Mulai keep-alive
        keepAliveHandler.post(keepAliveRunnable);
    }

    @Override
    protected void onPause() {
        super.onPause();
        // JANGAN panggil webView.onPause() atau webView.pauseTimers()
        // supaya YouTube player tidak berhenti saat background
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (keepAliveHandler != null) keepAliveHandler.removeCallbacks(keepAliveRunnable);
        stopService(new Intent(this, MusicService.class));
        webView.destroy();
    }
}
