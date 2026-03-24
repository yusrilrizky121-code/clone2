package com.auspoty.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.PowerManager;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.DownloadListener;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import java.io.File;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private ProgressBar progressBar;
    private Handler keepAliveHandler;
    private Runnable keepAliveRunnable;
    private PowerManager.WakeLock webViewWakeLock;
    private static final int REQ_LOGIN = 102;
    private long activeDownloadId = -1;
    private BroadcastReceiver downloadReceiver;

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

            // Download MP3 via DownloadManager Android
            @android.webkit.JavascriptInterface
            public void downloadFile(String url, String filename) {
                try {
                    String safeFilename = filename.replaceAll("[/:*?\"<>|]", "_");
                    if (!safeFilename.endsWith(".mp3")) safeFilename += ".mp3";
                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                    req.setTitle(safeFilename.replace(".mp3", ""));
                    req.setDescription("Mengunduh lagu...");
                    req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    req.setDestinationInExternalPublicDir(Environment.DIRECTORY_MUSIC, "Auspoty/" + safeFilename);
                    req.allowScanningByMediaScanner();
                    activeDownloadId = dm.enqueue(req);
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Download dimulai: " + safeFilename, Toast.LENGTH_SHORT).show());
                } catch (Exception e) {
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Gagal download: " + e.getMessage(), Toast.LENGTH_LONG).show());
                }
            }

            // Cek apakah lagu sudah ada di lokal (offline)
            @android.webkit.JavascriptInterface
            public boolean isOfflineAvailable(String videoId) {
                File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC), "Auspoty");
                if (!dir.exists()) return false;
                File[] files = dir.listFiles();
                if (files == null) return false;
                for (File f : files) {
                    if (f.getName().contains(videoId)) return true;
                }
                return false;
            }

            // Ambil path file offline untuk diputar
            @android.webkit.JavascriptInterface
            public String getOfflineFilePath(String videoId) {
                File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC), "Auspoty");
                if (!dir.exists()) return "";
                File[] files = dir.listFiles();
                if (files == null) return "";
                for (File f : files) {
                    if (f.getName().contains(videoId)) return "file://" + f.getAbsolutePath();
                }
                return "";
            }

            // Ambil semua lagu offline sebagai JSON
            @android.webkit.JavascriptInterface
            public String getOfflineSongs() {
                File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC), "Auspoty");
                if (!dir.exists()) return "[]";
                File[] files = dir.listFiles();
                if (files == null || files.length == 0) return "[]";
                StringBuilder sb = new StringBuilder("[");
                for (int i = 0; i < files.length; i++) {
                    String name = files[i].getName().replace(".mp3", "");
                    sb.append("{\"filename\":\"").append(name.replace("\"", "\\\""))
                      .append("\",\"path\":\"file://").append(files[i].getAbsolutePath().replace("\"", "\\\""))
                      .append("\"}");
                    if (i < files.length - 1) sb.append(",");
                }
                sb.append("]");
                return sb.toString();
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

        // Request storage permission untuk download
        requestStoragePermission();

        // DownloadListener — tangkap semua download dari WebView
        webView.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) -> {
            try {
                String filename = "auspoty_music.mp3";
                if (contentDisposition != null && contentDisposition.contains("filename=")) {
                    filename = contentDisposition.substring(contentDisposition.indexOf("filename=") + 9).replace("\"", "").trim();
                }
                DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.setTitle(filename.replace(".mp3", ""));
                req.setDescription("Mengunduh lagu...");
                req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                req.setDestinationInExternalPublicDir(Environment.DIRECTORY_MUSIC, "Auspoty/" + filename);
                req.allowScanningByMediaScanner();
                req.addRequestHeader("User-Agent", userAgent);
                activeDownloadId = dm.enqueue(req);
                Toast.makeText(this, "Download dimulai: " + filename, Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Toast.makeText(this, "Gagal download: " + e.getMessage(), Toast.LENGTH_LONG).show();
            }
        });

        // BroadcastReceiver — notifikasi JS saat download selesai
        downloadReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                if (id == activeDownloadId) {
                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    DownloadManager.Query q = new DownloadManager.Query();
                    q.setFilterById(id);
                    Cursor c = dm.query(q);
                    if (c != null && c.moveToFirst()) {
                        int statusIdx = c.getColumnIndex(DownloadManager.COLUMN_STATUS);
                        int status = statusIdx >= 0 ? c.getInt(statusIdx) : -1;
                        if (status == DownloadManager.STATUS_SUCCESSFUL) {
                            runOnUiThread(() -> webView.evaluateJavascript(
                                "if(typeof showToast==='function') showToast('Download selesai! Lagu tersimpan di Music/Auspoty');", null));
                        } else {
                            runOnUiThread(() -> webView.evaluateJavascript(
                                "if(typeof showToast==='function') showToast('Download gagal, coba lagi');", null));
                        }
                        c.close();
                    }
                }
            }
        };
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(downloadReceiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE), Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(downloadReceiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
        }

        // Cegah WebView di-throttle saat background
        webView.setKeepScreenOn(false);
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
                    webView.evaluateJavascript(
                        "(function(){" +
                        "  if(typeof ytPlayer!=='undefined'&&ytPlayer&&typeof ytPlayer.getPlayerState==='function'){" +
                        "    var s=ytPlayer.getPlayerState();" +
                        "    if(s===0&&!window._bgEndedHandling){" +
                        "      window._bgEndedHandling=true;" +
                        "      if(typeof isRepeat!=='undefined'&&isRepeat){" +
                        "        ytPlayer.seekTo(0);ytPlayer.playVideo();" +
                        "        setTimeout(function(){window._bgEndedHandling=false;},3000);" +
                        "      } else if(typeof playNextSimilarSong==='function'){" +
                        "        playNextSimilarSong();" +
                        "        setTimeout(function(){window._bgEndedHandling=false;},5000);" +
                        "      }" +
                        "    } else if(s===1||s===3){" +
                        "      window._bgEndedHandling=false;" +
                        "    } else if(s===2&&typeof isPlaying!=='undefined'&&isPlaying){" +
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

    private void requestStoragePermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // Android 13+ pakai READ_MEDIA_AUDIO
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_MEDIA_AUDIO)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                    new String[]{ android.Manifest.permission.READ_MEDIA_AUDIO }, 200);
            }
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                    new String[]{
                        android.Manifest.permission.WRITE_EXTERNAL_STORAGE,
                        android.Manifest.permission.READ_EXTERNAL_STORAGE
                    }, 200);
            }
        }
    }

    private long lastBackPressTime = 0;
    private static final String[] DOUBLE_BACK_VIEWS = {"view-home", "view-search", "view-library"};

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            webView.evaluateJavascript(
                "(function(){ " +
                "  var active = document.querySelector('.view-section.active');" +
                "  return active ? active.id : 'view-home';" +
                "})()",
                result -> {
                    if (result == null) result = "\"view-home\"";
                    final String viewId = result.replace("\"", "").trim();
                    boolean isDoubleBackView = false;
                    for (String v : DOUBLE_BACK_VIEWS) {
                        if (v.equals(viewId)) { isDoubleBackView = true; break; }
                    }
                    if (isDoubleBackView) {
                        long now = System.currentTimeMillis();
                        if (now - lastBackPressTime < 2000) {
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
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (keepAliveHandler != null) keepAliveHandler.removeCallbacks(keepAliveRunnable);
        if (webViewWakeLock != null && webViewWakeLock.isHeld()) webViewWakeLock.release();
        if (downloadReceiver != null) { try { unregisterReceiver(downloadReceiver); } catch (Exception ignored) {} }
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
