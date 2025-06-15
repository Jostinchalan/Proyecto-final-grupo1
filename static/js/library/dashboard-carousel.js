// Dashboard Carousel Functionality
const currentSlide = {
  recent: 0,
  popular: 0,
}

const slidesToShow = {
  recent: 3,
  popular: 4,
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("🎠 Dashboard carousel initialized")

  // Initialize carousels
  initializeCarousel("recent")
  initializeCarousel("popular")

  // Auto-scroll functionality
  setInterval(() => {
    autoSlide("recent")
    autoSlide("popular")
  }, 5000)
})

function initializeCarousel(type) {
  const carousel = document.getElementById(`${type}-carousel`)
  if (!carousel) return

  const cards = carousel.querySelectorAll(type === "recent" ? ".story-card" : ".popular-story-card")
  const totalCards = cards.length

  if (totalCards <= slidesToShow[type]) {
    // Hide navigation buttons if not enough cards
    const controls = carousel.closest(".section").querySelector(".controls")
    const navButtons = controls.querySelectorAll(".carousel-btn")
    navButtons.forEach((btn) => (btn.style.display = "none"))
    return
  }

  updateCarousel(type)
}

function nextSlide(type) {
  const carousel = document.getElementById(`${type}-carousel`)
  if (!carousel) return

  const cards = carousel.querySelectorAll(type === "recent" ? ".story-card" : ".popular-story-card")
  const totalCards = cards.length
  const maxSlide = Math.max(0, totalCards - slidesToShow[type])

  currentSlide[type] = Math.min(currentSlide[type] + 1, maxSlide)
  updateCarousel(type)
}

function prevSlide(type) {
  const carousel = document.getElementById(`${type}-carousel`)
  if (!carousel) return

  currentSlide[type] = Math.max(currentSlide[type] - 1, 0)
  updateCarousel(type)
}

function updateCarousel(type) {
  const carousel = document.getElementById(`${type}-carousel`)
  if (!carousel) return

  const container = carousel.querySelector(type === "recent" ? ".story-cards" : ".popular-stories")
  if (!container) return

  const cardWidth = type === "recent" ? 320 : 280 // Approximate card width + gap
  const translateX = -(currentSlide[type] * cardWidth)

  container.style.transform = `translateX(${translateX}px)`
  container.style.transition = "transform 0.3s ease-in-out"

  // Update button states
  updateNavigationButtons(type)
}

function updateNavigationButtons(type) {
  const section = document.getElementById(`${type}-carousel`).closest(".section")
  const prevBtn = section.querySelector(".prev")
  const nextBtn = section.querySelector(".next")

  if (!prevBtn || !nextBtn) return

  const carousel = document.getElementById(`${type}-carousel`)
  const cards = carousel.querySelectorAll(type === "recent" ? ".story-card" : ".popular-story-card")
  const totalCards = cards.length
  const maxSlide = Math.max(0, totalCards - slidesToShow[type])

  // Update button states
  prevBtn.disabled = currentSlide[type] === 0
  nextBtn.disabled = currentSlide[type] >= maxSlide

  prevBtn.style.opacity = prevBtn.disabled ? "0.5" : "1"
  nextBtn.style.opacity = nextBtn.disabled ? "0.5" : "1"
}

function autoSlide(type) {
  const carousel = document.getElementById(`${type}-carousel`)
  if (!carousel) return

  const cards = carousel.querySelectorAll(type === "recent" ? ".story-card" : ".popular-story-card")
  const totalCards = cards.length

  if (totalCards <= slidesToShow[type]) return

  const maxSlide = Math.max(0, totalCards - slidesToShow[type])

  if (currentSlide[type] >= maxSlide) {
    currentSlide[type] = 0
  } else {
    currentSlide[type]++
  }

  updateCarousel(type)
}

// Touch/swipe support for mobile
let startX = 0
let currentX = 0
let isDragging = false

document.addEventListener("touchstart", handleTouchStart, { passive: true })
document.addEventListener("touchmove", handleTouchMove, { passive: true })
document.addEventListener("touchend", handleTouchEnd, { passive: true })

function handleTouchStart(e) {
  const carousel = e.target.closest("#recent-carousel, #popular-carousel")
  if (!carousel) return

  startX = e.touches[0].clientX
  isDragging = true
}

function handleTouchMove(e) {
  if (!isDragging) return

  currentX = e.touches[0].clientX
}

function handleTouchEnd(e) {
  if (!isDragging) return

  const carousel = e.target.closest("#recent-carousel, #popular-carousel")
  if (!carousel) return

  const diffX = startX - currentX
  const threshold = 50

  if (Math.abs(diffX) > threshold) {
    const type = carousel.id.includes("recent") ? "recent" : "popular"

    if (diffX > 0) {
      nextSlide(type)
    } else {
      prevSlide(type)
    }
  }

  isDragging = false
}

// Keyboard navigation
document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") {
    prevSlide("recent")
  } else if (e.key === "ArrowRight") {
    nextSlide("recent")
  }
})

// Expose functions globally
window.nextSlide = nextSlide
window.prevSlide = prevSlide

console.log("✅ Dashboard carousel loaded successfully")

