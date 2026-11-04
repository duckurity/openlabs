package com.duckcorp.nestguard;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class SecretFolderActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_secret_folder);

        Button documentsButton = findViewById(R.id.documentsButton);
        Button discountButton = findViewById(R.id.discountButton);

        documentsButton.setOnClickListener(v ->
                Toast.makeText(this, "No documents available", Toast.LENGTH_SHORT).show());

        discountButton.setOnClickListener(v ->
                startActivity(new Intent(this, PromoActivity.class)));
    }
}