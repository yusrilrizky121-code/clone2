package com.auspoty.app;

import android.accounts.Account;
import android.accounts.AccountManager;
import android.app.Activity;
import android.content.Context;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Bridge antara WebView dan Android AccountManager.
 * Cara kerja sama seperti Metrolist — ambil akun Google yang sudah login di HP,
 * tanpa perlu Google Cloud Console / OAuth web.
 */
public class GoogleLoginBridge {

    private final Activity activity;
    private final WebView webView;

    public GoogleLoginBridge(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
    }

    /**
     * Dipanggil dari JS: window.AndroidBridge.getGoogleAccounts()
     * Return JSON array akun Google yang ada di HP
     */
    @JavascriptInterface
    public String getGoogleAccounts() {
        try {
            AccountManager am = AccountManager.get(activity);
            Account[] accounts = am.getAccountsByType("com.google");
            JSONArray arr = new JSONArray();
            for (Account acc : accounts) {
                JSONObject obj = new JSONObject();
                obj.put("name", acc.name); // ini adalah email Google
                obj.put("email", acc.name);
                // Ambil display name dari account jika tersedia
                String displayName = acc.name.split("@")[0]; // fallback: bagian sebelum @
                obj.put("displayName", displayName);
                arr.put(obj);
            }
            return arr.toString();
        } catch (Exception e) {
            return "[]";
        }
    }

    /**
     * Dipanggil dari JS: window.AndroidBridge.loginWithAccount(email)
     * Simpan akun yang dipilih user, kirim balik ke JS
     */
    @JavascriptInterface
    public void loginWithAccount(final String email) {
        try {
            AccountManager am = AccountManager.get(activity);
            Account[] accounts = am.getAccountsByType("com.google");
            String displayName = email.split("@")[0];
            for (Account acc : accounts) {
                if (acc.name.equals(email)) {
                    // Coba ambil display name yang lebih bagus
                    String fullName = am.getUserData(acc, "fullName");
                    if (fullName != null && !fullName.isEmpty()) {
                        displayName = fullName;
                    }
                    break;
                }
            }
            final String finalName = displayName;
            final String finalEmail = email;
            activity.runOnUiThread(() -> {
                String js = "javascript:(function(){" +
                    "var user = {name:'" + finalName.replace("'", "\\'") + "'," +
                    "email:'" + finalEmail.replace("'", "\\'") + "'," +
                    "picture:'',sub:'" + finalEmail.replace("'", "\\'") + "'};" +
                    "localStorage.setItem('auspotyGoogleUser', JSON.stringify(user));" +
                    "if(typeof updateProfileUI === 'function') updateProfileUI();" +
                    "if(typeof closeLoginModal === 'function') closeLoginModal();" +
                    "if(typeof showToast === 'function') showToast('Selamat datang, " + finalName.replace("'", "\\'") + "!');" +
                    "})()";
                webView.evaluateJavascript(js, null);
            });
        } catch (Exception e) {
            activity.runOnUiThread(() ->
                webView.evaluateJavascript("javascript:showToast('Login gagal')", null)
            );
        }
    }

    /**
     * Dipanggil dari JS: window.AndroidBridge.isAndroid()
     * Untuk deteksi apakah running di APK
     */
    @JavascriptInterface
    public boolean isAndroid() {
        return true;
    }
}
