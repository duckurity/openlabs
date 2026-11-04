package com.duckcorp.nestguard;

import android.os.Bundle;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class FlagActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_flag);

        TextView flagText = findViewById(R.id.flagText);
        flagText.setText(BuildConfig.CTF_FLAG);
    }
}