package com.example.setasia

import android.annotation.SuppressLint
import android.content.Context
import android.location.Address
import android.location.Geocoder
import android.location.Location
import android.os.Build
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.tasks.await
import java.util.Locale

class LocationHelper(private val context: Context) {
    private val fusedLocationClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)
    private val geocoder = Geocoder(context, Locale.getDefault())

    private var lastLat: Double? = null
    private var lastLon: Double? = null

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocationString(): String {
        return try {
            val location: Location? = fusedLocationClient.lastLocation.await()
            if (location != null) {
                lastLat = location.latitude
                lastLon = location.longitude
                getAddressFromLocation(location)
            } else {
                "Ubicación desconocida (sin señal GPS reciente)"
            }
        } catch (e: Exception) {
            "Error al obtener ubicación: ${e.message}"
        }
    }
    
    fun getLastLatLon(): Pair<Double?, Double?> {
        return Pair(lastLat, lastLon)
    }

    @Suppress("DEPRECATION")
    private fun getAddressFromLocation(location: Location): String {
        return try {
            val addresses: List<Address>? = geocoder.getFromLocation(location.latitude, location.longitude, 1)
            if (!addresses.isNullOrEmpty()) {
                val address = addresses[0]
                // Ej: "San Lorenzo de El Escorial, Comunidad de Madrid"
                val locality = address.locality ?: address.subAdminArea ?: ""
                val adminArea = address.adminArea ?: ""
                if (locality.isNotEmpty() && adminArea.isNotEmpty()) {
                    "$locality, $adminArea"
                } else if (locality.isNotEmpty()) {
                    locality
                } else {
                    "Lat: ${location.latitude}, Lon: ${location.longitude}"
                }
            } else {
                "Lat: ${location.latitude}, Lon: ${location.longitude}"
            }
        } catch (e: Exception) {
            "Lat: ${location.latitude}, Lon: ${location.longitude}"
        }
    }
}
