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
    val currentScreen by viewModel.currentScreen.collectAsState()

    if (currentScreen == AppScreen.CONFIG) {
        ConfigScreen(viewModel)
        return
    }

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
    val searchRadius by viewModel.searchRadius.collectAsState()

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
            
            // Selector de Radio de Búsqueda
            if (useLocation) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Radio (línea recta):",
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(2, 5, 10, 20).forEach { km ->
                            val isSelected = searchRadius == km
                            Surface(
                                color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                                shape = RoundedCornerShape(16.dp),
                                onClick = { viewModel.setSearchRadius(km) }
                            ) {
                                Text(
                                    text = "${km}km",
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                    color = if (isSelected) MaterialTheme.colorScheme.onPrimary else Color.White,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                }
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
                        fontSize = 16.sp
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
                        Text("Fuentes:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        message.sources.forEach { source ->
                            var sourceText = "- ${source.title}"
                            if (!source.species.isNullOrEmpty()) sourceText += " (Especies: ${source.species.joinToString(", ")})"
                            if (!source.zones.isNullOrEmpty()) sourceText += " (Zonas: ${source.zones.joinToString(", ")})"
                            Text(sourceText, fontSize = 12.sp, color = Color.Gray)
                        }
                    }

                    if (message.geography?.candidateSpecies != null && message.geography.candidateSpecies.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Registros históricos cercanos:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        message.geography.candidateSpecies.forEach { candidate ->
                            Text("- ${candidate.species} (${candidate.sampleRecords} registros)", fontSize = 12.sp, color = Color.DarkGray)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ConfigScreen(viewModel: MushroomViewModel) {
    var backendUrl by remember { mutableStateOf(BuildConfig.BACKEND_URL) }
    
    var isPrivate by remember { mutableStateOf(true) }
    
    val privateProviders = listOf("lm_studio", "ollama")
    val cloudProviders = listOf("openai", "cloud_compatible")

    var selectedProvider by remember { mutableStateOf(privateProviders[0]) }
    var apiKey by remember { mutableStateOf("") }
    var selectedModel by remember { mutableStateOf("") }
    
    var useVisionModel by remember { mutableStateOf(false) }
    var selectedVisionModel by remember { mutableStateOf("") }

    val availableModels by viewModel.availableModels.collectAsState()
    val isFetching by viewModel.isFetchingModels.collectAsState()

    // Reset when toggling between private/cloud
    LaunchedEffect(isPrivate) {
        selectedProvider = if (isPrivate) privateProviders[0] else cloudProviders[0]
        selectedModel = ""
        selectedVisionModel = ""
    }

    val backgroundImage = androidx.compose.ui.res.painterResource(id = R.drawable.fondo)
    
    Box(modifier = Modifier.fillMaxSize()) {
        androidx.compose.foundation.Image(
            painter = backgroundImage,
            contentDescription = "Fondo",
            contentScale = androidx.compose.ui.layout.ContentScale.Crop,
            modifier = Modifier.fillMaxSize()
        )
        Box(modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.5f)))

        Column(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(32.dp))
            Text("Configuración MycoAI", style = MaterialTheme.typography.headlineMedium, color = Color.White)
            Spacer(modifier = Modifier.height(16.dp))

            // Selector dinámico de URL del Servidor MycoAI
            OutlinedTextField(
                value = backendUrl, 
                onValueChange = { backendUrl = it }, 
                label = { Text("URL del Servidor MycoAI") }, 
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                    unfocusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f)
                )
            )
            Spacer(modifier = Modifier.height(16.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                Button(
                    onClick = { isPrivate = true },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isPrivate) MaterialTheme.colorScheme.primary else Color.Gray.copy(alpha = 0.5f)
                    )
                ) { Text("IA Privada") }
                
                Button(
                    onClick = { isPrivate = false },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (!isPrivate) MaterialTheme.colorScheme.primary else Color.Gray.copy(alpha = 0.5f)
                    )
                ) { Text("IA en Nube") }
            }
            Spacer(modifier = Modifier.height(24.dp))

            // Selector de proveedor
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceEvenly) {
                val currentList = if (isPrivate) privateProviders else cloudProviders
                currentList.forEach { prov ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = selectedProvider == prov, onClick = { selectedProvider = prov })
                        Text(prov, color = Color.White)
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (isPrivate) {
                Text(
                    "Nota: La IP y el puerto del servidor de modelos se configuran en el backend de MycoAI.",
                    color = Color.Yellow,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(bottom = 16.dp)
                )
            } else {
                OutlinedTextField(
                    value = apiKey, 
                    onValueChange = { apiKey = it }, 
                    label = { Text("API Key") }, 
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                        unfocusedContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f)
                    )
                )
                Spacer(modifier = Modifier.height(16.dp))
            }
            
            Button(
                onClick = { viewModel.fetchModels(backendUrl, selectedProvider, if (!isPrivate) apiKey else null) },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isFetching
            ) {
                Text(if (isFetching) "Cargando..." else "Buscar Modelos")
            }
            
            if (availableModels.isNotEmpty()) {
                Spacer(modifier = Modifier.height(16.dp))
                
                Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = useVisionModel, 
                        onCheckedChange = { useVisionModel = it },
                        colors = CheckboxDefaults.colors(checkedColor = MaterialTheme.colorScheme.primary, uncheckedColor = Color.White)
                    )
                    Text("Usar un modelo distinto para fotos", color = Color.White, fontSize = 14.sp)
                }

                Row(modifier = Modifier.fillMaxWidth().weight(1f)) {
                    // Columna 1: Modelo principal
                    Column(modifier = Modifier.weight(1f).padding(end = 4.dp)) {
                        Text("Modelo Chat:", color = Color.White, fontSize = 12.sp)
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.Black.copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                                .padding(4.dp)
                        ) {
                            items(availableModels) { model ->
                                val isSelected = selectedModel == model
                                Surface(
                                    color = if (isSelected) MaterialTheme.colorScheme.primary else Color.Transparent,
                                    shape = RoundedCornerShape(8.dp),
                                    onClick = { selectedModel = model },
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
                                ) {
                                    Text(text = model, color = Color.White, modifier = Modifier.padding(8.dp), fontSize = 12.sp)
                                }
                            }
                        }
                    }

                    // Columna 2: Modelo de Visión
                    if (useVisionModel) {
                        Column(modifier = Modifier.weight(1f).padding(start = 4.dp)) {
                            Text("Modelo Fotos:", color = Color.White, fontSize = 12.sp)
                            LazyColumn(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .background(Color.Black.copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                                    .padding(4.dp)
                            ) {
                                items(availableModels) { model ->
                                    val isSelected = selectedVisionModel == model
                                    Surface(
                                        color = if (isSelected) MaterialTheme.colorScheme.secondary else Color.Transparent,
                                        shape = RoundedCornerShape(8.dp),
                                        onClick = { selectedVisionModel = model },
                                        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
                                    ) {
                                        Text(text = model, color = Color.White, modifier = Modifier.padding(8.dp), fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = {
                    viewModel.startChat(
                        backendUrl = backendUrl,
                        provider = selectedProvider,
                        model = selectedModel,
                        visionModel = if (useVisionModel && selectedVisionModel.isNotBlank()) selectedVisionModel else null,
                        providerKey = if (!isPrivate && apiKey.isNotBlank()) apiKey else null
                    )
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                enabled = selectedModel.isNotBlank() && (!useVisionModel || selectedVisionModel.isNotBlank()) && (isPrivate || apiKey.isNotBlank())
            ) {
                Text("Empezar a buscar setas")
            }
            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}
