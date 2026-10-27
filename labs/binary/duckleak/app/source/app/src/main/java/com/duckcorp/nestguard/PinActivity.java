package com.duckcorp.nestguard;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class PinActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_pin);

        final EditText pinInput = findViewById(R.id.pinInput);
        Button unlockButton = findViewById(R.id.unlockButton);

        unlockButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String enteredPin = pinInput.getText().toString();

                if (enteredPin.equals(getString(R.string.vault_pin))) {
                    Intent intent = new Intent(PinActivity.this, SecretFolderActivity.class);
                    startActivity(intent);
                } else {
                    Toast.makeText(PinActivity.this, getString(R.string.pin_wrong), Toast.LENGTH_SHORT).show();
                }
            }
        });
    }
}