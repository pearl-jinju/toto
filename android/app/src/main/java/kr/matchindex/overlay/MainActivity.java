package kr.matchindex.overlay;

import android.app.Activity;
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
    private TextView status;
    private Button permissionButton;
    private Button startButton;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);

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

        permissionButton = new Button(this);
        permissionButton.setText(R.string.settings);
        permissionButton.setAllCaps(false);
        permissionButton.setOnClickListener(view -> openOverlaySettings());
        append(content, permissionButton, 10);

        startButton = new Button(this);
        startButton.setText(R.string.start_overlay);
        startButton.setAllCaps(false);
        startButton.setOnClickListener(view -> startOverlay());
        append(content, startButton, 8);

        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        boolean allowed = Settings.canDrawOverlays(this);
        status.setText(allowed ? R.string.permission_granted : R.string.permission_needed);
        permissionButton.setVisibility(allowed ? View.GONE : View.VISIBLE);
        startButton.setEnabled(allowed);
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
        Intent settings = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION);
        if (Build.VERSION.SDK_INT < 30) {
            settings.setData(Uri.fromParts("package", getPackageName(), null));
        }
        try {
            startActivity(settings);
        } catch (ActivityNotFoundException error) {
            Toast.makeText(this, R.string.settings_error, Toast.LENGTH_LONG).show();
        }
    }

    private void startOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            openOverlaySettings();
            return;
        }
        try {
            startForegroundService(new Intent(this, OverlayService.class));
            moveTaskToBack(true);
        } catch (IllegalStateException | SecurityException error) {
            Toast.makeText(this, R.string.overlay_error, Toast.LENGTH_LONG).show();
        }
    }
}
