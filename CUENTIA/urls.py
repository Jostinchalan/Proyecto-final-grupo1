
# En CUENTIA/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from . import views
urlpatterns = [
    path('admin/', admin.site.urls),

    # Página de inicio pública (landing)
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),

    # Dashboard principal (requiere autenticación)
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Incluir URLs de las aplicaciones
    path('user/', include('user.urls')),
    path('stories/', include('stories.urls')),  # IMPORTANTE: stories debe estar antes que library
    path('library/', include('library.urls')),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug: Imprimir las URLs principales cargadas
print("URLs principales de CUENTIA cargadas:")
for pattern in urlpatterns:
    print(f"  - {pattern}")
