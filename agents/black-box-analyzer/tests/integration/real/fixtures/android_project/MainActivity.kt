package com.example.demo

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        binding.saveButton.setOnClickListener { save() }
    }

    override fun onStart() {
        super.onStart()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    fun onButtonClick(view: View) {
        refresh()
    }

    private fun refresh() {
    }

    private fun save() {
    }
}
