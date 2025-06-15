#stories/urls.py
from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    # Rutas principales
    path('generar/', views.generar_cuento_view, name='generar'),
    path('generando/', views.generando_cuento_view, name='generando'),
    path('cuento/<int:cuento_id>/', views.generated_story_view, name='generated_story'),

    # APIs y acciones
    path('cuento/<int:cuento_id>/status/', views.check_cuento_status, name='check_status'),
    path('cuento/<int:cuento_id>/contenido/', views.obtener_contenido_cuento, name='obtener_contenido'),
    path('cuento/<int:cuento_id>/favorito/', views.toggle_favorito_view, name='toggle_favorito'),
    path('cuento/<int:cuento_id>/guardar/', views.guardar_biblioteca_view, name='guardar_biblioteca'),
    path('cuento/<int:cuento_id>/eliminar/', views.eliminar_cuento, name='eliminar_cuento'),

    # DESCARGA PDF - CORREGIDA
    path('cuento/<int:cuento_id>/descargar/', views.descargar_pdf_view, name='descargar_pdf'),
]

# Debug: Imprimir las URLs cargadas
print("URLs de stories cargadas:")
for pattern in urlpatterns:
    print(f"  - stories/{pattern}")


