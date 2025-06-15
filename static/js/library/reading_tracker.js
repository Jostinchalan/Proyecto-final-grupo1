let selectedProfileId = "all" // CAMBIO: Inicializar con "all" por defecto
let currentPeriod = "week"
let chartsData = {}
const d3 = window.d3

document.addEventListener("DOMContentLoaded", () => {
  initializeTracker()
  loadInitialData()
})

function initializeTracker() {
  // Configurar botones de período
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"))
      this.classList.add("active")
      currentPeriod = this.dataset.period
      loadChartData()
    })
  })

  // CAMBIO: Seleccionar perfil "Todos" por defecto
  selectProfile("all")
}

function selectProfile(profileId) {
  console.log(`👤 Seleccionando perfil: ${profileId}`)

  selectedProfileId = profileId

  // Actualizar UI
  document.querySelectorAll(".profile-circle").forEach((circle) => {
    circle.classList.remove("selected")
  })

  const selectedCircle = document.querySelector(`[data-profile-id="${profileId}"]`)
  if (selectedCircle) {
    selectedCircle.classList.add("selected")
    console.log(`✅ Perfil seleccionado visualmente: ${profileId}`)
  }

  // Cargar datos para este perfil
  loadChartData(profileId)
}

function loadInitialData() {
  // CAMBIO: Cargar datos iniciales con perfil "all" seleccionado
  loadChartData("all")
}

// FUNCIÓN CORREGIDA PARA CARGAR DATOS
function loadChartData(profileId = selectedProfileId) {
  console.log(`\n🔍 === CARGANDO DATOS ===`)
  console.log(`👤 Profile ID: ${profileId}`)
  console.log(`📅 Período: ${currentPeriod}`)

  showLoading(true)

  let url = `/library/reading-tracker/stats/`
  if (profileId && profileId !== "all") {
    url += `${profileId}/`
  }
  url += `?period=${currentPeriod}`

  console.log(`📡 URL: ${url}`)

  fetch(url, {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'Content-Type': 'application/json'
    }
  })
    .then((response) => {
      console.log(`📡 Status: ${response.status}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      console.log(`📊 DATOS RECIBIDOS:`, data)

      if (data.error) {
        throw new Error(data.error)
      }

      chartsData = data
      updateStats()
      createCharts()
      showLoading(false)

      console.log(`✅ ÉXITO: Datos cargados correctamente`)
      console.log(`=== FIN CARGA ===\n`)
    })
    .catch((error) => {
      console.error(`❌ ERROR:`, error)
      showNotification(`Error: ${error.message}`, "error")
      showLoading(false)
    })
}

// FUNCIÓN PARA PROBAR MANUALMENTE
function testAPI() {
  console.log("🧪 PROBANDO API...")
  fetch('/library/reading-tracker/stats/?period=week')
    .then(r => r.json())
    .then(data => {
      console.log("✅ API funciona:", data)
      if (data.total_stories > 0) {
        console.log("🎉 ¡HAY DATOS! Las estadísticas deberían funcionar")
      }
    })
    .catch(e => console.error("❌ API no funciona:", e))
}

// Ejecutar prueba al cargar la página
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(testAPI, 1000)
})

// FUNCIÓN MEJORADA PARA MOSTRAR ESTADÍSTICAS
function updateStats() {
  console.log("📊 Actualizando estadísticas con datos:", chartsData)

  // Actualizar estadísticas principales
  const totalStoriesEl = document.getElementById("total-stories")
  const readingTimeEl = document.getElementById("reading-time")
  const storiesPerWeekEl = document.getElementById("stories-per-week")
  const favoriteThemeEl = document.getElementById("favorite-theme")

  if (totalStoriesEl) totalStoriesEl.textContent = chartsData.total_stories || 0
  if (readingTimeEl) readingTimeEl.textContent = chartsData.total_reading_time || "0s"
  if (storiesPerWeekEl) storiesPerWeekEl.textContent = chartsData.stories_per_week || 0
  if (favoriteThemeEl) favoriteThemeEl.textContent = chartsData.favorite_theme || "Sin datos"

  // Actualizar cambios porcentuales
  const storiesChange = document.getElementById("stories-change")
  if (storiesChange) {
    const change = chartsData.stories_change || 0
    storiesChange.textContent = `${change > 0 ? "+" : ""}${change}% vs período anterior`
    storiesChange.className = `stat-change ${change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`
  }

  const timeChange = document.getElementById("time-change")
  if (timeChange) {
    const change = chartsData.time_change || 0
    timeChange.textContent = `${change > 0 ? "+" : ""}${change}% vs período anterior`
    timeChange.className = `stat-change ${change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`
  }

  const weeklyChange = document.getElementById("weekly-change")
  if (weeklyChange) weeklyChange.textContent = "Promedio semanal"

  const themeCount = document.getElementById("theme-count")
  if (themeCount) themeCount.textContent = `${chartsData.themes_explored || 0} temas diferentes`

  console.log("✅ Estadísticas actualizadas")
}

function createCharts() {
  createReadingActivityChart()
  createThemesDistributionChart()
  createReadingProgressChart()
}

function createReadingActivityChart() {
  const container = d3.select("#reading-activity-chart")
  container.selectAll("*").remove()

  if (!chartsData.activity_data || chartsData.activity_data.length === 0) {
    container.append("div").attr("class", "no-data").text("No hay datos disponibles")
    return
  }

  const data = chartsData.activity_data

  const margin = { top: 20, right: 30, bottom: 40, left: 40 }
  const width = container.node().getBoundingClientRect().width - margin.left - margin.right
  const height = 250 - margin.top - margin.bottom

  const svg = container
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`)

  // Escala X
  const x = d3
    .scaleBand()
    .domain(data.map((d) => d.date))
    .range([0, width])
    .padding(0.1)

  // Escala Y
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(data, (d) => d.stories) || 1])
    .range([height, 0])

  // Crear barras
  g.selectAll(".bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", (d) => x(d.date))
    .attr("width", x.bandwidth())
    .attr("y", (d) => y(d.stories))
    .attr("height", (d) => height - y(d.stories))
    .attr("fill", "#7C3AED")
    .on("mouseover", (event, d) => {
      showTooltip(event, `${d.stories} cuentos`)
    })
    .on("mouseout", hideTooltip)

  // Ejes
  g.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height})`)
    .call(
      d3.axisBottom(x).tickFormat((d) => {
        const date = new Date(d)
        return currentPeriod === "week"
          ? date.toLocaleDateString("es-ES", { weekday: "short" })
          : currentPeriod === "month"
            ? date.getDate()
            : date.toLocaleDateString("es-ES", { month: "short" })
      }),
    )

  g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5))
}

// FUNCIÓN MEJORADA PARA CREAR GRÁFICA DE DISTRIBUCIÓN DE TEMAS
function createThemesDistributionChart() {
  const container = d3.select("#themes-distribution-chart")
  container.selectAll("*").remove()

  if (!chartsData.theme_distribution || chartsData.theme_distribution.length === 0) {
    container.append("div")
      .attr("class", "no-data")
      .style("display", "flex")
      .style("align-items", "center")
      .style("justify-content", "center")
      .style("height", "200px")
      .style("color", "#6b7280")
      .style("font-style", "italic")
      .text("No hay datos disponibles")
    return
  }

  const data = chartsData.theme_distribution
  console.log("📊 Creando gráfica de temas con datos:", data)

  const width = container.node().getBoundingClientRect().width
  const height = 250
  const radius = Math.min(width, height) / 2 - 20

  const svg = container.append("svg").attr("width", width).attr("height", height)

  const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`)

  const color = d3
    .scaleOrdinal()
    .domain(data.map((d) => d.theme))
    .range(["#7e22ce", "#a855f7", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"])

  const pie = d3.pie().value((d) => d.count)

  const arc = d3.arc().innerRadius(0).outerRadius(radius)

  const arcs = g.selectAll(".pie-slice").data(pie(data)).enter().append("g").attr("class", "pie-slice")

  arcs
    .append("path")
    .attr("d", arc)
    .attr("fill", (d) => color(d.data.theme))
    .style("cursor", "pointer")
    .on("mouseover", (event, d) => {
      showTooltip(event, `${d.data.theme}: ${d.data.count} cuento${d.data.count !== 1 ? 's' : ''}`)
    })
    .on("mouseout", hideTooltip)

  // Etiquetas mejoradas
  arcs
    .append("text")
    .attr("transform", (d) => {
      const centroid = arc.centroid(d)
      // Mover las etiquetas un poco hacia afuera
      centroid[0] *= 1.4
      centroid[1] *= 1.4
      return `translate(${centroid})`
    })
    .attr("text-anchor", "middle")
    .attr("font-size", "11px")
    .attr("fill", "white")
    .attr("font-weight", "bold")
    .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.7)")
    .text((d) => (d.data.count > 0 ? d.data.count : ""))
}

function createReadingProgressChart() {
  const container = d3.select("#reading-progress-chart")
  container.selectAll("*").remove()

  if (!chartsData.reading_progress || chartsData.reading_progress.length === 0) {
    container.append("div").attr("class", "no-data").text("No hay datos disponibles")
    return
  }

  const data = chartsData.reading_progress

  const margin = { top: 20, right: 30, bottom: 40, left: 50 }
  const width = container.node().getBoundingClientRect().width - margin.left - margin.right
  const height = 250 - margin.top - margin.bottom

  const svg = container
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`)

  const parseDate = d3.timeParse("%Y-%m-%d")
  const formatDate = d3.timeFormat("%d/%m")

  data.forEach((d) => {
    d.date = parseDate(d.date)
  })

  const x = d3
    .scaleTime()
    .domain(d3.extent(data, (d) => d.date))
    .range([0, width])

  const y = d3
    .scaleLinear()
    .domain([0, d3.max(data, (d) => d.minutes) || 10])
    .range([height, 0])

  const line = d3
    .line()
    .x((d) => x(d.date))
    .y((d) => y(d.minutes))
    .curve(d3.curveMonotoneX)

  // Área bajo la línea
  const area = d3
    .area()
    .x((d) => x(d.date))
    .y0(height)
    .y1((d) => y(d.minutes))
    .curve(d3.curveMonotoneX)

  // Agregar área
  g.append("path").datum(data).attr("class", "area").attr("d", area).attr("fill", "rgba(124, 58, 237, 0.1)")

  // Línea
  g.append("path")
    .datum(data)
    .attr("class", "line")
    .attr("d", line)
    .attr("fill", "none")
    .attr("stroke", "#7C3AED")
    .attr("stroke-width", 3)

  // Puntos
  g.selectAll(".dot")
    .data(data)
    .enter()
    .append("circle")
    .attr("class", "dot")
    .attr("cx", (d) => x(d.date))
    .attr("cy", (d) => y(d.minutes))
    .attr("r", 4)
    .attr("fill", "#7C3AED")
    .on("mouseover", (event, d) => {
      showTooltip(event, `${d.minutes} minutos`)
    })
    .on("mouseout", hideTooltip)

  // Ejes
  g.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x).tickFormat(formatDate))

  g.append("g").attr("class", "axis").call(d3.axisLeft(y))
}

function showTooltip(event, text) {
  const tooltip = d3.select("body").append("div").attr("class", "tooltip").style("opacity", 0)

  tooltip.transition().duration(200).style("opacity", 0.9)

  tooltip
    .html(text)
    .style("left", event.pageX + 10 + "px")
    .style("top", event.pageY - 28 + "px")
}

function hideTooltip() {
  d3.selectAll(".tooltip").remove()
}

function exportReport() {
  // Obtener formato y período
  const format = "pdf" // Por defecto PDF
  const profileParam = selectedProfileId ? `&profile_id=${selectedProfileId}` : ""

  // URL para exportar
  const url = `/library/reading-tracker/export/?format=${format}&period=${currentPeriod}${profileParam}`

  // Mostrar notificación
  showNotification("Generando reporte completo...", "info")

  // Abrir en nueva ventana
  window.open(url, "_blank")
}

function showLoading(show) {
  // Implementar indicador de carga
  const charts = document.querySelectorAll(".chart-container")

  if (show) {
    charts.forEach((chart) => {
      chart.classList.add("loading")
      const loader = document.createElement("div")
      loader.className = "chart-loader"
      loader.innerHTML = '<div class="spinner"></div>'
      chart.appendChild(loader)
    })
  } else {
    charts.forEach((chart) => {
      chart.classList.remove("loading")
      const loader = chart.querySelector(".chart-loader")
      if (loader) {
        loader.remove()
      }
    })
  }
}

function showNotification(message, type = "info") {
  const notification = document.createElement("div")
  notification.className = `notification notification-${type}`
  notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `

  if (!document.getElementById("notification-styles")) {
    const styles = document.createElement("style")
    styles.id = "notification-styles"
    styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border-left: 4px solid #7e22ce;
                animation: slideInRight 0.3s ease;
                max-width: 300px;
            }
            .notification-success { border-left-color: #10b981; }
            .notification-error { border-left-color: #ef4444; }
            .notification-info { border-left-color: #3b82f6; }
            .notification-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 15px;
            }
            .notification-message {
                color: #374151;
                font-size: 14px;
                font-weight: 500;
            }
            .notification-close {
                background: none;
                border: none;
                color: #6b7280;
                font-size: 18px;
                cursor: pointer;
                margin-left: 10px;
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `
    document.head.appendChild(styles)
  }

  document.body.appendChild(notification)

  setTimeout(() => {
    if (notification.parentElement) {
      notification.remove()
    }
  }, 5000)
}

// Detener temporizador al abandonar la página
window.addEventListener("beforeunload", () => {
  if (window.stopReadingTimer) {
    window.stopReadingTimer()
  }
})

// Hacer las funciones globales para que puedan ser llamadas desde otros scripts
window.selectProfile = selectProfile