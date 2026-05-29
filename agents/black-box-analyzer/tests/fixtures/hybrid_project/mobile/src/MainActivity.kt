package com.example.hybridapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        loadDataFromAPI()
    }

    private fun loadDataFromAPI() {
        // Call REST API
    }
}
