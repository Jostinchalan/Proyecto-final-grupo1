from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json
import logging

# Import models
from stories.models import Cuento, EstadisticaLectura
from user.models import Perfil
from .models import LibraryManager, CuentoEliminado

# Import utilities with error handling
try:
    from stories.utils import generar_pdf_cuento
except ImportError:
    generar_pdf_cuento = None

try:
    from .utils import get_reading_statistics, get_chart_data, generate_library_report
except ImportError:
    get_reading_statistics = None
    get_chart_data = None
    generate_library_report = None

# Get logger
logger = logging.getLogger(__name__)


@login_required
def export_reading_report(request):
    try:
        print(f"=== EXPORT_READING_REPORT ===")
        print(f"Usuario: {request.user.username}")
        print(f"Parámetros GET: {dict(request.GET)}")

        # Verificar que la función de generación esté disponible
        if not generate_library_report:
            logger.error("generate_library_report function not available")
            messages.error(request, 'Funcionalidad de exportación no disponible temporalmente.')
            return redirect('library:reading_tracker')

        # Obtener parámetros con valores por defecto seguros
        profile_id = request.GET.get('profile_id', 'all')
        period = request.GET.get('period', 'month')
        format_type = request.GET.get('format', 'pdf')

        print(f"Parámetros procesados:")
        print(f"  - Profile ID: {profile_id}")
        print(f"  - Period: {period}")
        print(f"  - Format: {format_type}")

        # Validar período
        valid_periods = ['week', 'month', 'year', 'all_time']
        if period not in valid_periods:
            logger.warning(f"Invalid period: {period}")
            period = 'month'

        # Obtener perfil si se especifica
        perfil = None
        if profile_id and profile_id != 'all':
            try:
                perfil = get_object_or_404(Perfil, id=profile_id, usuario=request.user)
                print(f"Perfil encontrado: {perfil.nombre}")
            except Exception as e:
                logger.error(f"Error getting profile {profile_id}: {e}")
                print(f"Error obteniendo perfil: {e}")
                perfil = None

        # Generar reporte según formato
        if format_type == 'pdf':
            try:
                print(f"Generando PDF...")

                # Generar PDF con manejo de errores robusto
                pdf_data = generate_library_report(request.user, perfil, period, 'pdf')

                # Verificar que el PDF no esté vacío
                if not pdf_data or len(pdf_data) == 0:
                    raise Exception("El PDF generado está vacío")

                # Verificar que sea realmente un PDF
                if not pdf_data.startswith(b'%PDF'):
                    raise Exception("Los datos generados no son un PDF válido")

                print(f"PDF generado exitosamente: {len(pdf_data)} bytes")

                # Crear respuesta HTTP
                response = HttpResponse(pdf_data, content_type='application/pdf')

                # Generar nombre de archivo
                profile_name = perfil.nombre if perfil else 'General'
                safe_profile_name = profile_name.replace(' ', '_').replace('/', '_')
                filename = f"CuentIA_Reporte_{period}_{safe_profile_name}_{timezone.now().strftime('%Y%m%d')}.pdf"

                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = len(pdf_data)

                logger.info(f"PDF report exported successfully for {request.user.username}")
                print(f"ÉXITO: Reporte PDF exportado")
                return response

            except Exception as e:
                logger.error(f"Error generating PDF: {str(e)}")
                print(f"ERROR PDF: {str(e)}")

                # Intentar generar un PDF de error
                try:
                    from reportlab.platypus import SimpleDocTemplate, Paragraph
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.lib.pagesizes import letter
                    from io import BytesIO

                    error_buffer = BytesIO()
                    doc = SimpleDocTemplate(error_buffer, pagesize=letter)
                    styles = getSampleStyleSheet()

                    story = [
                        Paragraph("Error al Generar Reporte", styles['Title']),
                        Paragraph(f"Se produjo un error: {str(e)}", styles['Normal']),
                        Paragraph("Por favor, intenta nuevamente o contacta al soporte técnico.", styles['Normal']),
                        Paragraph(f"Usuario: {request.user.username}", styles['Normal']),
                        Paragraph(f"Período: {period}", styles['Normal']),
                        Paragraph(f"Perfil: {perfil.nombre if perfil else 'General'}", styles['Normal']),
                        Paragraph(f"Fecha: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
                    ]

                    doc.build(story)
                    error_buffer.seek(0)
                    error_pdf = error_buffer.getvalue()

                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename="CuentIA_Error_Report.pdf"'
                    return response

                except Exception as pdf_error:
                    logger.error(f"Error creating error PDF: {pdf_error}")
                    messages.error(request, f'Error al generar el reporte: {str(e)}')
                    return redirect('library:reading_tracker')

        elif format_type == 'json':
            try:
                print(f"Generando JSON...")

                # Generar JSON
                json_data = generate_library_report(request.user, perfil, period, 'json')

                response = JsonResponse(json_data, safe=False)
                response['Content-Disposition'] = 'attachment; filename="reading_report.json"'

                logger.info(f"JSON report exported successfully for {request.user.username}")
                print(f"ÉXITO: Reporte JSON exportado")
                return response

            except Exception as e:
                logger.error(f"Error generating JSON: {str(e)}")
                print(f"ERROR JSON: {str(e)}")
                return JsonResponse({
                    'error': True,
                    'message': f'Error al generar reporte JSON: {str(e)}'
                }, status=500)

        else:
            logger.error(f"Unsupported format: {format_type}")
            messages.error(request, f'Formato no soportado: {format_type}')
            return redirect('library:reading_tracker')

    except Exception as e:
        logger.error(f"Critical error in export_reading_report: {str(e)}")
        print(f"ERROR CRÍTICO: {str(e)}")

        # Respuesta de error para AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': True,
                'message': f'Error crítico al exportar reporte: {str(e)}'
            }, status=500)

        # Respuesta de error para navegador
        messages.error(request, f'Error al exportar el reporte: {str(e)}')
        return redirect('library:reading_tracker')


# Mantener todas las demás vistas existentes...
@login_required
def library_view(request):
    try:
        print("Library view called")

        perfiles = Perfil.objects.filter(usuario=request.user).order_by('nombre')
        print(f"Found {perfiles.count()} profiles")

        # Get filters from URL - CORREGIDO
        filtros_actuales = {
            'perfil_id': request.GET.get('perfil', ''),  # Cambiar 'perfil' por 'perfil_id'
            'tema': request.GET.get('tema', ''),
            'titulo': request.GET.get('titulo', ''),
            'ordenar_por': request.GET.get('ordenar_por', 'fecha'),
        }

        print(f"Filtros actuales: {filtros_actuales}")

        # SOLO mostrar cuentos guardados en biblioteca
        cuentos = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).select_related('perfil')

        # Aplicar filtros adicionales
        perfil_seleccionado = None
        if filtros_actuales.get('perfil_id') and filtros_actuales['perfil_id'] != 'todos':
            try:
                perfil_id = int(filtros_actuales['perfil_id'])
                perfil_seleccionado = Perfil.objects.get(id=perfil_id, usuario=request.user)
                cuentos = cuentos.filter(perfil_id=perfil_id)
                print(f"Filtrado por perfil: {perfil_seleccionado.nombre}")
            except (ValueError, Perfil.DoesNotExist):
                print("Perfil no válido")

        if filtros_actuales.get('tema') and filtros_actuales['tema'] != 'todos':
            cuentos = cuentos.filter(tema=filtros_actuales['tema'])
            print(f"Filtrado por tema: {filtros_actuales['tema']}")

        if filtros_actuales.get('titulo'):
            cuentos = cuentos.filter(titulo__icontains=filtros_actuales['titulo'])
            print(f"Filtrado por título: {filtros_actuales['titulo']}")

        # Ordenar y filtrar
        ordenar_por = filtros_actuales.get('ordenar_por', 'fecha')
        if ordenar_por == 'fecha':
            cuentos = cuentos.order_by('-fecha_creacion')
        elif ordenar_por == 'dia':
            fecha_limite = timezone.now() - timedelta(days=1)
            cuentos = cuentos.filter(fecha_creacion__gte=fecha_limite).order_by('-fecha_creacion')
        elif ordenar_por == 'semana':
            fecha_limite = timezone.now() - timedelta(days=7)
            cuentos = cuentos.filter(fecha_creacion__gte=fecha_limite).order_by('-fecha_creacion')
        elif ordenar_por == 'mes':
            fecha_limite = timezone.now() - timedelta(days=30)
            cuentos = cuentos.filter(fecha_creacion__gte=fecha_limite).order_by('-fecha_creacion')
        elif ordenar_por == 'año':
            fecha_limite = timezone.now() - timedelta(days=365)
            cuentos = cuentos.filter(fecha_creacion__gte=fecha_limite).order_by('-fecha_creacion')
        elif ordenar_por == 'favoritos':
            # CORREGIDO: Filtrar solo cuentos marcados como favoritos
            cuentos = cuentos.filter(es_favorito=True).order_by('-fecha_creacion')
            print(f" Filtrando solo favoritos: {cuentos.count()} cuentos encontrados")
        else:
            cuentos = cuentos.order_by('-fecha_creacion')

        print(f"Found {cuentos.count()} stories after filters")

        # Si hay perfil seleccionado, obtener solo temas de ese perfil
        if perfil_seleccionado:
            temas_disponibles = Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True,
                perfil=perfil_seleccionado
            ).values_list('tema', flat=True).distinct().order_by('tema')
        else:
            temas_disponibles = Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True
            ).values_list('tema', flat=True).distinct().order_by('tema')

        print(f"Temas disponibles: {list(temas_disponibles)}")

        # Migración automática si es necesario
        total_cuentos_usuario = Cuento.objects.filter(usuario=request.user).count()
        cuentos_completados = Cuento.objects.filter(usuario=request.user, estado='completado').count()
        cuentos_en_biblioteca = Cuento.objects.filter(usuario=request.user, estado='completado',
                                                      en_biblioteca=True).count()

        if cuentos_completados > 0 and cuentos_en_biblioteca == 0:
            print("Migrando cuentos existentes a biblioteca...")
            migrated = Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=False
            ).update(en_biblioteca=True)
            print(f"{migrated} cuentos migrados automáticamente")

        # Pagination
        paginator = Paginator(cuentos, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get available titles for autocomplete
        all_titles = list(Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).values_list('titulo', flat=True))

        context = {
            'cuentos': page_obj,
            'perfiles': perfiles,
            'temas_disponibles': temas_disponibles,
            'filtros_actuales': filtros_actuales,
            'perfil_seleccionado': perfil_seleccionado,
            'total_cuentos': cuentos.count(),
            'titulos_disponibles': json.dumps(all_titles),
        }

        print("Rendering library template")
        logger.info(f"Library loaded for {request.user.username}: {cuentos.count()} stories")
        return render(request, 'library/library.html', context)

    except Exception as e:
        print(f"Error in library_view: {str(e)}")
        logger.error(f"Error in library_view: {str(e)}")
        messages.error(request, 'Error al cargar la biblioteca.')
        return redirect('dashboard')


@login_required
def reading_tracker_view(request):
    try:
        # Get user profiles
        perfiles = Perfil.objects.filter(usuario=request.user).order_by('nombre')

        print(f"Cargando seguimiento lector para {request.user.username}")
        print(f"Perfiles encontrados: {perfiles.count()}")

        # USAR SOLO ESTADÍSTICAS BÁSICAS PARA EVITAR ERROR DE PIPE
        # Calcular estadísticas directamente desde la base de datos
        from django.db import models
        from datetime import timedelta

        # Obtener cuentos del usuario en biblioteca
        total_cuentos = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).count()

        # Obtener estadísticas de lectura de la última semana
        fecha_limite = timezone.now() - timedelta(days=7)
        estadisticas_semana = EstadisticaLectura.objects.filter(
            usuario=request.user,
            fecha_lectura__gte=fecha_limite
        )

        # Calcular tiempo total de lectura
        tiempo_total_segundos = estadisticas_semana.aggregate(
            total=models.Sum('tiempo_lectura')
        )['total'] or 0

        # Formatear tiempo
        if tiempo_total_segundos >= 3600:
            horas = tiempo_total_segundos // 3600
            minutos = (tiempo_total_segundos % 3600) // 60
            tiempo_formateado = f"{horas}h {minutos}m"
        elif tiempo_total_segundos >= 60:
            minutos = tiempo_total_segundos // 60
            tiempo_formateado = f"{minutos}m"
        else:
            tiempo_formateado = f"{tiempo_total_segundos}s"

        # Calcular cuentos por semana
        cuentos_semana = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True,
            fecha_creacion__gte=fecha_limite
        ).count()

        # Obtener tema favorito
        tema_counts = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).values('tema').annotate(
            count=models.Count('id')
        ).order_by('-count')

        tema_favorito = "Sin datos"
        temas_explorados = 0

        if tema_counts:
            tema_favorito = tema_counts[0]['tema'].title() if tema_counts[0]['tema'] else "Sin datos"
            temas_explorados = len(tema_counts)

        print(f"Estadísticas calculadas: {total_cuentos} cuentos totales")
        print(f"Tiempo de lectura: {tiempo_formateado}")
        print(f"Tema favorito: {tema_favorito}")

        # Preparar contexto con datos seguros
        context = {
            'profiles': perfiles,
            'total_stories': total_cuentos,
            'reading_time': tiempo_formateado,
            'stories_per_week': cuentos_semana,
            'favorite_theme': tema_favorito,
            'themes_explored': temas_explorados,
            'stories_change': 0,  # Valor por defecto
            'time_change': 0,  # Valor por defecto
        }

        logger.info(f"Reading tracker loaded successfully for {request.user.username}")
        return render(request, 'library/reading_tracker.html', context)

    except Exception as e:
        print(f"Error en reading_tracker_view: {str(e)}")
        logger.error(f"Error in reading_tracker_view: {str(e)}")

        # En caso de error, mostrar datos básicos
        perfiles = Perfil.objects.filter(usuario=request.user).order_by('nombre')
        context = {
            'profiles': perfiles,
            'total_stories': 0,
            'reading_time': '0s',
            'stories_per_week': 0,
            'favorite_theme': 'Sin datos',
            'themes_explored': 0,
            'stories_change': 0,
            'time_change': 0,
        }

        messages.warning(request, 'Cargando vista básica del seguimiento lector.')
        return render(request, 'library/reading_tracker.html', context)


@login_required
def get_profile_stats(request, profile_id=None):
    """API para obtener estadísticas de un perfil específico - VERSIÓN FINAL CORREGIDA"""
    try:
        print(f"\n === GET_PROFILE_STATS DEBUG ===")
        print(f"Usuario logueado: {request.user.username}")
        print(f"Profile ID: {profile_id}")

        period = request.GET.get('period', 'week')
        print(f"Período: {period}")

        # CALCULAR ESTADÍSTICAS MANUALMENTE (más confiable)
        from django.db import models
        from datetime import timedelta, datetime, date
        from django.utils import timezone

        # Filtros base
        cuentos_filter = {
            'usuario': request.user,
            'estado': 'completado',
            'en_biblioteca': True
        }

        stats_filter = {'usuario': request.user}

        # Filtrar por perfil si se especifica
        perfil_obj = None
        if profile_id and profile_id != 'all':
            try:
                perfil_obj = get_object_or_404(Perfil, id=profile_id, usuario=request.user)
                cuentos_filter['perfil'] = perfil_obj
                stats_filter['perfil'] = perfil_obj
                print(f"Filtrando por perfil: {perfil_obj.nombre}")
            except:
                print(f"Perfil {profile_id} no encontrado")

        # Filtrar por período
        fecha_limite = None
        if period == 'week':
            fecha_limite = timezone.now() - timedelta(days=7)
        elif period == 'month':
            fecha_limite = timezone.now() - timedelta(days=30)
        elif period == 'year':
            fecha_limite = timezone.now() - timedelta(days=365)

        if fecha_limite:
            stats_filter['fecha_lectura__gte'] = fecha_limite
            # Para cuentos usamos fecha_creacion
            cuentos_filter['fecha_creacion__gte'] = fecha_limite

        print(f"Fecha límite: {fecha_limite}")

        # OBTENER DATOS
        cuentos = Cuento.objects.filter(**cuentos_filter)
        estadisticas = EstadisticaLectura.objects.filter(**stats_filter)

        total_cuentos = cuentos.count()
        total_tiempo_segundos = estadisticas.aggregate(
            total=models.Sum('tiempo_lectura')
        )['total'] or 0

        print(f"Cuentos encontrados: {total_cuentos}")
        print(f"Tiempo total: {total_tiempo_segundos} segundos")

        # Formatear tiempo
        if total_tiempo_segundos >= 3600:
            horas = total_tiempo_segundos // 3600
            minutos = (total_tiempo_segundos % 3600) // 60
            tiempo_formateado = f"{horas}h {minutos}m"
        elif total_tiempo_segundos >= 60:
            minutos = total_tiempo_segundos // 60
            segundos = total_tiempo_segundos % 60
            tiempo_formateado = f"{minutos}m {segundos}s"
        else:
            tiempo_formateado = f"{total_tiempo_segundos}s"

        # Cuentos por semana (promedio)
        if period == 'week':
            cuentos_por_semana = total_cuentos
        elif period == 'month':
            cuentos_por_semana = round(total_cuentos / 4.33, 1)
        else:  # year
            cuentos_por_semana = round(total_cuentos / 52, 1)

        # Tema favorito
        tema_counts = cuentos.values('tema').annotate(
            count=models.Count('id')
        ).order_by('-count')

        tema_favorito = "Sin datos"
        temas_explorados = 0

        if tema_counts:
            tema_favorito = tema_counts[0]['tema'].title()
            temas_explorados = len(tema_counts)

        print(f"Tema favorito: {tema_favorito}")
        print(f"Temas explorados: {temas_explorados}")

        # DATOS PARA GRÁFICAS - USAR FECHA DE CREACIÓN DE CUENTOS EN LUGAR DE ESTADÍSTICAS

        # 1. Actividad de lectura (últimos días) - CORREGIDO USANDO CUENTOS
        activity_data = []
        days_range = 7 if period == 'week' else (30 if period == 'month' else 365)

        if period == 'year':
            # Para año, usar meses
            for i in range(12):
                fecha = timezone.now().date() - timedelta(days=30 * i)
                month_start = fecha.replace(day=1)
                if i == 0:
                    month_end = timezone.now().date()
                else:
                    next_month = month_start.replace(
                        month=month_start.month + 1) if month_start.month < 12 else month_start.replace(
                        year=month_start.year + 1, month=1)
                    month_end = next_month - timedelta(days=1)

                # USAR FECHA DE CREACIÓN DE CUENTOS
                count = cuentos.filter(
                    fecha_creacion__date__gte=month_start,
                    fecha_creacion__date__lte=month_end
                ).count()

                activity_data.append({
                    'date': fecha.strftime('%Y-%m-%d'),
                    'stories': count
                })
            activity_data.reverse()
        else:
            # Para semana/mes, usar días - USAR FECHA DE CREACIÓN DE CUENTOS
            # Obtener la fecha actual en la zona horaria local
            ahora_local = timezone.localtime(timezone.now())
            hoy_local = ahora_local.date()
            print(f"Fecha actual local: {hoy_local}")
            print(f"Hora actual local: {ahora_local}")

            for i in range(min(days_range, 30)):
                fecha_objetivo = hoy_local - timedelta(days=i)
                print(f"Procesando fecha: {fecha_objetivo}")

                # CONTAR CUENTOS CREADOS EN ESA FECHA (usando fecha_creacion)
                count = 0
                cuentos_del_dia = []

                for cuento in cuentos:
                    # Convertir fecha_creacion a fecha local
                    fecha_creacion_local = timezone.localtime(cuento.fecha_creacion).date()
                    print(
                        f"Cuento '{cuento.titulo}' creado: {cuento.fecha_creacion} -> local: {fecha_creacion_local}")

                    if fecha_creacion_local == fecha_objetivo:
                        count += 1
                        cuentos_del_dia.append(cuento.titulo)

                print(f"Cuentos para {fecha_objetivo}: {count}")
                if cuentos_del_dia:
                    print(f"Títulos: {cuentos_del_dia}")

                activity_data.append({
                    'date': fecha_objetivo.strftime('%Y-%m-%d'),
                    'stories': count
                })

            activity_data.reverse()

        # 2. Distribución por temas
        theme_distribution = []
        for tema_data in tema_counts:
            if tema_data['count'] > 0:
                theme_distribution.append({
                    'theme': tema_data['tema'].title(),
                    'count': tema_data['count']
                })

        # 3. Progreso de lectura (tiempo por día) - MANTENER CON ESTADÍSTICAS
        reading_progress = []
        ahora_local = timezone.localtime(timezone.now())
        hoy_local = ahora_local.date()

        for i in range(min(days_range, 30)):
            fecha_objetivo = hoy_local - timedelta(days=i)

            # Calcular tiempo total para esa fecha usando estadísticas
            tiempo_total = 0
            for stat in estadisticas:
                fecha_stat = timezone.localtime(stat.fecha_lectura).date()
                if fecha_stat == fecha_objetivo:
                    tiempo_total += stat.tiempo_lectura or 0

            reading_progress.append({
                'date': fecha_objetivo.strftime('%Y-%m-%d'),
                'minutes': tiempo_total // 60,
                'seconds': tiempo_total
            })

        reading_progress.reverse()

        # RESPUESTA FINAL
        response_data = {
            'total_stories': total_cuentos,
            'total_reading_time': tiempo_formateado,
            'stories_per_week': cuentos_por_semana,
            'favorite_theme': tema_favorito,
            'themes_explored': temas_explorados,
            'stories_change': 10.5,  # Valor de ejemplo
            'time_change': 15.2,  # Valor de ejemplo
            'activity_data': activity_data,
            'theme_distribution': theme_distribution,
            'reading_progress': reading_progress
        }

        print(f"Enviando respuesta:")
        print(f"  - Total cuentos: {response_data['total_stories']}")
        print(f"  - Tiempo total: {response_data['total_reading_time']}")
        print(f"  - Tema favorito: {response_data['favorite_theme']}")
        print(f"  - Actividad: {len(activity_data)} puntos")
        print(f"  - Temas: {len(theme_distribution)} categorías")

        # Debug de activity_data
        print(f"Activity data:")
        for item in activity_data:
            print(f"  {item['date']}: {item['stories']} cuentos")

        print(f"=== FIN DEBUG ===\n")

        return JsonResponse(response_data)

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'error': 'Error al obtener estadísticas',
            'message': str(e),
            'total_stories': 0,
            'total_reading_time': '0s',
            'favorite_theme': 'Error'
        }, status=500)


# Resto de vistas existentes sin cambios...
@login_required
def view_library_story(request, story_id):
    try:
        story = get_object_or_404(
            Cuento,
            id=story_id,
            usuario=request.user,
            estado='completado',
            en_biblioteca=True  # Solo cuentos en biblioteca
        )

        # Mark as read if the method exists
        if hasattr(story, 'marcar_como_leido'):
            story.marcar_como_leido()

        # Register reading statistic from library with profile
        EstadisticaLectura.objects.create(
            usuario=request.user,
            cuento=story,
            perfil=story.perfil,
            tipo_lectura='biblioteca'
        )

        logger.info(f"Story viewed from library: {story.titulo} by {request.user.username}")

        # Redirect to existing generated story view
        return redirect('stories:generated_story', cuento_id=story.id)

    except Exception as e:
        logger.error(f"Error viewing story from library: {str(e)}")
        messages.error(request, 'Error al cargar el cuento.')
        return redirect('library:library')


@login_required
def update_reading_time(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        cuento_id = data.get('cuento_id')
        tiempo_lectura = data.get('tiempo_lectura', 0)  # en segundos
        profile_id = data.get('profile_id')  # ID del perfil específico

        if not cuento_id or tiempo_lectura <= 0:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)

        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        # Obtener el perfil correcto
        perfil = None
        if profile_id and profile_id != 'all':
            try:
                perfil = Perfil.objects.get(id=profile_id, usuario=request.user)
            except Perfil.DoesNotExist:
                pass

        # Si no se proporciona perfil, usar el del cuento
        if not perfil and cuento.perfil:
            perfil = cuento.perfil

        # Buscar estadística existente para hoy y este perfil
        hoy = timezone.now().date()
        estadistica = EstadisticaLectura.objects.filter(
            usuario=request.user,
            cuento=cuento,
            perfil=perfil,  # Incluir perfil en la búsqueda
            fecha_lectura__date=hoy
        ).first()

        if estadistica:
            # Actualizar estadística existente (acumular tiempo)
            estadistica.tiempo_lectura += tiempo_lectura
            estadistica.save()
            tiempo_total = estadistica.tiempo_lectura
        else:
            # Crear nueva estadística
            estadistica = EstadisticaLectura.objects.create(
                usuario=request.user,
                cuento=cuento,
                perfil=perfil,  # Incluir perfil
                tiempo_lectura=tiempo_lectura,
                tipo_lectura='texto',
                fecha_lectura=timezone.now()
            )
            tiempo_total = tiempo_lectura

        # Incrementar contador de veces leído
        if hasattr(cuento, 'veces_leido'):
            # Solo incrementar si es una nueva sesión (más de 10 segundos)
            if tiempo_lectura >= 10:
                cuento.veces_leido += 1
                cuento.save(update_fields=['veces_leido'])

        # Formatear tiempo para respuesta
        total_hours = tiempo_total // 3600
        total_minutes = (tiempo_total % 3600) // 60
        total_seconds = tiempo_total % 60

        if total_hours > 0:
            tiempo_formateado = f"{total_hours}h {total_minutes}m {total_seconds}s"
        elif total_minutes > 0:
            tiempo_formateado = f"{total_minutes}m {total_seconds}s"
        else:
            tiempo_formateado = f"{total_seconds}s"

        return JsonResponse({
            'success': True,
            'message': 'Tiempo de lectura actualizado',
            'tiempo_lectura': tiempo_lectura,
            'tiempo_total': tiempo_total,
            'tiempo_formateado': tiempo_formateado,
            'perfil_nombre': perfil.nombre if perfil else 'Sin perfil'
        })

    except Exception as e:
        logger.error(f"Error updating reading time: {str(e)}")
        return JsonResponse({
            'error': 'Error al actualizar tiempo de lectura',
            'message': str(e)
        }, status=500)


# Resto de las vistas existentes sin cambios...
@login_required
def debug_library_view(request):
    return HttpResponse("Library debug view is working! User: " + str(request.user.username))


@login_required
@require_POST
def delete_story(request, story_id):
    try:
        story = get_object_or_404(
            Cuento,
            id=story_id,
            usuario=request.user,
            estado='completado'
        )
        title = story.titulo

        print(f"ELIMINANDO DESDE LIBRARY: {story.titulo} (ID: {story.id})")

        # NUEVO: Registrar en auditoría ANTES de eliminar
        try:
            cuento_eliminado = LibraryManager.registrar_cuento_eliminado(
                cuento=story,
                usuario=request.user,
                request=request,
                motivo='usuario'
            )

            if cuento_eliminado:
                logger.info(f"Cuento registrado en auditoría: {story.titulo} (ID: {story.id})")
                print(f"AUDITORÍA: Cuento '{story.titulo}' registrado correctamente")
            else:
                logger.warning(f"No se pudo registrar en auditoría: {story.titulo} (ID: {story.id})")
                print(f"AUDITORÍA: Error registrando '{story.titulo}'")

        except Exception as audit_error:
            logger.error(f"Error en auditoría para cuento {story.id}: {audit_error}")
            print(f"AUDITORÍA: Error - {audit_error}")
            # Continuar con la eliminación aunque falle la auditoría
        EstadisticaLectura.objects.filter(cuento=story).delete()

        story.delete()

        logger.info(f"Cuento eliminado: {title} (ID: {story_id}) por usuario {request.user.username}")
        print(f"ELIMINACIÓN: '{title}' eliminado correctamente")

        return JsonResponse({
            'success': True,
            'message': f'Cuento "{title}" eliminado exitosamente de tu biblioteca'
        })

    except Exception as e:
        logger.error(f"Error deleting story from library: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error al eliminar el cuento de la biblioteca'
        })


@login_required
def download_library_story(request, story_id):
    try:
        story = get_object_or_404(
            Cuento,
            id=story_id,
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        )

        logger.info(f"Descargando PDF desde biblioteca: {story.titulo}")
        pdf_buffer = generar_pdf_cuento(story)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"CuentIA_{story.titulo.replace(' ', '_').replace('/', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_buffer.getvalue())

        # Register download statistic with profile
        EstadisticaLectura.objects.create(
            usuario=request.user,
            cuento=story,
            perfil=story.perfil,
            tipo_lectura='descarga'
        )

        logger.info(f"PDF descargado desde biblioteca: {story.titulo}")
        return response

    except Exception as e:
        logger.error(f"Error generating PDF from library: {str(e)}")
        messages.error(request, 'Error al generar el PDF.')
        return redirect('library:library')


@login_required
def search_stories_ajax(request):
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'stories': []})

    try:
        stories = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True,
            titulo__icontains=query
        ).select_related('perfil')[:10]

        results = []
        for story in stories:
            results.append({
                'id': story.id,
                'title': story.titulo,
                'character': story.personaje_principal,
                'theme': story.get_tema_display() if hasattr(story, 'get_tema_display') else story.tema,
                'profile': story.perfil.nombre if story.perfil else 'Sin perfil',
                'date': story.fecha_creacion.strftime('%d/%m/%Y'),
                'times_read': getattr(story, 'veces_leido', 0),
            })

        return JsonResponse({'stories': results})
    except Exception as e:
        logger.error(f"Error in AJAX search: {str(e)}")
        return JsonResponse({'stories': [], 'error': 'Error en la búsqueda'})


@login_required
def filter_by_profile(request, profile_id):
    try:
        profile = get_object_or_404(Perfil, id=profile_id, usuario=request.user)

        stories = Cuento.objects.filter(
            usuario=request.user,
            perfil=profile,
            estado='completado',
            en_biblioteca=True
        ).order_by('-fecha_creacion')

        if not stories.exists():
            messages.info(request, f'El perfil "{profile.nombre}" no tiene cuentos guardados en la biblioteca.')

        paginator = Paginator(stories, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'cuentos': page_obj,
            'perfil_seleccionado': profile,
            'perfiles': Perfil.objects.filter(usuario=request.user),
            'temas_disponibles': Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True
            ).values_list('tema', flat=True).distinct().order_by('tema'),
            'years': [date.year for date in Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True
            ).dates('fecha_creacion', 'year', order='DESC')],
            'filtros_actuales': {'perfil': str(profile_id)},
            'total_cuentos': stories.count(),
        }

        return render(request, 'library/library.html', context)

    except Exception as e:
        logger.error(f"Error filtering by profile: {str(e)}")
        messages.error(request, 'Error al filtrar por perfil.')
        return redirect('library:library')


@login_required
def library_statistics(request):
    try:
        statistics = LibraryManager.get_library_statistics(request.user)
        popular_stories = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).order_by('-veces_leido')[:5] if hasattr(Cuento, 'veces_leido') else []

        recent_activity = EstadisticaLectura.objects.filter(
            usuario=request.user
        ).select_related('cuento').order_by('-fecha_lectura')[:10]

        context = {
            'statistics': statistics,
            'popular_stories': popular_stories,
            'recent_activity': recent_activity,
        }

        return render(request, 'library/statistics.html', context)

    except Exception as e:
        logger.error(f"Error in statistics: {str(e)}")
        messages.error(request, 'Error al cargar las estadísticas.')
        return redirect('library:library')


@login_required
@require_POST
def toggle_library_favorite(request, story_id):
    try:
        story = get_object_or_404(
            Cuento,
            id=story_id,
            usuario=request.user,
            estado='completado'
        )

        # Toggle favorite
        if hasattr(story, 'toggle_favorito'):
            is_favorite = story.toggle_favorito()
        elif hasattr(story, 'es_favorito'):
            story.es_favorito = not story.es_favorito
            story.save()
            is_favorite = story.es_favorito
        else:
            is_favorite = False

        logger.info(f"Favorite {'added' if is_favorite else 'removed'}: {story.titulo}")

        return JsonResponse({
            'success': True,
            'is_favorite': is_favorite,
            'message': 'Agregado a favoritos' if is_favorite else 'Removido de favoritos'
        })

    except Exception as e:
        logger.error(f"Error toggle favorite in library: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error al actualizar favorito'
        })


# filtros de busqueda
@login_required
def get_themes_by_profile(request):
    profile_id = request.GET.get('profile_id')

    try:
        if profile_id and profile_id != 'todos':
            # Obtener temas solo del perfil seleccionado
            temas = Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True,
                perfil_id=profile_id
            ).values_list('tema', flat=True).distinct().order_by('tema')
        else:
            # Obtener todos los temas del usuario
            temas = Cuento.objects.filter(
                usuario=request.user,
                estado='completado',
                en_biblioteca=True
            ).values_list('tema', flat=True).distinct().order_by('tema')

        # Filtrar temas vacíos o None
        temas_filtrados = [tema for tema in temas if tema and tema.strip()]

        return JsonResponse({
            'success': True,
            'temas': temas_filtrados
        })

    except Exception as e:
        logger.error(f"Error getting themes by profile: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def search_titles_ajax(request):
    query = request.GET.get('q', '').strip()
    profile_id = request.GET.get('profile_id')
    theme = request.GET.get('theme')

    if len(query) < 1:
        return JsonResponse({'titles': []})

    try:
        # Construir queryset base
        queryset = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True,
            titulo__icontains=query
        )

        # Aplicar filtros adicionales si están presentes
        if profile_id and profile_id != 'todos':
            queryset = queryset.filter(perfil_id=profile_id)

        if theme and theme != 'todos':
            queryset = queryset.filter(tema=theme)

        # Obtener títulos únicos
        titles = list(queryset.values_list('titulo', flat=True).distinct()[:10])

        return JsonResponse({
            'success': True,
            'titles': titles
        })

    except Exception as e:
        logger.error(f"Error in title search: {str(e)}")
        return JsonResponse({
            'success': False,
            'titles': [],
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def eliminar_cuento_con_auditoria(request, cuento_id):
    try:
        from stories.models import Cuento

        # Obtener el cuento
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        # Registrar en auditoría ANTES de eliminar
        cuento_eliminado = LibraryManager.registrar_cuento_eliminado(
            cuento=cuento,
            usuario=request.user,
            request=request,
            motivo='usuario'
        )

        if cuento_eliminado:
            logger.info(f"Cuento registrado en auditoría: {cuento.titulo}")
        else:
            logger.warning(f"No se pudo registrar en auditoría: {cuento.titulo}")

        # Eliminar el cuento
        titulo_eliminado = cuento.titulo
        cuento.delete()

        logger.info(f"Cuento eliminado: {titulo_eliminado} (ID: {cuento_id}) por usuario {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': f'Cuento "{titulo_eliminado}" eliminado correctamente',
            'cuento_id': cuento_id
        })

    except Cuento.DoesNotExist:
        logger.warning(f"Intento de eliminar cuento inexistente: {cuento_id}")
        return JsonResponse({
            'success': False,
            'error': 'Cuento no encontrado'
        }, status=404)

    except Exception as e:
        logger.error(f"Error eliminando cuento {cuento_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar cuento: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def estadisticas_cuentos_eliminados(request):
    try:
        # Parámetros
        time_period = request.GET.get('period', 'month')
        profile_id = request.GET.get('profile_id')

        # Obtener rango de fechas
        from .utils import get_time_range_ecuador
        start_date, end_date = get_time_range_ecuador(time_period)

        # Filtros base
        queryset = CuentoEliminado.objects.filter(usuario=request.user)

        if start_date:
            queryset = queryset.filter(fecha_eliminacion__gte=start_date)

        if profile_id and profile_id != 'all':
            queryset = queryset.filter(perfil_id=profile_id)

        # Obtener estadísticas
        cuentos_eliminados = queryset.order_by('-fecha_eliminacion')

        # Preparar datos para respuesta
        eliminados_data = []
        for cuento in cuentos_eliminados[:10]:  # Máximo 10 para el reporte
            eliminados_data.append({
                'titulo': cuento.titulo,
                'fecha_eliminacion': cuento.fecha_eliminacion.strftime('%d de %B de %Y'),
                'personaje': cuento.personaje_principal or 'Sin personaje',
                'tema': cuento.tema_display,
                'perfil': cuento.perfil.nombre if cuento.perfil else 'Sin perfil'
            })

        return JsonResponse({
            'success': True,
            'total_eliminados': cuentos_eliminados.count(),
            'cuentos_eliminados': eliminados_data
        })

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de eliminados: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def eliminar_cuento(request, cuento_id):
    try:
        from .models import Cuento

        # Obtener el cuento
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        print(f"ELIMINANDO: {cuento.titulo} (ID: {cuento.id})")

        # NUEVO: Registrar en auditoría ANTES de eliminar
        try:
            from library.models import LibraryManager

            cuento_eliminado = LibraryManager.registrar_cuento_eliminado(
                cuento=cuento,
                usuario=request.user,
                request=request,
                motivo='usuario'
            )

            if cuento_eliminado:
                logger.info(f"Cuento registrado en auditoría: {cuento.titulo} (ID: {cuento.id})")
                print(f"AUDITORÍA: Cuento '{cuento.titulo}' registrado correctamente")
            else:
                logger.warning(f"⚠️ No se pudo registrar en auditoría: {cuento.titulo} (ID: {cuento.id})")
                print(f"AUDITORÍA: Error registrando '{cuento.titulo}'")

        except Exception as audit_error:
            logger.error(f"Error en auditoría para cuento {cuento.id}: {audit_error}")
            print(f"AUDITORÍA: Error - {audit_error}")
            # Continuar con la eliminación aunque falle la auditoría

        # Eliminar el cuento
        titulo_eliminado = cuento.titulo
        cuento.delete()

        logger.info(f"Cuento eliminado: {titulo_eliminado} (ID: {cuento_id}) por usuario {request.user.username}")
        print(f"ELIMINACIÓN: '{titulo_eliminado}' eliminado correctamente")

        return JsonResponse({
            'success': True,
            'message': f'Cuento "{titulo_eliminado}" eliminado correctamente',
            'cuento_id': cuento_id
        })

    except Cuento.DoesNotExist:
        logger.warning(f"Intento de eliminar cuento inexistente: {cuento_id}")
        return JsonResponse({
            'success': False,
            'error': 'Cuento no encontrado'
        }, status=404)

    except Exception as e:
        logger.error(f"Error eliminando cuento {cuento_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar cuento: {str(e)}'
        }, status=500)
