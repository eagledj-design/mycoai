package com.example.setasia

import com.example.setasia.BuildConfig
import com.google.gson.annotations.SerializedName
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit
import okhttp3.Interceptor

data class ConsultRequest(
    val question: String,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerializedName("radius_km") val radiusKm: Int? = null,
    val month: Int? = null,
    val species: List<String>? = null,
    val images: List<String>? = null,
    val provider: String? = null,
    val model: String? = null,
    @SerializedName("vision_model") val visionModel: String? = null
)

data class ConsultResponse(
    val answer: String,
    val sources: List<Source>? = null,
    val geography: Geography? = null,
    val safety: String? = null
)

data class Source(
    val title: String,
    val url: String,
    val excerpt: String,
    val locator: String? = null,
    val species: List<String>? = null,
    val zones: List<String>? = null
)

data class Geography(
    @SerializedName("candidate_species")
    val candidateSpecies: List<CandidateSpecies>? = null
)

data class CandidateSpecies(
    val species: String,
    @SerializedName("sample_records")
    val sampleRecords: Int,
    val example: String? = null
)

interface MycoAiApi {
    @GET("health")
    suspend fun checkHealth(): retrofit2.Response<Void>

    @POST("consult")
    suspend fun consult(
        @Body request: ConsultRequest,
        @Header("X-MycoAI-Provider-Key") providerKey: String? = null
    ): ConsultResponse

    @GET("models")
    suspend fun listModels(
        @Query("provider") provider: String,
        @Header("X-MycoAI-Provider-Key") providerKey: String? = null
    ): ListModelsResponse
}

data class ListModelsResponse(
    val provider: String,
    val models: List<String>
)

object RetrofitClient {
    private val TOKEN = BuildConfig.BACKEND_TOKEN

    private var currentBaseUrl: String? = null
    private var currentInstance: MycoAiApi? = null

    fun getInstance(baseUrl: String): MycoAiApi {
        // Aseguramos que la URL termina en barra "/"
        val safeUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        if (currentInstance == null || currentBaseUrl != safeUrl) {
            currentBaseUrl = safeUrl

            val authInterceptor = Interceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("Authorization", "Bearer $TOKEN")
                    .addHeader("Content-Type", "application/json")
                    .build()
                chain.proceed(request)
            }

            val okHttpClient = OkHttpClient.Builder()
                .readTimeout(180, TimeUnit.SECONDS)
                .connectTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(authInterceptor)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(safeUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            currentInstance = retrofit.create(MycoAiApi::class.java)
        }
        return currentInstance!!
    }
}
