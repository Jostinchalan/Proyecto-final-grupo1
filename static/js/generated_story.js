//static/js/generated_story.js
/**
 * Generated Story JavaScript - AUDIO SIMPLIFICADO + MODO OSCURO + DESCARGA
 * Un solo botón para escuchar el cuento + aplicación del modo oscuro + descarga de PDF
 */

// Variables globales
let currentUtterance = null
let isPlaying = false

/**
 * Inicialización
 */
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Inicializando cuento...")

  setupEventListeners()
  animateElements()

  // NUEVA FUNCIONALIDAD - Aplicar modo oscuro
  applyDarkModeIfActive()

  // NUEVA FUNCIONALIDAD - Configurar descarga
  setupDownloadButton()

  // Verificar TTS
  if ("speechSynthesis" in window) {
    console.log("✅ TTS disponible")
  } else {
    console.error("❌ TTS no disponible")
    mostrarMensaje("⚠️ Tu navegador no soporta síntesis de voz", "error")
  }

  setTimeout(() => {
    mostrarMensaje("✨ ¡Cuento listo para leer!", "success")
  }, 1000)
})

/**
 * NUEVA FUNCIONALIDAD - Configurar botón de descarga
 */
function setupDownloadButton() {
  console.log("📄 Configurando botón de descarga...")

  // Buscar botón de descarga por ID o clase
  const downloadBtn =
    document.getElementById("download-btn") ||
    document.querySelector(".download-btn") ||
    document.querySelector('[data-action="download"]')

  if (downloadBtn) {
    downloadBtn.addEventListener("click", function (e) {
      e.preventDefault()
      e.stopPropagation()

      const cuentoId = this.dataset.cuentoId || document.querySelector(".story-container")?.dataset.storyId

      if (!cuentoId) {
        console.error("❌ No se pudo determinar el ID del cuento")
        mostrarMensaje("❌ Error: No se pudo determinar el cuento a descargar", "error")
        return
      }

      console.log("📄 Iniciando descarga para cuento:", cuentoId)

      // Mostrar mensaje de descarga
      mostrarMensaje("📄 Preparando descarga...", "info")

      // Crear enlace temporal para forzar descarga
      const tempLink = document.createElement("a")
      tempLink.href = `/stories/cuento/${cuentoId}/descargar/`
      tempLink.download = "" // Esto fuerza la descarga
      tempLink.style.display = "none"
      tempLink.target = "_blank" // Abrir en nueva ventana como respaldo

      // Agregar al DOM, hacer clic y remover
      document.body.appendChild(tempLink)
      tempLink.click()
      document.body.removeChild(tempLink)

      // Mensaje de éxito después de un momento
      setTimeout(() => {
        mostrarMensaje("✅ ¡Descarga iniciada!", "success")
      }, 1000)
    })

    console.log("✅ Botón de descarga configurado")
  } else {
    console.warn("⚠️ No se encontró botón de descarga")
  }

  // También configurar enlaces de descarga directos
  document.querySelectorAll('a[href*="/descargar/"]').forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault()

      const href = this.href
      const cuentoId = href.match(/\/cuento\/(\d+)\/descargar\//)?.[1]

      console.log("📄 Descarga directa para cuento:", cuentoId)

      // Mostrar mensaje de descarga
      mostrarMensaje("📄 Preparando descarga...", "info")

      // Crear enlace temporal para forzar descarga
      const tempLink = document.createElement("a")
      tempLink.href = href
      tempLink.download = ""
      tempLink.style.display = "none"
      tempLink.target = "_blank"

      document.body.appendChild(tempLink)
      tempLink.click()
      document.body.removeChild(tempLink)

      setTimeout(() => {
        mostrarMensaje("✅ ¡Descarga iniciada!", "success")
      }, 1000)
    })
  })
}

/**
 * NUEVA FUNCIONALIDAD - Aplicar modo oscuro si está activo
 */
function applyDarkModeIfActive() {
  // Verificar si el modo oscuro está activo
  const isDarkMode = document.documentElement.classList.contains("dark-mode")

  if (isDarkMode) {
    console.log("🌙 Modo oscuro detectado en generated_story")

    // Forzar aplicación de estilos de modo oscuro
    const storyContainer = document.querySelector(".story-container")
    const storyCard = document.querySelector(".story-card")

    if (storyContainer) {
      storyContainer.style.setProperty("background", "var(--bg-primary)", "important")
      storyContainer.style.setProperty("color", "var(--text-primary)", "important")
    }

    if (storyCard) {
      storyCard.style.setProperty("background", "var(--card-bg)", "important")
      storyCard.style.setProperty("border-color", "var(--border-color)", "important")
    }

    // Aplicar a todas las secciones
    const sections = document.querySelectorAll(".story-image-section, .story-content-section, .story-actions")
    sections.forEach((section) => {
      section.style.setProperty("background", "var(--card-bg)", "important")
      if (section.classList.contains("story-actions")) {
        section.style.setProperty("background", "var(--hover-bg)", "important")
      }
    })

    // Aplicar a texto
    const textElements = document.querySelectorAll(".story-text, .story-text p")
    textElements.forEach((element) => {
      element.style.setProperty("color", "var(--text-primary)", "important")
    })

    // Aplicar a bordes
    const borderElements = document.querySelectorAll(".story-image-section, .story-actions")
    borderElements.forEach((element) => {
      element.style.setProperty("border-color", "var(--border-color)", "important")
    })

    console.log("✅ Modo oscuro aplicado correctamente a generated_story")
  } else {
    console.log("☀️ Modo claro activo en generated_story")
  }
}

/**
 * NUEVA FUNCIONALIDAD - Observar cambios en el modo oscuro
 */
function observeDarkModeChanges() {
  // Crear un observer para detectar cambios en la clase dark-mode
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "attributes" && mutation.attributeName === "class") {
        const isDarkMode = document.documentElement.classList.contains("dark-mode")
        console.log("🔄 Cambio de modo detectado:", isDarkMode ? "Oscuro" : "Claro")

        // Reaplicar estilos
        setTimeout(() => {
          applyDarkModeIfActive()
        }, 100)
      }
    })
  })

  // Observar cambios en el elemento html
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  })

  console.log("👁️ Observer del modo oscuro configurado")
}

/**
 * Configurar event listeners
 */
function setupEventListeners() {
  const audioBtn = document.getElementById("audio-btn")
  if (audioBtn) {
    audioBtn.addEventListener("click", toggleAudio)
  }

  // NUEVA FUNCIONALIDAD - Configurar observer del modo oscuro
  observeDarkModeChanges()
}

/**
 * ALTERNAR AUDIO (Play/Stop)
 */
function toggleAudio() {
  if (isPlaying) {
    stopStory()
  } else {
    playStory()
  }
}

/**
 * REPRODUCIR CUENTO
 */
function playStory() {
  console.log("▶️ Iniciando reproducción...")

  if (!window.speechSynthesis) {
    mostrarMensaje("❌ Tu navegador no soporta síntesis de voz", "error")
    return
  }

  // Obtener texto del cuento
  const storyElement = document.getElementById("story-content")
  const moralejaElement = document.getElementById("moraleja-content")

  let fullText = ""
  if (storyElement) {
    fullText += storyElement.innerText || storyElement.textContent
  }
  if (moralejaElement && moralejaElement.textContent.trim()) {
    fullText += "\n\n" + (moralejaElement.innerText || moralejaElement.textContent)
  }

  if (!fullText.trim()) {
    mostrarMensaje("❌ No hay texto para reproducir", "error")
    return
  }

  console.log("📝 Reproduciendo cuento...")

  // Crear utterance
  currentUtterance = new SpeechSynthesisUtterance(fullText)

  // Configurar voz en español
  currentUtterance.lang = "es-ES"
  currentUtterance.rate = 0.8
  currentUtterance.pitch = 1.0
  currentUtterance.volume = 1.0

  // Buscar voz en español
  const voices = window.speechSynthesis.getVoices()
  const spanishVoice = voices.find((voice) => voice.lang.startsWith("es"))

  if (spanishVoice) {
    currentUtterance.voice = spanishVoice
    console.log("🎤 Voz:", spanishVoice.name)
  }

  // Eventos
  currentUtterance.onstart = () => {
    console.log("✅ Reproducción iniciada")
    isPlaying = true
    updateAudioButton()
    mostrarMensaje("🎧 Escuchando cuento...", "info")
  }

  currentUtterance.onend = () => {
    console.log("✅ Reproducción completada")
    isPlaying = false
    updateAudioButton()
    mostrarMensaje("✅ Cuento terminado", "success")
  }

  currentUtterance.onerror = (event) => {
    console.error("❌ Error TTS:", event)
    isPlaying = false
    updateAudioButton()
    mostrarMensaje("❌ Audio detenido", "error")
  }

  // Iniciar reproducción
  window.speechSynthesis.speak(currentUtterance)
}

/**
 * DETENER CUENTO
 */
function stopStory() {
  console.log("⏹️ Deteniendo reproducción...")

  window.speechSynthesis.cancel()
  isPlaying = false
  currentUtterance = null
  updateAudioButton()
  mostrarMensaje("⏹️ Audio detenido", "info")
}

/**
 * ACTUALIZAR BOTÓN DE AUDIO
 */
function updateAudioButton() {
  const audioBtn = document.getElementById("audio-btn")

  if (audioBtn) {
    if (isPlaying) {
      audioBtn.innerHTML = `
        <div class="btn-icon">⏹️</div>
        <span>Detener Audio</span>
      `
      audioBtn.className = "action-btn btn-danger"
    } else {
      audioBtn.innerHTML = `
        <div class="btn-icon">🎧</div>
        <span>Escuchar Cuento</span>
      `
      audioBtn.className = "action-btn btn-audio"
    }
  }
}

/**
 * DETENER AUDIO AL CAMBIAR DE PÁGINA
 */
function stopAudioOnPageChange() {
  if (window.speechSynthesis && isPlaying) {
    console.log("🔄 Deteniendo audio por cambio de página...")
    window.speechSynthesis.cancel()
    isPlaying = false
    currentUtterance = null
  }
}

/**
 * Event listeners para detectar cambio de página
 */
window.addEventListener("beforeunload", stopAudioOnPageChange)
window.addEventListener("pagehide", stopAudioOnPageChange)

// Detener audio cuando se hace clic en enlaces
document.addEventListener("click", (event) => {
  const target = event.target

  // Si es un enlace que va a otra página
  if (target.tagName === "A" && target.href && !target.href.includes("#")) {
    stopAudioOnPageChange()
  }

  // Si es un botón que puede redirigir
  if (target.tagName === "BUTTON" && target.type === "submit") {
    stopAudioOnPageChange()
  }
})

/**
 * Mostrar mensajes
 */
function mostrarMensaje(mensaje, tipo = "info") {
  console.log(`📢 ${tipo.toUpperCase()}: ${mensaje}`)

  const messageDiv = document.createElement("div")

  let backgroundColor
  switch (tipo) {
    case "success":
      backgroundColor = "#8b5cf6"
      break
    case "error":
      backgroundColor = "#EF4444"
      break
    default:
      backgroundColor = "#9481dd"
  }

  messageDiv.style.cssText = `
    position: fixed;
    top: 2rem;
    right: 2rem;
    background: ${backgroundColor};
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    z-index: 1000;
    font-weight: 600;
    max-width: 300px;
    word-wrap: break-word;
  `

  messageDiv.textContent = mensaje
  document.body.appendChild(messageDiv)

  setTimeout(() => {
    if (document.body.contains(messageDiv)) {
      document.body.removeChild(messageDiv)
    }
  }, 3000)
}

/**
 * Animar elementos
 */
function animateElements() {
  const elements = document.querySelectorAll(".story-text, .story-image, .btn-action")

  elements.forEach((el, index) => {
    el.style.opacity = "0"
    el.style.transform = "translateY(20px)"

    setTimeout(() => {
      el.style.transition = "all 0.6s ease-out"
      el.style.opacity = "1"
      el.style.transform = "translateY(0)"
    }, index * 100)
  })
}

console.log("✅ Script de audio simplificado + modo oscuro + descarga cargado")
