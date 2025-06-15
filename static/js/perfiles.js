let perfilAEliminar = null

// Función para obtener el token CSRF
function getCSRFToken() {
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
  if (csrfToken) {
    return csrfToken.value
  }

  // Alternativa: buscar en las cookies
  const cookies = document.cookie.split(";")
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=")
    if (name === "csrftoken") {
      return value
    }
  }

  console.error("CSRF token not found")
  return null
}

// Función para confirmar eliminación
function confirmarEliminacion(perfilId, nombrePerfil) {
  console.log("🎯 Confirmar eliminación llamada:", perfilId, nombrePerfil)
  perfilAEliminar = perfilId
  document.getElementById("perfilNombre").textContent = nombrePerfil
  document.getElementById("confirmModal").style.display = "flex"
  document.body.style.overflow = "hidden" // Prevenir scroll del fondo
}

// Función para cerrar modal
function cerrarModal() {
  document.getElementById("confirmModal").style.display = "none"
  document.body.style.overflow = "auto"
  perfilAEliminar = null

  // Resetear el botón
  const btnDelete = document.querySelector(".btn-confirm-delete")
  btnDelete.textContent = "Eliminar"
  btnDelete.disabled = false
}

// Función para eliminar perfil
function eliminarPerfil() {
  if (!perfilAEliminar) {
    console.error("No hay perfil seleccionado para eliminar")
    return
  }

  const csrfToken = getCSRFToken()
  if (!csrfToken) {
    mostrarMensaje("Error: Token de seguridad no encontrado", "error")
    return
  }

  // Mostrar loading en el botón
  const btnDelete = document.querySelector(".btn-confirm-delete")
  const originalText = btnDelete.textContent
  btnDelete.textContent = "Eliminando..."
  btnDelete.disabled = true

  console.log("🔄 Eliminando perfil:", perfilAEliminar)
  console.log("🔑 CSRF Token:", csrfToken)

  // Hacer petición AJAX
  fetch(`/user/perfiles/${perfilAEliminar}/eliminar-ajax/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json",
    },
    credentials: "same-origin", // Incluir cookies
  })
    .then((response) => {
      console.log("📡 Response status:", response.status)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      console.log("✅ Response data:", data)

      if (data.success) {
        // Mostrar mensaje de éxito
        mostrarMensaje(data.message, "success")

        // Remover la card del DOM con animación
        const profileCard = document.querySelector(`[data-perfil-id="${perfilAEliminar}"]`)
        if (profileCard) {
          profileCard.style.transition = "all 0.3s ease"
          profileCard.style.transform = "scale(0.8)"
          profileCard.style.opacity = "0"

          setTimeout(() => {
            profileCard.remove()
          }, 300)
        }

        cerrarModal()
      } else {
        mostrarMensaje(data.message || "Error al eliminar el perfil", "error")
        btnDelete.textContent = originalText
        btnDelete.disabled = false
      }
    })
    .catch((error) => {
      console.error("❌ Error completo:", error)
      mostrarMensaje("Error al eliminar el perfil. Inténtalo de nuevo.", "error")
      btnDelete.textContent = originalText
      btnDelete.disabled = false
    })
}

// Función para mostrar mensajes
function mostrarMensaje(mensaje, tipo) {
  const messageDiv = document.createElement("div")
  messageDiv.className = `message-toast message-${tipo}`
  messageDiv.textContent = mensaje

  // Estilos del mensaje
  messageDiv.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: ${tipo === "success" ? "#10B981" : "#EF4444"};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        z-index: 1001;
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
        word-wrap: break-word;
    `

  document.body.appendChild(messageDiv)

  // Remover después de 4 segundos
  setTimeout(() => {
    messageDiv.style.animation = "slideOutRight 0.3s ease-in"
    setTimeout(() => {
      if (document.body.contains(messageDiv)) {
        document.body.removeChild(messageDiv)
      }
    }, 300)
  }, 4000)
}

// Cerrar modal con ESC
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    cerrarModal()
  }
})

// Cerrar modal al hacer click fuera
document.getElementById("confirmModal").addEventListener("click", function (e) {
  if (e.target === this) {
    cerrarModal()
  }
})

// Funciones existentes...
function toggleFavorite(perfilId) {
  console.log("Toggle favorite for profile:", perfilId)
  const button = event.target.closest(".btn-favorite")
  button.style.color = button.style.color === "rgb(252, 165, 165)" ? "white" : "#FCA5A5"
}

function toggleMenu(index) {
  console.log("Toggle menu for profile:", index)
}

// Animaciones adicionales
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOM cargado, inicializando...")

  // Animación de entrada para las cards
  const cards = document.querySelectorAll(".profile-card, .add-profile-card")
  cards.forEach((card, index) => {
    card.style.opacity = "0"
    card.style.transform = "translateY(20px)"

    setTimeout(() => {
      card.style.transition = "all 0.5s ease"
      card.style.opacity = "1"
      card.style.transform = "translateY(0)"
    }, index * 100)
  })

  // Debug: verificar que el CSRF token esté disponible
  const csrfAvailable = getCSRFToken()
  console.log("🔑 CSRF Token disponible:", csrfAvailable ? "Sí" : "No")
  if (csrfAvailable) {
    console.log("🔑 Token:", csrfAvailable.substring(0, 10) + "...")
  }
})
