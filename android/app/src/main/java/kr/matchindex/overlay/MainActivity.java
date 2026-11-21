package kr.matchindex.overlay;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final String START_URI = "matchindex://overlay/start";
    private static final String START_AFTER_SETTINGS = "start_after_settings";
    private static final String START_WHEN_FOCUSED = "start_when_focused";
    private static final String RETURN_TO_CALLER = "return_to_caller";

    private TextView status;
    private AlertDialog permissionPrompt;
    private boolean startAfterSettings;
    private boolean startWhenFocused;
    private boolean returnToCaller;
    private boolean resumed;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        if (state == null) {
            queueBrowserLaunch(getIntent());
        } else {
            startAfterSettings = state.getBoolean(START_AFTER_SETTINGS);
            startWhenFocused = state.getBoolean(START_WHEN_FOCUSED);
            returnToCaller = state.getBoolean(RETURN_TO_CALLER);
        }

        int padding = OverlayService.dp(this, 24);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(0xFF0C1520);

        LinearLayout content = new LinearLayout(this);
        content.setGravity(Gravity.CENTER_VERTICAL);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(padding, padding, padding, padding);
        scroll.addView(content);
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets safe = insets.getInsets(WindowInsets.Type.systemBars());
                content.setPadding(padding + safe.left, padding + safe.top,
                        padding + safe.right, padding + safe.bottom);
            }
            return insets;
        });

        TextView title = label(R.string.title, 28, Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        content.addView(title);
        append(content, label(R.string.description, 16, 0xFFB6C8D9), 16);

        status = label(R.string.permission_needed, 15, 0xFF77E5B0);
        append(content, status, 24);

        Button startButton = new Button(this);
        startButton.setText(R.string.start_overlay);
        startButton.setAllCaps(false);
        startButton.setOnClickListener(view -> requestOverlay());
        append(content, startButton, 8);

        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        resumed = true;
        boolean allowed = Settings.canDrawOverlays(this);
        status.setText(allowed ? R.string.permission_granted : R.string.permission_needed);
        boolean requested = startAfterSettings;
        startAfterSettings = false;
        if (requested && allowed) startWhenFocused = true;
        launchWhenReady();
    }

    @Override
    protected void onPause() {
        resumed = false;
        super.onPause();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        queueBrowserLaunch(intent);
        launchWhenReady();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) launchWhenReady();
    }

    private void queueBrowserLaunch(Intent intent) {
        if (intent == null || !Intent.ACTION_VIEW.equals(intent.getAction())
                || !START_URI.equals(intent.getDataString())) return;
        startWhenFocused = true;
        returnToCaller = true;
    }

    private void launchWhenReady() {
        if (!startWhenFocused || !resumed || !hasWindowFocus() || isFinishing()) return;
        startWhenFocused = false;
        requestOverlay();
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putBoolean(START_AFTER_SETTINGS, startAfterSettings);
        state.putBoolean(START_WHEN_FOCUSED, startWhenFocused);
        state.putBoolean(RETURN_TO_CALLER, returnToCaller);
    }

    private void requestOverlay() {
        if (Settings.canDrawOverlays(this)) {
            startOverlay();
            return;
        }

        if (permissionPrompt != null && permissionPrompt.isShowing()) return;
        permissionPrompt = new AlertDialog.Builder(this)
                .setTitle(R.string.permission_title)
                .setMessage(R.string.permission_explanation)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.open_settings, (dialog, which) -> openOverlaySettings())
                .show();
    }

    private TextView label(int text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setLineSpacing(OverlayService.dp(this, 2), 1f);
        return view;
    }

    private void append(LinearLayout container, View view, int gap) {
        LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        layout.topMargin = OverlayService.dp(this, gap);
        container.addView(view, layout);
    }

    private void openOverlaySettings() {
        if (startAfterSettings) return;

        Intent settings = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION);
        if (Build.VERSION.SDK_INT < 30) {
            settings.setData(Uri.fromParts("package", getPackageName(), null));
        }
        startAfterSettings = true;
        try {
            startActivity(settings);
        } catch (ActivityNotFoundException | SecurityException error) {
            startAfterSettings = false;
            Toast.makeText(this, R.string.settings_error, Toast.LENGTH_LONG).show();
        }
    }

    private void startOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            status.setText(R.string.permission_needed);
            return;
        }
        try {
            startForegroundService(new Intent(this, OverlayService.class));
            if (returnToCaller) {
                finish();
            } else {
                moveTaskToBack(true);
            }
        } catch (IllegalStateException | SecurityException error) {
            Toast.makeText(this, R.string.overlay_error, Toast.LENGTH_LONG).show();
        }
    }
}
