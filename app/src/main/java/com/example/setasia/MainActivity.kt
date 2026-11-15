package com.example.setasia

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import android.content.Context
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.core.content.FileProvider
import java.io.File
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.setasia.ui.theme.SetasIATheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SetasIATheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MushroomApp()
                }
            }
        }
    }
}

@Composable
fun MushroomApp(viewModel: MushroomViewModel = viewModel()) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val locationHelper = remember { LocationHelper(context) }

    var hasLocationPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        hasLocationPermission = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
    }

    LaunchedEffect(Unit) {
        if (!hasLocationPermission) {
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    LaunchedEffect(hasLocationPermission) {
        if (hasLocationPermission) {
            coroutineScope.launch {
                val locationStr = locationHelper.getCurrentLocationString()
                val latlon = locationHelper.getLastLatLon()
                viewModel.setLocation(locationStr, latlon.first, latlon.second)
            }
        }
    }

    ChatScreen(viewModel = viewModel)
}

fun createImageUri(context: Context): Uri {
    val file = File(context.cacheDir, "camera_image_${System.currentTimeMillis()}.jpg")
    return FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
}

@Composable
fun ChatScreen(viewModel: MushroomViewModel) {
    val chatHistory by viewModel.chatHistory.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val currentLocation by viewModel.currentLocation.collectAsState()
    val useLocation by viewModel.useLocation.collectAsState()

    var inputText by remember { mutableStateOf("") }
    val context = LocalContext.current
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    
    // Lanzador para la cámara de fotos
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success && imageUri != null) {
            try {
                // Decodificar la imagen guardada
                val bitmap = if (Build.VERSION.SDK_INT >= 28) {
                    val source = ImageDecoder.createSource(context.contentResolver, imageUri!!)
                    ImageDecoder.decodeBitmap(source)
                } else {
                    @Suppress("DEPRECATION")
                    MediaStore.Images.Media.getBitmap(context.contentResolver, imageUri)
                }
                // Enviar foto al modelo
                viewModel.sendImageMessage(inputText, bitmap)
                inputText = ""
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    // Cargamos la imagen de fondo
    val backgroundImage = androidx.compose.ui.res.painterResource(id = R.drawable.fondo)

    Box(modifier = Modifier.fillMaxSize()) {
        // La imagen de fondo ocupando toda la pantalla
        androidx.compose.foundation.Image(
            painter = backgroundImage,
            contentDescription = "Fondo de setas",
            contentScale = androidx.compose.ui.layout.ContentScale.Crop, // Para que llene la pantalla sin deformarse
            modifier = Modifier.fillMaxSize()
        )

        // Un pequeño velo oscuro (opcional) para que el texto y los bocadillos se lean mejor sobre la foto
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.3f))
        )

        // El contenido original del chat
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
                .windowInsetsPadding(WindowInsets.ime) // ¡Esto empuja el contenido hacia arriba cuando sale el teclado!
        ) {
            Spacer(modifier = Modifier.height(16.dp)) // Bajamos un poco la ubicación

            // Location Header con interruptor
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📍 Ubicación: ${currentLocation ?: "Buscando..."}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier.weight(1f)
                )
                Switch(
                    checked = useLocation,
                    onCheckedChange = { viewModel.toggleUseLocation(it) },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = MaterialTheme.colorScheme.primary,
                        uncheckedThumbColor = Color.Gray
                    )
                )
            }

            HorizontalDivider(color = Color.White.copy(alpha = 0.5f))

            // Chat list
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentPadding = PaddingValues(vertical = 12.dp),
                reverseLayout = false
            ) {
                // Filter out system prompt from UI
                val visibleMessages = chatHistory.filter { it.role != "system" }

                items(visibleMessages) { msg ->
                    ChatBubble(message = msg)
                    Spacer(modifier = Modifier.height(12.dp))
                }
                if (isLoading) {
                    item {
                        CircularProgressIndicator(modifier = Modifier.padding(16.dp).align(Alignment.CenterHorizontally))
                    }
                }
            }

            // Input area
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp, bottom = 32.dp), // Subimos el cajón de texto aprox 1 cm extra
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Botón de Cámara
                IconButton(
                    onClick = {
                        val uri = createImageUri(context)
                        imageUri = uri
                        cameraLauncher.launch(uri)
                    },
                    modifier = Modifier
                        .padding(end = 8.dp)
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.8f), RoundedCornerShape(50))
                ) {
                    Text("📸", fontSize = 20.sp)
                }
                
                OutlinedTextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("¿Qué tipo de setas hay por aquí?") },
                    shape = RoundedCornerShape(24.dp), // Bordes más redondeados y modernos
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                        unfocusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f)
                    )
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    onClick = {
                        viewModel.sendMessage(inputText)
                        inputText = ""
                    },
                    enabled = inputText.isNotBlank() && !isLoading,
                    shape = RoundedCornerShape(24.dp), // Botón redondeado a juego
                    modifier = Modifier.height(56.dp) // Misma altura que el TextField
                ) {
                    Text("Enviar")
                }
            }
        }
    }
}

@Composable
fun ChatBubble(message: UIMessage) {
    val isUser = message.role == "user"
    val bubbleColor = if (isUser) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.secondaryContainer
    val bubbleTextColor = if (isUser) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSecondaryContainer
    val alignment = if (isUser) Alignment.End else Alignment.Start

    Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = alignment) {
        Box(
            modifier = Modifier
                .background(bubbleColor, RoundedCornerShape(12.dp))
                .padding(12.dp)
                .fillMaxWidth(0.85f)
        ) {
            // Container para que el usuario pueda hacer long-press y copiar texto
            SelectionContainer {
                Column {
                    if (message.hasImage) {
                        Text(
                            text = "📷 [Imagen adjunta]",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                    }
                    Text(
                        text = message.content,
                        fontSize = 16.sp,
                        color = bubbleTextColor
                    )
                    
                    if (message.safety != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "⚠️ ${message.safety}",
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    if (!message.sources.isNullOrEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Fuentes:", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = bubbleTextColor)
                        message.sources.forEach { source ->
                            var sourceText = "- ${source.title}"
                            if (!source.species.isNullOrEmpty()) sourceText += " (Especies: ${source.species.joinToString(", ")})"
                            if (!source.zones.isNullOrEmpty()) sourceText += " (Zonas: ${source.zones.joinToString(", ")})"
                            Text(sourceText, fontSize = 12.sp, color = bubbleTextColor)
                        }
                    }

                    if (message.geography?.candidateSpecies != null && message.geography.candidateSpecies.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Registros históricos cercanos:", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = bubbleTextColor)
                        message.geography.candidateSpecies.forEach { candidate ->
                            Text("- ${candidate.species} (${candidate.sampleRecords} registros)", fontSize = 12.sp, color = bubbleTextColor)
                        }
                    }
                }
            }
        }
    }
}
