package com.duckcorp.nestguard;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class PromoActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_promo);

        final EditText promoInput = findViewById(R.id.promoInput);
        Button promoButton = findViewById(R.id.promoButton);

        promoButton.setOnClickListener(v -> {
            String enteredCode = promoInput.getText().toString();

            if (enteredCode.equals("DUCK-STAFF-7394")) {
                startActivity(new Intent(this, FlagActivity.class));
            } else {
                Toast.makeText(this, "Wrong discount code", Toast.LENGTH_SHORT).show();
            }
        });
    }
}