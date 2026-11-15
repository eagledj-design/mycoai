package com.example.setasia

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import android.graphics.Bitmap
import android.util.Base64
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.Calendar

class MushroomViewModel : ViewModel() {

    private val _chatHistory = MutableStateFlow<List<UIMessage>>(emptyList())
    val chatHistory: StateFlow<List<UIMessage>> = _chatHistory

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _currentLocation = MutableStateFlow<String?>(null)
    val currentLocation: StateFlow<String?> = _currentLocation

    private val _useLocation = MutableStateFlow(true)
    val useLocation: StateFlow<Boolean> = _useLocation

    private var currentLat: Double? = null
    private var currentLon: Double? = null

    fun toggleUseLocation(use: Boolean) {
        _useLocation.value = use
    }

    fun setLocation(locationStr: String, lat: Double?, lon: Double?) {
        if (_currentLocation.value == locationStr) return
        _currentLocation.value = locationStr
        currentLat = lat
        currentLon = lon
    }

    // Nueva función para enviar imágenes (Multimodal)
    fun sendImageMessage(userText: String, bitmap: Bitmap) {
        // Redimensionar para no saturar la red ni la memoria del móvil
        val maxDim = 800
        val scale = maxDim.toFloat() / Math.max(bitmap.width, bitmap.height)
        val scaled = if (scale < 1f) Bitmap.createScaledBitmap(bitmap, (bitmap.width * scale).toInt(), (bitmap.height * scale).toInt(), true) else bitmap

        // Comprimir a JPEG y convertir a Base64
        val outputStream = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.JPEG, 80, outputStream)
        // Reducir la calidad si supera los 3MB? 800x800 a 80q es menos de 300KB, así que sin problema.
        val base64Image = Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP)

        val text = if (userText.isNotBlank()) userText else "¿Qué seta es esta?"
        val userMessage = UIMessage(role = "user", content = text, hasImage = true)
        _chatHistory.value = _chatHistory.value + userMessage
        
        sendRequestToLLM(text, listOf("data:image/jpeg;base64,$base64Image"))
    }

    fun sendMessage(userText: String) {
        if (userText.isBlank()) return

        val userMessage = UIMessage(role = "user", content = userText.trim())
        _chatHistory.value = _chatHistory.value + userMessage

        sendRequestToLLM(userText.trim(), null)
    }

    private fun sendRequestToLLM(question: String, images: List<String>?) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                // Verificar health (opcional, recomendado en el prompt)
                try {
                    val health = RetrofitClient.instance.checkHealth()
                    if (!health.isSuccessful) {
                        throw Exception("Backend no disponible")
                    }
                } catch (e: Exception) {
                    _chatHistory.value = _chatHistory.value + UIMessage("assistant", "Error de conexión: Backend MycoAI no accesible. Revisa Tailscale.")
                    _isLoading.value = false
                    return@launch
                }

                val request = ConsultRequest(
                    question = question,
                    latitude = if (_useLocation.value) currentLat else null,
                    longitude = if (_useLocation.value) currentLon else null,
                    images = images
                )
                val response = RetrofitClient.instance.consult(request)
                
                val aiMessage = UIMessage(
                    role = "assistant", 
                    content = response.answer,
                    sources = response.sources,
                    geography = response.geography,
                    safety = response.safety
                )
                _chatHistory.value = _chatHistory.value + aiMessage
                
            } catch (e: retrofit2.HttpException) {
                if (e.code() == 401) {
                     _chatHistory.value = _chatHistory.value + UIMessage("assistant", "Error 401: Token inválido de MycoAI.")
                } else {
                     _chatHistory.value = _chatHistory.value + UIMessage("assistant", "Error HTTP ${e.code()}: ${e.message()}")
                }
            } catch (e: Exception) {
                e.printStackTrace()
                _chatHistory.value = _chatHistory.value + UIMessage("assistant", "Error en el análisis: ${e.message}.")
            } finally {
                _isLoading.value = false
            }
        }
    }
}
