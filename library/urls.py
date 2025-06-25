from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Debug route - DEBE ESTAR PRIMERO
    path('debug/', views.debug_library_view, name='debug'),

    # Ruta principal de biblioteca
    path('', views.library_view, name='library'),
    path('delete/<int:story_id>/', views.delete_story, name='delete_story'),
    path('download/<int:story_id>/', views.download_library_story, name='download_story'),
    path('search/', views.search_stories_ajax, name='search_stories'),
    path('profile/<int:profile_id>/', views.filter_by_profile, name='filter_by_profile'),
    path('view/<int:story_id>/', views.view_library_story, name='view_story'),
    path('statistics/', views.library_statistics, name='statistics'),
    path('favorite/<int:story_id>/', views.toggle_library_favorite, name='toggle_favorite'),

    # Rutas para seguimiento lector
    path('reading-tracker/', views.reading_tracker_view, name='reading_tracker'),
    path('reading-tracker/stats/<int:profile_id>/', views.get_profile_stats, name='profile_stats'),
    path('reading-tracker/stats/', views.get_profile_stats, name='all_stats'),
    path('reading-tracker/export/', views.export_reading_report, name='export_report'),
    path('reading-tracker/update-time/', views.update_reading_time, name='update_reading_time'),

    # NUEVAS RUTAS AJAX PARA FILTROS DINÁMICOS
    path('ajax/themes-by-profile/', views.get_themes_by_profile, name='themes_by_profile'),
    path('ajax/search-titles/', views.search_titles_ajax, name='search_titles'),

]

# Debug: Imprimir las URLs de library cargadas
print("URLs de library cargadas:")
for pattern in urlpatterns:
    print(f"  - library/{pattern}")
