package com.example.setasia

data class UIMessage(
    val role: String, // "user", "assistant"
    val content: String,
    val hasImage: Boolean = false,
    val sources: List<Source>? = null,
    val geography: Geography? = null,
    val safety: String? = null
)
