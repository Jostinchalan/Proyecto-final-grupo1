document.addEventListener("DOMContentLoaded", () => {
  // Variables para manejo de avatar
  const avatarInput = document.getElementById("avatar-input")
  const avatarPreview = document.getElementById("avatar-preview")
  const defaultAvatar = document.getElementById("default-avatar")
  const avatarSaveSection = document.getElementById("avatar-save-section")
  const saveAvatarBtn = document.getElementById("save-avatar-btn")
  const cancelAvatarBtn = document.getElementById("cancel-avatar-btn")

  let originalAvatarSrc = null
  let selectedFile = null

  // Variables para validaciones
  const usernameInput = document.getElementById("username")
  const emailInput = document.getElementById("email")
  const currentPasswordInput = document.getElementById("id_old_password")
  const newPasswordInput = document.getElementById("id_new_password1")
  const confirmPasswordInput = document.getElementById("id_new_password2")

  // Guardar la imagen original al cargar la página
  if (avatarPreview) {
    originalAvatarSrc = avatarPreview.src
  }

  // NUEVO: Manejar envío del formulario de perfil
  const profileForm = document.getElementById("profile-form")
  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault()

      const formData = new FormData(profileForm)
      const submitButton = profileForm.querySelector('button[type="submit"]')

      // Mostrar estado de carga
      const originalText = submitButton.textContent
      submitButton.textContent = "Guardando..."
      submitButton.disabled = true

      try {
        console.log("📤 Enviando formulario de perfil...")
        console.log("📦 Datos del formulario:", Object.fromEntries(formData))

        const response = await fetch("/user/settings/", {
          method: "POST",
          body: formData,
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
          },
        })

        console.log("📡 Respuesta del servidor:", response.status)

        if (response.ok) {
          // Verificar si es una redirección o respuesta JSON
          const contentType = response.headers.get("content-type")

          if (contentType && contentType.includes("application/json")) {
            const data = await response.json()
            console.log("📋 Datos de respuesta JSON:", data)
            if (data.status === "success") {
              showMessage("Perfil actualizado exitosamente", "success")
              // Recargar la página para mostrar los cambios
              setTimeout(() => {
                window.location.reload()
              }, 1500)
            } else {
              showMessage(data.message || "Error al actualizar perfil", "error")
            }
          } else {
            // Es una redirección, recargar la página
            console.log("🔄 Redirección detectada, recargando página...")
            showMessage("Perfil actualizado exitosamente", "success")
            setTimeout(() => {
              window.location.reload()
            }, 1500)
          }
        } else {
          throw new Error(`Error del servidor: ${response.status}`)
        }
      } catch (error) {
        console.error("❌ Error:", error)
        showMessage("Error al guardar los cambios", "error")
      } finally {
        // Restaurar botón
        submitButton.textContent = originalText
        submitButton.disabled = false
      }
    })
  }

  // Avatar upload functionality
  avatarInput.addEventListener("change", (e) => {
    const file = e.target.files[0]
    if (file) {
      selectedFile = file
      const reader = new FileReader()
      reader.onload = (e) => {
        const newImageSrc = e.target.result

        if (avatarPreview) {
          avatarPreview.src = newImageSrc
        } else if (defaultAvatar) {
          // Reemplazar el avatar por defecto con la nueva imagen
          const profileAvatar = document.querySelector(".profile-avatar")
          profileAvatar.innerHTML = `
            <img src="${newImageSrc}" alt="Avatar" id="avatar-preview">
            <div class="avatar-overlay">
              <label for="avatar-input" class="avatar-button">
                <i class="fas fa-camera"></i>
                AÑADIR FOTO
              </label>
              <input type="file" id="avatar-input" accept="image/*" style="display: none;">
            </div>
          `

          // Reconectar el event listener para el nuevo input
          const newAvatarInput = document.getElementById("avatar-input")
          newAvatarInput.addEventListener("change", avatarInput.onchange)
        }

        // Mostrar botones de guardar/cancelar
        avatarSaveSection.style.display = "flex"
      }
      reader.readAsDataURL(file)
    }
  })

  // Guardar avatar
  saveAvatarBtn.addEventListener("click", async () => {
    if (!selectedFile) return

    const formData = new FormData()
    formData.append("avatar", selectedFile)
    formData.append("csrfmiddlewaretoken", getCookie("csrftoken"))
    formData.append("form_type", "avatar")

    try {
      saveAvatarBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...'
      saveAvatarBtn.disabled = true

      const response = await fetch("/user/settings/", {
        method: "POST",
        body: formData,
      })

      if (response.ok) {
        // Actualizar todas las imágenes de avatar en la página
        const newAvatarPreview = document.getElementById("avatar-preview")
        if (newAvatarPreview) {
          const newSrc = newAvatarPreview.src

          // Actualizar avatar en la barra superior
          const topBarAvatar = document.querySelector(".top-bar .avatar img")
          if (topBarAvatar) {
            topBarAvatar.src = newSrc
          }

          // Actualizar avatar en el sidebar derecho
          const sidebarAvatar = document.querySelector(".user-avatar img")
          if (sidebarAvatar) {
            sidebarAvatar.src = newSrc
          }

          // Actualizar avatar en user-profile
          const userProfileAvatar = document.querySelector(".user-profile .avatar img")
          if (userProfileAvatar) {
            userProfileAvatar.src = newSrc
          }

          originalAvatarSrc = newSrc
        }

        // Ocultar botones
        avatarSaveSection.style.display = "none"
        selectedFile = null

        // Mostrar mensaje de éxito
        showMessage("Foto de perfil actualizada correctamente", "success")

        // Recargar la página después de un breve delay para ver los cambios
        setTimeout(() => {
          window.location.reload()
        }, 1500)
      } else {
        throw new Error("Error al guardar la imagen")
      }
    } catch (error) {
      console.error("Error:", error)
      showMessage("Error al guardar la foto de perfil", "error")
    } finally {
      saveAvatarBtn.innerHTML = '<i class="fas fa-save"></i> Guardar foto'
      saveAvatarBtn.disabled = false
    }
  })

  // Cancelar cambio de avatar
  cancelAvatarBtn.addEventListener("click", () => {
    // Restaurar imagen original
    const currentAvatarPreview = document.getElementById("avatar-preview")
    if (currentAvatarPreview && originalAvatarSrc) {
      currentAvatarPreview.src = originalAvatarSrc
    } else if (!originalAvatarSrc) {
      // Restaurar avatar por defecto
      const profileAvatar = document.querySelector(".profile-avatar")
      profileAvatar.innerHTML = `
        <div class="default-avatar" id="default-avatar">
          <i class="fas fa-user"></i>
        </div>
        <div class="avatar-overlay">
          <label for="avatar-input" class="avatar-button">
            <i class="fas fa-camera"></i>
            AÑADIR FOTO
          </label>
          <input type="file" id="avatar-input" accept="image/*" style="display: none;">
        </div>
      `

      // Reconectar event listener
      const newAvatarInput = document.getElementById("avatar-input")
      newAvatarInput.addEventListener("change", avatarInput.onchange)
    }

    // Ocultar botones
    avatarSaveSection.style.display = "none"
    selectedFile = null

    // Limpiar input
    avatarInput.value = ""
  })

  // VALIDACIONES EN TIEMPO REAL

  // Validación de nombre de usuario
  if (usernameInput) {
    let usernameTimeout
    usernameInput.addEventListener("input", () => {
      clearTimeout(usernameTimeout)
      usernameTimeout = setTimeout(() => {
        validateField("username", usernameInput.value, usernameInput)
      }, 500)
    })
  }

  // Validación de email
  if (emailInput) {
    let emailTimeout
    emailInput.addEventListener("input", () => {
      clearTimeout(emailTimeout)
      emailTimeout = setTimeout(() => {
        validateField("email", emailInput.value, emailInput)
      }, 500)
    })
  }

  // Validación de contraseña actual
  if (currentPasswordInput) {
    let currentPasswordTimeout
    currentPasswordInput.addEventListener("input", () => {
      clearTimeout(currentPasswordTimeout)
      currentPasswordTimeout = setTimeout(() => {
        validateCurrentPassword(currentPasswordInput.value, currentPasswordInput)
      }, 500)
    })
  }

  // Validación de nueva contraseña
  if (newPasswordInput) {
    let newPasswordTimeout
    newPasswordInput.addEventListener("input", () => {
      clearTimeout(newPasswordTimeout)
      newPasswordTimeout = setTimeout(() => {
        validateNewPassword(newPasswordInput.value, newPasswordInput)
      }, 500)
    })
  }

  // Validación de confirmación de contraseña
  if (confirmPasswordInput) {
    let confirmPasswordTimeout
    confirmPasswordInput.addEventListener("input", () => {
      clearTimeout(confirmPasswordTimeout)
      confirmPasswordTimeout = setTimeout(() => {
        validateConfirmPassword(newPasswordInput.value, confirmPasswordInput.value, confirmPasswordInput)
      }, 500)
    })
  }

  // Email notifications toggle
  const emailNotifications = document.getElementById("email-notifications")
  emailNotifications.addEventListener("change", function () {
    console.log("📧 Cambiando notificaciones por email:", this.checked)

    fetch("/user/update-preferences/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        email_notifications: this.checked,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("✅ Respuesta email notifications:", data)
        if (data.status === "success") {
          showMessage(
            this.checked ? "Notificaciones por email activadas" : "Notificaciones por email desactivadas",
            "success",
          )
        }
      })
      .catch((error) => {
        console.error("❌ Error:", error)
      })
  })

  // Dark mode toggle
  const darkMode = document.getElementById("dark-mode")
  darkMode.addEventListener("change", function () {
    console.log("🌙 Cambiando modo oscuro:", this.checked)

    // Aplicar inmediatamente a toda la página
    document.documentElement.classList.toggle("dark-mode", this.checked)

    // Guardar en la base de datos
    fetch("/user/update-preferences/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        dark_mode: this.checked,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("✅ Respuesta dark mode:", data)
        if (data.status === "success") {
          showMessage(this.checked ? "Modo oscuro activado" : "Modo oscuro desactivado", "success")
        }
      })
      .catch((error) => {
        console.error("❌ Error:", error)
      })
  })

  // Language selection
  const languageSelect = document.getElementById("language-select")
  languageSelect.addEventListener("change", function () {
    console.log("🌍 Cambiando idioma a:", this.value)
    console.log("🔧 Texto seleccionado:", this.options[this.selectedIndex].text)

    // Validar que el idioma sea válido
    const idiomasValidos = ["es", "en", "de", "fr"]
    if (!idiomasValidos.includes(this.value)) {
      console.error("❌ Idioma no válido:", this.value)
      showMessage("Error: Idioma no válido", "error")
      return
    }

    // Mostrar mensaje de carga
    showMessage("Guardando idioma...", "info")

    fetch("/user/update-preferences/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        language: this.value,
      }),
    })
      .then((response) => {
        console.log("📡 Respuesta del servidor:", response.status)
        return response.json()
      })
      .then((data) => {
        console.log("✅ Respuesta cambio de idioma:", data)
        if (data.status === "success") {
          const textoIdioma = this.options[this.selectedIndex].text
          showMessage(`Idioma cambiado a ${textoIdioma}`, "success")
          console.log("🎉 Idioma guardado exitosamente en la base de datos")
        } else {
          console.error("❌ Error en la respuesta:", data)
          showMessage("Error al cambiar idioma", "error")
        }
      })
      .catch((error) => {
        console.error("❌ Error cambiando idioma:", error)
        showMessage("Error de conexión al cambiar idioma", "error")
      })
  })

  // Apply dark mode on load
  if (darkMode.checked) {
    document.documentElement.classList.add("dark-mode")
  }

  // NUEVA FUNCIÓN: Verificar datos del usuario (para debugging)
  window.verifyUserData = async () => {
    try {
      const response = await fetch("/user/verify-data/", {
        method: "GET",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })

      if (response.ok) {
        const data = await response.json()
        console.log("📊 Datos actuales del usuario:", data)
        return data
      }
    } catch (error) {
      console.error("Error verificando datos:", error)
    }
  }
})

// FUNCIONES DE VALIDACIÓN
async function validateField(fieldType, value, inputElement) {
  if (!value.trim()) {
    removeValidationMessage(inputElement)
    return
  }

  try {
    const response = await fetch(`/user/validate-${fieldType}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        [fieldType]: value,
      }),
    })

    const data = await response.json()
    showValidationMessage(inputElement, data.message, data.valid ? "success" : "error")
  } catch (error) {
    console.error(`Error validando ${fieldType}:`, error)
  }
}

async function validateCurrentPassword(password, inputElement) {
  if (!password.trim()) {
    removeValidationMessage(inputElement)
    return
  }

  try {
    const response = await fetch("/user/validate-current-password/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        current_password: password,
      }),
    })

    const data = await response.json()
    showValidationMessage(inputElement, data.message, data.valid ? "success" : "error")
  } catch (error) {
    console.error("Error validando contraseña actual:", error)
  }
}

async function validateNewPassword(password, inputElement) {
  if (!password.trim()) {
    removeValidationMessage(inputElement)
    return
  }

  try {
    const response = await fetch("/user/validate-new-password/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        new_password: password,
      }),
    })

    const data = await response.json()

    if (data.valid) {
      showValidationMessage(inputElement, data.message, "success")
    } else {
      let message = data.message
      if (data.errors && data.errors.length > 0) {
        message += "\n• " + data.errors.join("\n• ")
      }
      showValidationMessage(inputElement, message, "error")
    }
  } catch (error) {
    console.error("Error validando nueva contraseña:", error)
  }
}

async function validateConfirmPassword(newPassword, confirmPassword, inputElement) {
  if (!confirmPassword.trim()) {
    removeValidationMessage(inputElement)
    return
  }

  try {
    const response = await fetch("/user/validate-confirm-password/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    })

    const data = await response.json()
    showValidationMessage(inputElement, data.message, data.valid ? "success" : "error")
  } catch (error) {
    console.error("Error validando confirmación de contraseña:", error)
  }
}

function showValidationMessage(inputElement, message, type) {
  // Remover mensaje anterior si existe
  removeValidationMessage(inputElement)

  // Crear nuevo mensaje
  const messageDiv = document.createElement("div")
  messageDiv.className = `validation-message ${type}`
  messageDiv.textContent = message
  messageDiv.style.cssText = `
    color: ${type === "error" ? "#ef4444" : "#10b981"};
    font-size: 0.875rem;
    margin-top: 5px;
    font-weight: 500;
  `

  // Insertar después del input
  inputElement.parentNode.insertBefore(messageDiv, inputElement.nextSibling)
}

function removeValidationMessage(inputElement) {
  const existingMessage = inputElement.parentNode.querySelector(".validation-message")
  if (existingMessage) {
    existingMessage.remove()
  }
}

function getCookie(name) {
  let cookieValue = null
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";")
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

function showMessage(message, type) {
  // Crear elemento de mensaje
  const messageDiv = document.createElement("div")
  messageDiv.className = `message ${type}`

  let backgroundColor = ""
  switch (type) {
    case "success":
      backgroundColor = "background: linear-gradient(135deg, #10b981, #059669);"
      break
    case "error":
      backgroundColor = "background: linear-gradient(135deg, #ef4444, #dc2626);"
      break
    case "info":
      backgroundColor = "background: linear-gradient(135deg, #3b82f6, #2563eb);"
      break
    default:
      backgroundColor = "background: linear-gradient(135deg, #6b7280, #4b5563);"
  }

  messageDiv.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    z-index: 1000;
    animation: slideIn 0.3s ease-out;
    ${backgroundColor}
  `
  messageDiv.textContent = message

  // Agregar estilos de animación si no existen
  if (!document.getElementById("message-styles")) {
    const style = document.createElement("style")
    style.id = "message-styles"
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
    `
    document.head.appendChild(style)
  }

  document.body.appendChild(messageDiv)

  // Remover después de 3 segundos
  setTimeout(() => {
    messageDiv.remove()
  }, 3000)
}
