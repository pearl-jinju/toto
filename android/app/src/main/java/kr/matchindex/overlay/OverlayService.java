package kr.matchindex.overlay;

import android.app.AppOpsManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.display.DisplayManager;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.WindowMetrics;
import android.webkit.SafeBrowsingResponse;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class OverlayService extends Service {
    private static final String ORIGIN_HOST = "matchindex-proto.onrender.com";
    private static final String ENTRY_URL = "https://" + ORIGIN_HOST + "/?view=overlay";
    private static final String CLOSE = "kr.matchindex.overlay.CLOSE";
    private static final String CHANNEL = "match-analysis-window";
    private static final int NOTIFICATION = 12;

    private enum OverlaySize {
        SMALL(268, 210, R.string.overlay_size_small),
        MEDIUM(314, 414, R.string.overlay_size_medium),
        LARGE(374, 540, R.string.overlay_size_large);

        final int widthDp;
        final int heightDp;
        final int announcement;

        OverlaySize(int widthDp, int heightDp, int announcement) {
            this.widthDp = widthDp;
            this.heightDp = heightDp;
            this.announcement = announcement;
        }
    }

    private static final OverlaySize[] SIZES = OverlaySize.values();

    private Context windowContext;
    private WindowManager windows;
    private WindowManager.LayoutParams placement;
    private LinearLayout panel;
    private FrameLayout body;
    private WebView browser;
    private LinearLayout recovery;
    private Button shrink;
    private Button grow;
    private OverlaySize size = OverlaySize.MEDIUM;
    private boolean attached;
    private AppOpsManager permissions;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AppOpsManager.OnOpChangedListener permissionChanged = (op, packageName) -> main.post(() -> {
        if (!Settings.canDrawOverlays(this)) stopSelf();
    });

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && CLOSE.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, R.string.overlay_error, Toast.LENGTH_LONG).show();
            stopSelf();
            return START_NOT_STICKY;
        }
        if (attached) return START_NOT_STICKY;

        try {
            enterForeground();
            createPanel();
            permissions = getSystemService(AppOpsManager.class);
            permissions.startWatchingMode(AppOpsManager.OPSTR_SYSTEM_ALERT_WINDOW, getPackageName(), permissionChanged);
        } catch (WindowManager.BadTokenException | IllegalStateException | SecurityException error) {
            Toast.makeText(this, R.string.overlay_error, Toast.LENGTH_LONG).show();
            stopSelf();
        }
        return START_NOT_STICKY;
    }

    private void enterForeground() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL,
                getString(R.string.notification_channel), NotificationManager.IMPORTANCE_LOW));

        PendingIntent showApp = PendingIntent.getActivity(this, 0,
                new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        PendingIntent close = PendingIntent.getService(this, 1,
                new Intent(this, OverlayService.class).setAction(CLOSE), PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.ic_overlay)
                .setContentTitle(getString(R.string.app_name))
                .setContentText(getString(R.string.notification_text))
                .setContentIntent(showApp)
                .setOngoing(true)
                .addAction(new Notification.Action.Builder(null, getString(R.string.close_overlay), close).build())
                .build();
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIFICATION, notification);
        }
    }

    private void createPanel() {
        int type = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        windowContext = this;
        if (Build.VERSION.SDK_INT >= 30) {
            DisplayManager displays = getSystemService(DisplayManager.class);
            Display display = displays.getDisplay(Display.DEFAULT_DISPLAY);
            if (display == null) throw new IllegalStateException("No primary display");
            windowContext = createDisplayContext(display).createWindowContext(type, null);
        }
        windows = windowContext.getSystemService(WindowManager.class);
        panel = new LinearLayout(windowContext);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackground(panelBackground());
        panel.setClipToOutline(true);

        LinearLayout toolbar = new LinearLayout(windowContext);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setBackgroundColor(0xFF142636);
        TextView handle = new TextView(windowContext);
        handle.setText(R.string.drag_overlay);
        handle.setGravity(Gravity.CENTER_VERTICAL);
        handle.setTextColor(0xFFD7EDFF);
        handle.setTextSize(13);
        handle.setTypeface(Typeface.DEFAULT_BOLD);
        handle.setPadding(dp(windowContext, 12), 0, dp(windowContext, 4), 0);
        handle.setMaxLines(2);
        handle.setOnTouchListener(new DragHandle());
        toolbar.addView(handle, new LinearLayout.LayoutParams(0, -1, 1f));

        shrink = toolbarControl("−", R.string.minimize_overlay);
        shrink.setOnClickListener(view -> stepSize(-1));
        toolbar.addView(shrink, new LinearLayout.LayoutParams(dp(windowContext, 48), -1));

        grow = toolbarControl("+", R.string.expand_overlay);
        grow.setOnClickListener(view -> stepSize(1));
        toolbar.addView(grow, new LinearLayout.LayoutParams(dp(windowContext, 48), -1));
        updateSizeButtons();

        Button close = toolbarControl("×", R.string.close_overlay);
        close.setOnClickListener(view -> stopSelf());
        toolbar.addView(close, new LinearLayout.LayoutParams(dp(windowContext, 48), -1));
        panel.addView(toolbar, new LinearLayout.LayoutParams(-1, dp(windowContext, 48)));

        body = new FrameLayout(windowContext);
        panel.addView(body, new LinearLayout.LayoutParams(-1, 0, 1f));
        browser = createWebView();
        body.addView(browser, new FrameLayout.LayoutParams(-1, -1));
        recovery = recoveryPanel();
        body.addView(recovery, new FrameLayout.LayoutParams(-1, -1));

        placement = new WindowManager.LayoutParams(0, 0, type, windowFlags(),
                PixelFormat.TRANSLUCENT);
        placement.gravity = Gravity.TOP | Gravity.LEFT;
        placement.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE;
        if (Build.VERSION.SDK_INT >= 30) placement.setFitInsetsTypes(WindowInsets.Type.ime());
        Rect bounds = safeBounds();
        resizeToFit(bounds);
        placement.x = bounds.right - placement.width - dp(windowContext, 8);
        placement.y = bounds.top + dp(windowContext, 16);
        clamp(bounds);
        windows.addView(panel, placement);
        attached = true;
        browser.loadUrl(ENTRY_URL);
    }

    private GradientDrawable panelBackground() {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(0xFF0C1520);
        shape.setStroke(dp(windowContext, 1), 0xFF38556A);
        shape.setCornerRadius(dp(windowContext, 14));
        return shape;
    }

    private Button toolbarControl(String label, int description) {
        Button button = new Button(windowContext);
        button.setText(label);
        button.setTextSize(24);
        button.setTextColor(Color.WHITE);
        button.setContentDescription(getString(description));
        button.setTooltipText(getString(description));
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setPadding(0, 0, 0, 0);
        button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF223B4D));
        return button;
    }

    private WebView createWebView() {
        WebView web = new WebView(windowContext);
        web.setBackgroundColor(0xFF0C1520);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                boolean blocked = !allowed(request.getUrl());
                if (blocked && request.isForMainFrame()) {
                    Toast.makeText(OverlayService.this, R.string.source_outside, Toast.LENGTH_SHORT).show();
                }
                return blocked;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                if (!allowed(Uri.parse(url))) {
                    view.stopLoading();
                    showError();
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) showError();
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse error) {
                if (request.isForMainFrame()) showError();
            }

            @Override
            public void onSafeBrowsingHit(WebView view, WebResourceRequest request, int threatType,
                                          SafeBrowsingResponse callback) {
                callback.backToSafety(true);
                if (request.isForMainFrame()) showError();
            }
        });
        return web;
    }

    private static boolean allowed(Uri url) {
        return "https".equals(url.getScheme())
                && ORIGIN_HOST.equals(url.getHost())
                && url.getUserInfo() == null
                && (url.getPort() == -1 || url.getPort() == 443);
    }

    private LinearLayout recoveryPanel() {
        LinearLayout content = new LinearLayout(windowContext);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER);
        int padding = dp(windowContext, 16);
        content.setPadding(padding, padding, padding, padding);
        content.setBackgroundColor(0xFF0C1520);
        TextView message = new TextView(windowContext);
        message.setText(R.string.load_error);
        message.setTextColor(0xFFD7EDFF);
        message.setGravity(Gravity.CENTER);
        content.addView(message);
        Button retry = new Button(windowContext);
        retry.setText(R.string.reload);
        retry.setOnClickListener(view -> {
            content.setVisibility(View.GONE);
            browser.setVisibility(View.VISIBLE);
            browser.loadUrl(ENTRY_URL);
        });
        content.addView(retry);
        content.setVisibility(View.GONE);
        return content;
    }

    private void showError() {
        if (browser == null || recovery == null) return;
        browser.setVisibility(View.GONE);
        recovery.setVisibility(View.VISIBLE);
    }

    private int windowFlags() {
        return WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                | (size == OverlaySize.SMALL ? WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE : 0);
    }

    private void stepSize(int direction) {
        int next = size.ordinal() + direction;
        if (!attached || next < 0 || next >= SIZES.length) return;
        size = SIZES[next];
        updateSizeButtons();
        if (size == OverlaySize.SMALL) browser.clearFocus();
        updateSizeAndPosition();
        panel.announceForAccessibility(getString(size.announcement));
    }

    private void updateSizeButtons() {
        boolean smaller = size != OverlaySize.SMALL;
        boolean larger = size != OverlaySize.LARGE;
        shrink.setEnabled(smaller);
        grow.setEnabled(larger);
        shrink.setAlpha(smaller ? 1f : 0.45f);
        grow.setAlpha(larger ? 1f : 0.45f);
    }

    private Rect safeBounds() {
        if (Build.VERSION.SDK_INT >= 30) {
            WindowMetrics metrics = windows.getMaximumWindowMetrics();
            Rect bounds = new Rect(metrics.getBounds());
            Insets insets = metrics.getWindowInsets().getInsetsIgnoringVisibility(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            bounds.left += insets.left;
            bounds.top += insets.top;
            bounds.right -= insets.right;
            bounds.bottom -= insets.bottom;
            return bounds;
        }
        DisplayMetrics metrics = new DisplayMetrics();
        windows.getDefaultDisplay().getMetrics(metrics);
        return new Rect(0, dp(windowContext, 24), metrics.widthPixels, metrics.heightPixels);
    }

    private void resizeToFit(Rect bounds) {
        int gap = dp(windowContext, 16);
        placement.width = Math.min(dp(windowContext, size.widthDp), Math.max(1, bounds.width() - gap));
        placement.height = Math.min(dp(windowContext, size.heightDp), Math.max(1, bounds.height() - gap));
        placement.flags = windowFlags();
    }

    private void clamp(Rect bounds) {
        placement.x = Math.max(bounds.left, Math.min(placement.x, bounds.right - placement.width));
        placement.y = Math.max(bounds.top, Math.min(placement.y, bounds.bottom - placement.height));
    }

    private void updateSizeAndPosition() {
        Rect bounds = safeBounds();
        resizeToFit(bounds);
        clamp(bounds);
        updateWindow();
    }

    private void updateWindow() {
        if (!attached) return;
        try {
            windows.updateViewLayout(panel, placement);
        } catch (IllegalArgumentException | SecurityException error) {
            stopSelf();
        }
    }

    @Override
    public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        if (attached) updateSizeAndPosition();
    }

    private final class DragHandle implements View.OnTouchListener {
        private int startX;
        private int startY;
        private float touchX;
        private float touchY;
        private boolean dragging;

        @Override
        public boolean onTouch(View target, MotionEvent event) {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    startX = placement.x;
                    startY = placement.y;
                    touchX = event.getRawX();
                    touchY = event.getRawY();
                    dragging = false;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    int movedX = Math.round(event.getRawX() - touchX);
                    int movedY = Math.round(event.getRawY() - touchY);
                    int slop = ViewConfiguration.get(windowContext).getScaledTouchSlop();
                    dragging |= Math.abs(movedX) >= slop || Math.abs(movedY) >= slop;
                    if (dragging) {
                        placement.x = startX + movedX;
                        placement.y = startY + movedY;
                        clamp(safeBounds());
                        updateWindow();
                    }
                    return true;
                case MotionEvent.ACTION_UP:
                    if (!dragging) target.performClick();
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    return true;
                default:
                    return false;
            }
        }
    }

    static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    @Override
    public void onDestroy() {
        if (permissions != null) permissions.stopWatchingMode(permissionChanged);
        main.removeCallbacksAndMessages(null);
        if (attached && panel.isAttachedToWindow()) {
            try {
                windows.removeViewImmediate(panel);
            } catch (IllegalArgumentException ignored) {
                // The system may have removed the overlay after revoking access.
            }
        }
        attached = false;
        if (browser != null) {
            body.removeView(browser);
            browser.stopLoading();
            browser.destroy();
        }
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }
}
