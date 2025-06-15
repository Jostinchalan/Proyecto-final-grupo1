// static/js/library.js
console.log("🔄 Cargando biblioteca JavaScript - VERSIÓN CON FILTROS DINÁMICOS")

// ===================================
// VARIABLES GLOBALES ULTRA SIMPLES
// ===================================
window.audioControl = {
  isPlaying: false,
  currentCuentoId: null,
  utterance: null,
  manualStop: false,
}

// NUEVA: Variable para controlar filtros dinámicos
window.filtrosControl = {
  searchTimeout: null,
  isFiltering: false
}

// ===================================
// INICIALIZACIÓN
// ===================================
document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ DOM cargado - Inicializando biblioteca")

  // Limpiar cualquier audio previo
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }

  // Inicializar después de un pequeño delay
  setTimeout(initializeBiblioteca, 500)
})

function initializeBiblioteca() {
  console.log("🚀 Inicializando biblioteca...")

  // Configurar filtros MEJORADOS
  setupFilters()

  // Configurar botones de audio - MÉTODO ULTRA SIMPLE
  setupAudioButtons()

  // Configurar botones de descarga
  setupDownloadButtons()

  // Configurar otros botones
  setupOtherButtons()

  // Configurar modal de forma directa
  setupModalDirecto()

  console.log("✅ Biblioteca inicializada correctamente")
}

// ===================================
// CONFIGURACIÓN DE FILTROS MEJORADA
// ===================================
function setupFilters() {
  console.log("🔍 Configurando filtros dinámicos...")

  const perfilSelector = document.getElementById("perfil")
  const temaSelector = document.getElementById("tema")
  const filtrosForm = document.getElementById("filtros-form")
  const tituloInput = document.getElementById("titulo")

  // NUEVO: Manejar cambio de perfil con actualización dinámica de temas
  if (perfilSelector) {
    perfilSelector.addEventListener("change", function () {
      const perfilId = this.value
      console.log("👤 Perfil seleccionado:", perfilId)
      actualizarTemasPorPerfilDinamico(perfilId)
    })
  }

  // NUEVO: Manejar cambio de tema
  if (temaSelector) {
    temaSelector.addEventListener("change", function () {
      console.log("🎨 Tema seleccionado:", this.value)
      // Auto-submit después de cambio de tema
      setTimeout(() => filtrosForm.submit(), 100)
    })
  }

  // MEJORADO: Búsqueda por título con autocomplete
  if (tituloInput) {
    setupTitleAutocomplete(tituloInput, filtrosForm)
  }

  // Auto-submit para otros filtros
  const otherFilterSelects = document.querySelectorAll(".filter-select:not(#perfil):not(#tema)")
  otherFilterSelects.forEach((select) => {
    select.addEventListener("change", function () {
      console.log("🔄 Filtro cambiado:", this.name, this.value)
      filtrosForm.submit()
    })
  })
}

// NUEVA FUNCIÓN: Actualizar temas por perfil de forma dinámica - MEJORADA
async function actualizarTemasPorPerfilDinamico(perfilId) {
  const temaSelector = document.getElementById("tema")
  const filtrosForm = document.getElementById("filtros-form")

  if (!temaSelector) return

  // Mostrar estado de carga
  const temaActual = temaSelector.value
  temaSelector.disabled = true
  temaSelector.innerHTML = '<option value="todos">🔄 Cargando temas...</option>'

  try {
    console.log("📡 Obteniendo temas para perfil:", perfilId)

    const response = await fetch(`/library/ajax/themes-by-profile/?profile_id=${perfilId}`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()

    if (data.success) {
      // Limpiar y reconstruir opciones
      temaSelector.innerHTML = ''

      // Opción "todos"
      const opcionTodos = document.createElement('option')
      opcionTodos.value = 'todos'
      opcionTodos.textContent = 'TODOS LOS TEMAS'
      temaSelector.appendChild(opcionTodos)

      // Agregar temas disponibles
      if (data.temas && data.temas.length > 0) {
        data.temas.forEach(tema => {
          const option = document.createElement('option')
          option.value = tema
          option.textContent = tema.toUpperCase()
          temaSelector.appendChild(option)
        })

        console.log(`✅ ${data.temas.length} temas cargados para perfil ${perfilId}`)
      } else {
        console.log("ℹ️ No hay temas disponibles para este perfil")
      }

      // Restaurar selección si el tema sigue disponible
      if (data.temas.includes(temaActual)) {
        temaSelector.value = temaActual
      } else {
        temaSelector.value = 'todos'
      }

      temaSelector.disabled = false

      // Auto-submit después de actualizar temas
      setTimeout(() => {
        console.log("🔄 Auto-submit después de actualizar temas")
        filtrosForm.submit()
      }, 300)

    } else {
      throw new Error(data.error || 'Error al obtener temas')
    }

  } catch (error) {
    console.error("❌ Error al obtener temas:", error)
    temaSelector.innerHTML = '<option value="todos">❌ Error al cargar temas</option>'
    temaSelector.disabled = false
    showMessage("❌ Error al cargar temas: " + error.message, "error")
  }
}

// NUEVA FUNCIÓN: Configurar autocomplete para título - MEJORADA
function setupTitleAutocomplete(tituloInput, filtrosForm) {
  console.log("🔍 Configurando autocomplete para títulos...")

  let autocompleteContainer = null
  let selectedIndex = -1

  // Crear contenedor de autocomplete
  function createAutocompleteContainer() {
    if (autocompleteContainer) return

    autocompleteContainer = document.createElement('div')
    autocompleteContainer.className = 'autocomplete-suggestions'
    autocompleteContainer.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ddd;
      border-top: none;
      border-radius: 0 0 8px 8px;
      max-height: 200px;
      overflow-y: auto;
      z-index: 1000;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      display: none;
    `

    // Hacer el contenedor padre relativo
    tituloInput.parentElement.style.position = 'relative'
    tituloInput.parentElement.appendChild(autocompleteContainer)
  }

  // Manejar input con debounce mejorado
  tituloInput.addEventListener('input', function() {
    const query = this.value.trim()
    selectedIndex = -1

    clearTimeout(window.filtrosControl.searchTimeout)

    if (query.length < 1) {
      hideAutocomplete()
      // Auto-submit para limpiar filtro
      window.filtrosControl.searchTimeout = setTimeout(() => {
        if (!window.filtrosControl.isFiltering) {
          console.log("🔄 Auto-submit para limpiar filtro")
          filtrosForm.submit()
        }
      }, 500)
      return
    }

    // Buscar sugerencias con delay más corto
    window.filtrosControl.searchTimeout = setTimeout(() => {
      searchTitleSuggestions(query)
    }, 200) // Reducido de 300ms a 200ms
  })

  // Buscar sugerencias mejorado
  async function searchTitleSuggestions(query) {
    try {
      const perfilId = document.getElementById('perfil')?.value || 'todos'
      const tema = document.getElementById('tema')?.value || 'todos'

      const params = new URLSearchParams({
        q: query,
        profile_id: perfilId,
        theme: tema
      })

      const response = await fetch(`/library/ajax/search-titles/?${params}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      if (data.success && data.titles && data.titles.length > 0) {
        showAutocomplete(data.titles, query)
      } else {
        hideAutocomplete()
        // Auto-submit si no hay sugerencias pero hay texto
        if (query.length >= 2) {
          window.filtrosControl.searchTimeout = setTimeout(() => {
            if (!window.filtrosControl.isFiltering) {
              console.log("🔍 Auto-submit por búsqueda sin sugerencias:", query)
              window.filtrosControl.isFiltering = true
              filtrosForm.submit()
            }
          }, 800)
        }
      }

    } catch (error) {
      console.error("❌ Error en búsqueda de títulos:", error)
      hideAutocomplete()
    }
  }

  // Mostrar sugerencias mejorado
  function showAutocomplete(titles, query) {
    createAutocompleteContainer()

    autocompleteContainer.innerHTML = ''

    titles.forEach((title, index) => {
      const suggestion = document.createElement('div')
      suggestion.className = 'autocomplete-suggestion'
      suggestion.dataset.index = index
      suggestion.style.cssText = `
        padding: 12px 15px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
        transition: background-color 0.2s;
        font-size: 14px;
      `

      // Resaltar texto coincidente
      const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
      const highlightedTitle = title.replace(regex, '<strong style="color: #8B5CF6;">$1</strong>')
      suggestion.innerHTML = highlightedTitle

      // Click en sugerencia
      suggestion.addEventListener('click', () => {
        selectSuggestion(title)
      })

      // Hover effect
      suggestion.addEventListener('mouseenter', () => {
        clearSelection()
        suggestion.style.backgroundColor = '#f5f5f5'
        selectedIndex = index
      })

      suggestion.addEventListener('mouseleave', () => {
        suggestion.style.backgroundColor = 'white'
      })

      autocompleteContainer.appendChild(suggestion)
    })

    autocompleteContainer.style.display = 'block'
  }

  // Seleccionar sugerencia
  function selectSuggestion(title) {
    tituloInput.value = title
    hideAutocomplete()
    window.filtrosControl.isFiltering = true
    console.log("🎯 Sugerencia seleccionada:", title)
    filtrosForm.submit()
  }

  // Limpiar selección
  function clearSelection() {
    autocompleteContainer.querySelectorAll('.autocomplete-suggestion').forEach(el => {
      el.style.backgroundColor = 'white'
    })
  }

  // Ocultar sugerencias
  function hideAutocomplete() {
    if (autocompleteContainer) {
      autocompleteContainer.style.display = 'none'
    }
    selectedIndex = -1
  }

  // Manejar teclas mejorado
  tituloInput.addEventListener('keydown', (e) => {
    const suggestions = autocompleteContainer?.querySelectorAll('.autocomplete-suggestion')

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (suggestions && suggestions.length > 0) {
        selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1)
        updateSelection(suggestions)
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (suggestions && suggestions.length > 0) {
        selectedIndex = Math.max(selectedIndex - 1, -1)
        updateSelection(suggestions)
      }
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (selectedIndex >= 0 && suggestions && suggestions[selectedIndex]) {
        const selectedTitle = suggestions[selectedIndex].textContent
        selectSuggestion(selectedTitle)
      } else {
        hideAutocomplete()
        window.filtrosControl.isFiltering = true
        console.log("🔍 Enter presionado - búsqueda directa:", tituloInput.value)
        filtrosForm.submit()
      }
    } else if (e.key === 'Escape') {
      hideAutocomplete()
    }
  })

  // Actualizar selección visual
  function updateSelection(suggestions) {
    clearSelection()
    if (selectedIndex >= 0 && suggestions[selectedIndex]) {
      suggestions[selectedIndex].style.backgroundColor = '#f5f5f5'
    }
  }

  // Ocultar al hacer click fuera
  document.addEventListener('click', (e) => {
    if (!tituloInput.contains(e.target) && !autocompleteContainer?.contains(e.target)) {
      hideAutocomplete()
    }
  })

  // Auto-submit con debounce para búsqueda en tiempo real
  tituloInput.addEventListener('input', function() {
    clearTimeout(window.filtrosControl.searchTimeout)
    window.filtrosControl.searchTimeout = setTimeout(() => {
      if (!window.filtrosControl.isFiltering && this.value.trim().length >= 2) {
        console.log("🔍 Auto-submit por búsqueda en tiempo real:", this.value)
        window.filtrosControl.isFiltering = true
        filtrosForm.submit()
      }
      window.filtrosControl.isFiltering = false
    }, 1200) // 1.2 segundos de delay para auto-submit
  })
}
// ===================================
// RESTO DE FUNCIONES EXISTENTES (sin cambios)
// ===================================

// NUEVA FUNCIONALIDAD: CONFIGURAR BOTONES DE DESCARGA
function setupDownloadButtons() {
  console.log("📄 Configurando botones de descarga...")

  // Buscar todos los enlaces de descarga
  document.querySelectorAll('a[href*="/descargar/"], .download-btn, [data-action="download"]').forEach((element) => {
    element.addEventListener("click", function (e) {
      e.preventDefault()
      e.stopPropagation()

      let href = this.href
      let cuentoId = null

      // Si es un botón con data-cuento-id
      if (this.dataset.cuentoId) {
        cuentoId = this.dataset.cuentoId
        href = `/stories/cuento/${cuentoId}/descargar/`
      } else if (href) {
        // Extraer ID del cuento de la URL
        const match = href.match(/\/cuento\/(\d+)\/descargar\//)
        if (match) {
          cuentoId = match[1]
        }
      }

      if (!cuentoId || !href) {
        console.error("❌ No se pudo determinar el ID del cuento o la URL")
        showMessage("❌ Error: No se pudo determinar el cuento a descargar", "error")
        return
      }

      console.log("📄 Iniciando descarga para cuento:", cuentoId)
      console.log("📄 URL de descarga:", href)

      // Mostrar mensaje de descarga
      showMessage("📄 Preparando descarga...", "info")

      // Crear enlace temporal para forzar descarga
      const tempLink = document.createElement("a")
      tempLink.href = href
      tempLink.download = "" // Esto fuerza la descarga
      tempLink.style.display = "none"
      tempLink.target = "_blank" // Abrir en nueva ventana como respaldo

      // Agregar al DOM, hacer clic y remover
      document.body.appendChild(tempLink)
      tempLink.click()
      document.body.removeChild(tempLink)

      // Mensaje de éxito después de un momento
      setTimeout(() => {
        showMessage("✅ ¡Descarga iniciada!", "success")
      }, 1000)
    })
  })

  console.log("✅ Botones de descarga configurados")
}

// CONFIGURACIÓN DIRECTA DEL MODAL - NUEVA FUNCIÓN
function setupModalDirecto() {
  console.log("🔍 Configurando modal de forma directa")

  // 1. Configurar botón cancelar con método directo
  const cancelarBtn = document.querySelector(".modal-cancel")
  if (cancelarBtn) {
    // Eliminar event listeners previos
    const nuevoCancelarBtn = cancelarBtn.cloneNode(true)
    cancelarBtn.parentNode.replaceChild(nuevoCancelarBtn, cancelarBtn)

    // Agregar event listener directo con onclick
    nuevoCancelarBtn.onclick = (e) => {
      e.preventDefault()
      e.stopPropagation()
      console.log("🚫 Botón cancelar clickeado (método directo)")
      closeDeleteModal()
      return false
    }
    console.log("✅ Botón cancelar configurado con método directo")
  } else {
    console.warn("⚠️ No se encontró el botón cancelar")
  }

  // 2. Configurar botón X para cerrar con método directo
  const closeBtn = document.querySelector(".modal-close")
  if (closeBtn) {
    // Eliminar event listeners previos
    const nuevoCloseBtn = closeBtn.cloneNode(true)
    closeBtn.parentNode.replaceChild(nuevoCloseBtn, closeBtn)

    // Agregar event listener directo con onclick
    nuevoCloseBtn.onclick = (e) => {
      e.preventDefault()
      e.stopPropagation()
      console.log("❌ Botón cerrar (X) clickeado (método directo)")
      closeDeleteModal()
      return false
    }
    console.log("✅ Botón cerrar (X) configurado con método directo")
  } else {
    console.warn("⚠️ No se encontró el botón cerrar (X)")
  }

  // 3. Configurar cierre al hacer click fuera del modal
  const modal = document.getElementById("deleteModal")
  if (modal) {
    modal.onclick = (e) => {
      if (e.target === modal) {
        console.log("🌫️ Click fuera del modal (método directo)")
        closeDeleteModal()
      }
    }
    console.log("✅ Cierre al hacer click fuera configurado")
  } else {
    console.warn("⚠️ No se encontró el modal")
  }
}

// CONFIGURACIÓN DE BOTONES DE AUDIO - ULTRA SIMPLE
function setupAudioButtons() {
  console.log("🎵 Configurando botones de audio...")

  // REMOVER TODOS LOS EVENT LISTENERS PREVIOS
  document.querySelectorAll(".play-story").forEach((btn) => {
    // Clonar el botón para remover todos los event listeners
    const newBtn = btn.cloneNode(true)
    btn.parentNode.replaceChild(newBtn, btn)
  })

  // AGREGAR NUEVOS EVENT LISTENERS - UNO POR UNO
  document.querySelectorAll(".play-story").forEach((btn) => {
    btn.addEventListener("click", handleAudioClick, { once: false })
  })

  console.log("✅ Botones de audio configurados")
}

// MANEJAR CLICK EN BOTÓN DE AUDIO - ULTRA SIMPLE
function handleAudioClick(event) {
  event.preventDefault()
  event.stopPropagation()

  const btn = event.currentTarget
  const cuentoId = btn.dataset.cuentoId

  console.log("🎵 Click en botón audio - Cuento:", cuentoId)
  console.log("🎵 Estado actual:", window.audioControl.isPlaying ? "REPRODUCIENDO" : "DETENIDO")
  console.log("🎵 Texto del botón:", btn.textContent.trim())

  // LÓGICA ULTRA SIMPLE
  if (btn.textContent.includes("DETENER")) {
    console.log("⏹️ DETENER AUDIO")
    stopAudio()
  } else {
    console.log("▶️ INICIAR AUDIO")
    playAudio(cuentoId)
  }
}

// REPRODUCIR AUDIO - ULTRA SIMPLE
async function playAudio(cuentoId) {
  console.log("▶️ Iniciando reproducción para cuento:", cuentoId)

  try {
    // 1. DETENER CUALQUIER AUDIO PREVIO
    if (window.speechSynthesis.speaking) {
      console.log("🛑 Deteniendo audio previo...")
      window.speechSynthesis.cancel()
      await new Promise((resolve) => setTimeout(resolve, 100))
    }

    // 2. OBTENER CONTENIDO
    console.log("📥 Obteniendo contenido del cuento...")
    const response = await fetch(`/stories/cuento/${cuentoId}/contenido/`)

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`)
    }

    const data = await response.json()

    if (!data.success || !data.contenido) {
      throw new Error(data.message || "No se pudo obtener el contenido")
    }

    console.log("✅ Contenido obtenido correctamente")

    // 3. VERIFICAR SOPORTE DE TTS
    if (!window.speechSynthesis) {
      throw new Error("Tu navegador no soporta síntesis de voz")
    }

    // 4. CREAR UTTERANCE
    const utterance = new SpeechSynthesisUtterance(data.contenido)
    utterance.lang = "es-ES"
    utterance.rate = 0.8
    utterance.pitch = 1.0
    utterance.volume = 1.0

    // 5. CONFIGURAR VOZ EN ESPAÑOL
    const voices = window.speechSynthesis.getVoices()
    const spanishVoice = voices.find((voice) => voice.lang.includes("es"))
    if (spanishVoice) {
      utterance.voice = spanishVoice
      console.log("🎤 Voz configurada:", spanishVoice.name)
    }

    // 6. CONFIGURAR EVENTOS - ULTRA SIMPLE
    utterance.onstart = () => {
      console.log("✅ Audio iniciado")
      window.audioControl.isPlaying = true
      window.audioControl.currentCuentoId = cuentoId
      window.audioControl.utterance = utterance
      window.audioControl.manualStop = false

      updateButtonToStop(cuentoId)
      showMessage("🎧 Reproduciendo cuento...", "info")
    }

    utterance.onend = () => {
      console.log("✅ Audio terminado")

      // SOLO RESTAURAR SI NO FUE PARADA MANUAL
      if (!window.audioControl.manualStop) {
        console.log("📝 Terminación natural - restaurando botón")
        resetAudioState()
        showMessage("✅ Cuento terminado", "success")
      } else {
        console.log("⏹️ Fue parada manual - no hacer nada")
      }
    }

    utterance.onerror = (event) => {
      console.error("❌ Error en TTS:", event.error)
      resetAudioState()
      showMessage("❌ Error en la reproducción", "error")
    }

    // 7. INICIAR REPRODUCCIÓN
    console.log("🎤 Iniciando síntesis de voz...")
    window.speechSynthesis.speak(utterance)
  } catch (error) {
    console.error("❌ Error al reproducir:", error)
    resetAudioState()
    showMessage(`❌ Error: ${error.message}`, "error")
  }
}

// DETENER AUDIO - ULTRA SIMPLE
function stopAudio() {
  console.log("⏹️ Deteniendo audio...")

  // MARCAR COMO PARADA MANUAL
  window.audioControl.manualStop = true

  // CANCELAR SÍNTESIS
  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel()
  }

  // RESETEAR ESTADO
  resetAudioState()

  showMessage("⏹️ Audio detenido", "info")
}

// FUNCIONES DE ESTADO - ULTRA SIMPLES
function updateButtonToStop(cuentoId) {
  const btn = document.querySelector(`[data-cuento-id="${cuentoId}"].play-story`)
  if (btn) {
    btn.innerHTML = '<i class="fas fa-stop"></i> DETENER'
    btn.style.backgroundColor = "#ef4444"
    btn.style.color = "white"
  }
}

function resetAudioState() {
  console.log("🔄 Reseteando estado de audio...")

  // RESTAURAR BOTÓN
  if (window.audioControl.currentCuentoId) {
    const btn = document.querySelector(`[data-cuento-id="${window.audioControl.currentCuentoId}"].play-story`)
    if (btn) {
      btn.innerHTML = '<i class="fas fa-play"></i> ESCUCHAR'
      btn.style.backgroundColor = ""
      btn.style.color = ""
    }
  }

  // LIMPIAR ESTADO GLOBAL
  window.audioControl.isPlaying = false
  window.audioControl.currentCuentoId = null
  window.audioControl.utterance = null
  // NO resetear manualStop aquí
}

// CONFIGURACIÓN DE OTROS BOTONES
function setupOtherButtons() {
  // Favoritos
  document.querySelectorAll(".favorite-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault()
      e.stopPropagation()
      const cuentoId = this.dataset.cuentoId
      toggleFavorito(cuentoId)
    })
  })

  // Eliminar
  document.querySelectorAll(".delete-story").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault()
      e.stopPropagation()
      const cuentoId = this.dataset.cuentoId
      const cuentoTitulo = this.dataset.cuentoTitulo
      mostrarModalEliminar(cuentoId, cuentoTitulo)
    })
  })
}

// FUNCIONES DE FAVORITOS Y MODAL
function toggleFavorito(cuentoId) {
  const csrfToken =
    document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content")

  if (!csrfToken) {
    showMessage("Error: Token CSRF no encontrado", "error")
    return
  }

  fetch(`/stories/cuento/${cuentoId}/favorito/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        document.querySelectorAll(`[data-cuento-id="${cuentoId}"].favorite-btn`).forEach((btn) => {
          const icon = btn.querySelector("i")
          if (data.es_favorito) {
            icon.className = "fas fa-heart"
            btn.classList.add("active")
          } else {
            icon.className = "far fa-heart"
            btn.classList.remove("active")
          }
        })
        showMessage(data.message, "success")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showMessage("Error de conexión", "error")
    })
}

function mostrarModalEliminar(cuentoId, cuentoTitulo) {
  const modal = document.getElementById("deleteModal")
  const tituloModal = document.getElementById("cuentoTituloModal")
  const confirmBtn = document.getElementById("confirmDeleteBtn")
  const cancelBtn = document.querySelector(".modal-cancel")

  if (modal && tituloModal && confirmBtn) {
    tituloModal.textContent = cuentoTitulo
    modal.style.display = "flex"

    // NUEVO: Configurar botones directamente aquí
    confirmBtn.onclick = () => eliminarCuento(cuentoId)

    // NUEVO: Configurar botón cancelar directamente aquí
    if (cancelBtn) {
      cancelBtn.onclick = (e) => {
        e.preventDefault()
        e.stopPropagation()
        closeDeleteModal()
        return false
      }
    }

    console.log("📋 Modal de eliminación mostrado para:", cuentoTitulo)
  }
}

function closeDeleteModal() {
  const modal = document.getElementById("deleteModal")
  if (modal) {
    modal.style.display = "none"
    console.log("✅ Modal de eliminación cerrado")
  }
}

function eliminarCuento(cuentoId) {
  const csrfToken =
    document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content")

  fetch(`/stories/cuento/${cuentoId}/eliminar/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showMessage(data.message, "success")
        closeDeleteModal()
        setTimeout(() => window.location.reload(), 1000)
      } else {
        showMessage("Error al eliminar cuento", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showMessage("Error de conexión", "error")
    })
}

// FUNCIÓN PARA MOSTRAR MENSAJES
function showMessage(mensaje, tipo = "info") {
  console.log(`📢 ${tipo.toUpperCase()}: ${mensaje}`)

  const messageDiv = document.createElement("div")
  messageDiv.textContent = mensaje
  messageDiv.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    z-index: 1000;
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease;
  `

  switch (tipo) {
    case "success":
      messageDiv.style.backgroundColor = "#10b981"
      break
    case "error":
      messageDiv.style.backgroundColor = "#ef4444"
      break
    case "info":
      messageDiv.style.backgroundColor = "#3b82f6"
      break
    default:
      messageDiv.style.backgroundColor = "#6b7280"
  }

  document.body.appendChild(messageDiv)

  setTimeout(() => {
    messageDiv.style.opacity = "1"
    messageDiv.style.transform = "translateX(0)"
  }, 100)

  setTimeout(() => {
    messageDiv.style.opacity = "0"
    messageDiv.style.transform = "translateX(100%)"
    setTimeout(() => {
      if (messageDiv.parentNode) {
        messageDiv.parentNode.removeChild(messageDiv)
      }
    }, 300)
  }, 3000)
}

// FUNCIONES GLOBALES
window.closeDeleteModal = closeDeleteModal
window.toggleFavorito = toggleFavorito
window.mostrarModalEliminar = mostrarModalEliminar
window.eliminarCuento = eliminarCuento

// NUEVO: Asegurar que el botón cancelar funcione
document.addEventListener("click", (e) => {
  if (
    e.target &&
    (e.target.classList.contains("modal-cancel") ||
      (e.target.parentElement && e.target.parentElement.classList.contains("modal-cancel")))
  ) {
    console.log("🚫 Botón cancelar clickeado (event listener global)")
    closeDeleteModal()
    e.preventDefault()
    e.stopPropagation()
  }
})

console.log("✅ Biblioteca JavaScript cargado - VERSIÓN CON FILTROS DINÁMICOS INTEGRADOS")