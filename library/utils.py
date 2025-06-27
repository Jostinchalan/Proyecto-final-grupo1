from django.utils import timezone
from datetime import timedelta, datetime, date
from django.db.models import Count, Sum, Avg, Q
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from io import BytesIO
import logging
import pytz
from stories.models import Cuento, EstadisticaLectura
from user.models import Perfil

logger = logging.getLogger(__name__)


def get_ecuador_time():
    try:
        ecuador_tz = pytz.timezone('America/Guayaquil')
        utc_now = timezone.now()
        ecuador_time = utc_now.astimezone(ecuador_tz)
        return ecuador_time
    except Exception as e:
        logger.error(f"Error getting Ecuador time: {e}")
        return timezone.now()


def format_ecuador_datetime(dt=None, include_time=True):
    try:
        if dt is None:
            dt = get_ecuador_time()
        elif timezone.is_aware(dt):
            ecuador_tz = pytz.timezone('America/Guayaquil')
            dt = dt.astimezone(ecuador_tz)

        # Nombres de meses en español
        meses = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }

        if include_time:
            return f"{dt.day} de {meses[dt.month]} de {dt.year} a las {dt.strftime('%H:%M')}"
        else:
            return f"{dt.day} de {meses[dt.month]} de {dt.year}"
    except Exception as e:
        logger.error(f"Error formatting Ecuador datetime: {e}")
        return str(dt) if dt else "Fecha no disponible"


def get_time_range_ecuador(time_period):
    try:
        now_ecuador = get_ecuador_time()

        if time_period == 'week':
            start_date = now_ecuador - timedelta(days=7)
        elif time_period == 'month':
            start_date = now_ecuador - timedelta(days=30)
        elif time_period == 'year':
            # CORREGIDO: Usar 365 días exactos para evitar problemas
            start_date = now_ecuador - timedelta(days=365)
        else:  # 'all_time'
            start_date = None

        return start_date, now_ecuador
    except Exception as e:
        logger.error(f"Error getting time range: {e}")
        # Fallback seguro
        now = timezone.now()
        if time_period == 'year':
            start_date = now - timedelta(days=365)
        elif time_period == 'month':
            start_date = now - timedelta(days=30)
        elif time_period == 'week':
            start_date = now - timedelta(days=7)
        else:
            start_date = None
        return start_date, now


def get_reading_statistics(user, perfil=None, time_period='week'):
    try:
        start_date, end_date = get_time_range_ecuador(time_period)

        print(f"Calculando estadísticas para período: {time_period}")
        print(f"Rango de fechas: {start_date} - {end_date}")

        # Filtros base con manejo de errores
        sessions_filter = Q(usuario=user)
        stories_filter = Q(usuario=user, estado='completado', en_biblioteca=True)

        if perfil:
            sessions_filter &= Q(perfil=perfil)
            stories_filter &= Q(perfil=perfil)
            print(f"Filtrando por perfil: {perfil.nombre}")

        if start_date:
            sessions_filter &= Q(fecha_lectura__gte=start_date)
            stories_filter &= Q(fecha_creacion__gte=start_date)

        # Obtener datos con manejo de errores
        try:
            sessions = EstadisticaLectura.objects.filter(sessions_filter)
            stories = Cuento.objects.filter(stories_filter)
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            sessions = EstadisticaLectura.objects.none()
            stories = Cuento.objects.none()

        print(f"Cuentos encontrados: {stories.count()}")
        print(f"Sesiones de lectura: {sessions.count()}")

        total_stories = stories.count()

        # Calcular tiempo total con manejo de errores
        try:
            total_reading_time_seconds = sessions.aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0
        except Exception as e:
            logger.error(f"Error calculating reading time: {e}")
            total_reading_time_seconds = 0

        # Formatear tiempo de manera segura
        try:
            total_hours = total_reading_time_seconds // 3600
            total_minutes = (total_reading_time_seconds % 3600) // 60
            total_seconds_remainder = total_reading_time_seconds % 60

            if total_hours > 0:
                time_display = f"{total_hours}h {total_minutes}m"
            elif total_minutes > 0:
                time_display = f"{total_minutes}m {total_seconds_remainder}s"
            else:
                time_display = f"{total_seconds_remainder}s"
        except Exception as e:
            logger.error(f"Error formatting time: {e}")
            time_display = "0s"

        # Calcular cuentos por semana de manera segura
        try:
            if time_period == 'week':
                stories_per_week = total_stories
            elif time_period == 'month':
                stories_per_week = round(total_stories / 4.33, 1) if total_stories > 0 else 0
            else:  # year
                stories_per_week = round(total_stories / 52, 1) if total_stories > 0 else 0
        except Exception as e:
            logger.error(f"Error calculating stories per week: {e}")
            stories_per_week = 0

        # Obtener temas con manejo de errores
        try:
            theme_counts = stories.values('tema').annotate(
                count=Count('id')
            ).order_by('-count')
            themes_explored = len(theme_counts)
        except Exception as e:
            logger.error(f"Error getting themes: {e}")
            theme_counts = []
            themes_explored = 0

        # Tema favorito con manejo de errores
        favorite_theme_name = "Sin datos"
        try:
            favorite_theme = theme_counts.first()
            if favorite_theme and favorite_theme['count'] > 0:
                theme_code = favorite_theme['tema']
                try:
                    for choice in Cuento.TEMA_CHOICES:
                        if choice[0] == theme_code:
                            favorite_theme_name = choice[1]
                            break
                    if favorite_theme_name == "Sin datos":
                        favorite_theme_name = theme_code.title() if theme_code else "Sin datos"
                except:
                    favorite_theme_name = theme_code.title() if theme_code else "Sin datos"
        except Exception as e:
            logger.error(f"Error getting favorite theme: {e}")

        # Calcular cambios con manejo de errores
        stories_change = 0
        time_change = 0

        try:
            if start_date:
                period_duration = end_date - start_date
                prev_start = start_date - period_duration
                prev_sessions_filter = Q(usuario=user, fecha_lectura__gte=prev_start, fecha_lectura__lt=start_date)
                prev_stories_filter = Q(usuario=user, estado='completado', en_biblioteca=True,
                                        fecha_creacion__gte=prev_start, fecha_creacion__lt=start_date)

                if perfil:
                    prev_sessions_filter &= Q(perfil=perfil)
                    prev_stories_filter &= Q(perfil=perfil)

                prev_sessions = EstadisticaLectura.objects.filter(prev_sessions_filter)
                prev_stories_count = Cuento.objects.filter(prev_stories_filter).count()
                prev_time = prev_sessions.aggregate(total=Sum('tiempo_lectura'))['total'] or 0

                if prev_stories_count > 0:
                    stories_change = ((total_stories - prev_stories_count) / prev_stories_count) * 100
                elif total_stories > 0:
                    stories_change = 100

                if prev_time > 0:
                    time_change = ((total_reading_time_seconds - prev_time) / prev_time) * 100
                elif total_reading_time_seconds > 0:
                    time_change = 100
        except Exception as e:
            logger.error(f"Error calculating changes: {e}")

        # Promedio de sesión con manejo de errores
        try:
            average_session_time = sessions.aggregate(avg=Avg('tiempo_lectura'))['avg'] or 0
        except Exception as e:
            logger.error(f"Error calculating average session time: {e}")
            average_session_time = 0

        result = {
            'total_stories': total_stories,
            'total_reading_time': time_display,
            'total_reading_time_seconds': total_reading_time_seconds,
            'stories_per_week': stories_per_week,
            'themes_explored': themes_explored,
            'favorite_theme': favorite_theme_name,
            'stories_change': round(stories_change, 1),
            'time_change': round(time_change, 1),
            'average_session_time': average_session_time,
            'period_start': start_date,
            'period_end': end_date,
            'theme_distribution': list(theme_counts[:10])
        }

        print(f"Estadísticas calculadas: {result}")
        return result

    except Exception as e:
        logger.error(f"Critical error in get_reading_statistics: {e}")
        # Retornar datos por defecto en caso de error crítico
        return {
            'total_stories': 0,
            'total_reading_time': '0s',
            'total_reading_time_seconds': 0,
            'stories_per_week': 0,
            'themes_explored': 0,
            'favorite_theme': 'Error',
            'stories_change': 0,
            'time_change': 0,
            'average_session_time': 0,
            'period_start': None,
            'period_end': timezone.now(),
            'theme_distribution': []
        }


def get_chart_data(user, perfil=None, time_period='week'):
    try:
        start_date, end_date = get_time_range_ecuador(time_period)

        print(f"Generando datos de gráficas para período: {time_period}")

        base_filter = Q(usuario=user)
        if perfil:
            base_filter &= Q(perfil=perfil)
            print(f"Filtrando gráficas por perfil: {perfil.nombre}")
        if start_date:
            base_filter &= Q(fecha_lectura__gte=start_date)

        activity_data = []

        # Determinar rango de días de manera segura
        if time_period == 'week':
            days_range = 7
        elif time_period == 'month':
            days_range = 30
        else:  # year
            days_range = 12  # Para año usamos meses

        # Generar datos de actividad con manejo de errores
        try:
            if time_period == 'year':
                # Para año, usar meses - CORREGIDO
                ecuador_now = get_ecuador_time()
                months_data = {}

                for i in range(12):
                    try:
                        current_date = ecuador_now.date()
                        # Calcular fecha del mes
                        if i == 0:
                            month_date = current_date
                        else:
                            # Restar meses de manera segura
                            year = current_date.year
                            month = current_date.month - i

                            while month <= 0:
                                month += 12
                                year -= 1

                            month_date = date(year, month, 1)

                        month_key = month_date.strftime('%Y-%m')
                        months_data[month_key] = {
                            'month': month_date.strftime('%b'),
                            'date': month_date.strftime('%Y-%m-%d'),
                            'stories': 0
                        }
                    except Exception as e:
                        logger.error(f"Error processing month {i}: {e}")
                        continue

                # Obtener conteos por mes con manejo de errores
                try:
                    month_counts = EstadisticaLectura.objects.filter(base_filter).extra(
                        select={'month': "to_char(fecha_lectura, 'YYYY-MM')"}
                    ).values('month').annotate(count=Count('cuento', distinct=True))

                    for item in month_counts:
                        if item['month'] in months_data:
                            months_data[item['month']]['stories'] = item['count']
                except Exception as e:
                    logger.error(f"Error getting month counts: {e}")

                activity_data = list(months_data.values())
                activity_data.reverse()

            else:
                # Para semana/mes, usar días - CORREGIDO
                ecuador_now = get_ecuador_time()
                for i in range(min(days_range, 30)):  # Limitar a 30 días máximo
                    try:
                        current_date = ecuador_now.date()
                        day = current_date - timedelta(days=i)
                        day_filter = base_filter & Q(fecha_lectura__date=day)

                        day_count = EstadisticaLectura.objects.filter(day_filter).values('cuento').distinct().count()

                        activity_data.append({
                            'day': day.strftime('%a') if time_period == 'week' else day.day,
                            'date': day.strftime('%Y-%m-%d'),
                            'stories': day_count
                        })
                    except Exception as e:
                        logger.error(f"Error processing day {i}: {e}")
                        continue

                activity_data.reverse()

        except Exception as e:
            logger.error(f"Error generating activity data: {e}")
            activity_data = []

        # Distribución de temas con manejo de errores
        theme_distribution = []
        try:
            theme_filter = Q(usuario=user, estado='completado', en_biblioteca=True)
            if perfil:
                theme_filter &= Q(perfil=perfil)
            if start_date:
                theme_filter &= Q(fecha_creacion__gte=start_date)

            theme_counts = Cuento.objects.filter(theme_filter).values('tema').annotate(
                count=Count('id')
            ).order_by('-count')

            for item in theme_counts:
                try:
                    if item['count'] > 0:
                        theme_code = item['tema']
                        theme_name = theme_code

                        try:
                            for choice in Cuento.TEMA_CHOICES:
                                if choice[0] == theme_code:
                                    theme_name = choice[1]
                                    break
                        except:
                            pass

                        theme_distribution.append({
                            'theme': theme_name,
                            'count': item['count']
                        })
                except Exception as e:
                    logger.error(f"Error processing theme: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error getting theme distribution: {e}")

        # Progreso de lectura con manejo de errores
        reading_progress = []
        try:
            if time_period in ['week', 'month']:
                ecuador_now = get_ecuador_time()
                for i in range(min(days_range, 30)):
                    try:
                        current_date = ecuador_now.date()
                        day = current_date - timedelta(days=i)
                        day_filter = base_filter & Q(fecha_lectura__date=day)

                        day_seconds = EstadisticaLectura.objects.filter(day_filter).aggregate(
                            total=Sum('tiempo_lectura')
                        )['total'] or 0
                        day_minutes = day_seconds // 60

                        reading_progress.append({
                            'date': day.strftime('%Y-%m-%d'),
                            'minutes': day_minutes,
                            'seconds': day_seconds
                        })
                    except Exception as e:
                        logger.error(f"Error processing reading progress day {i}: {e}")
                        continue

                reading_progress.reverse()
            else:  # year - CORREGIDO
                ecuador_now = get_ecuador_time()
                for i in range(12):
                    try:
                        current_date = ecuador_now.date()

                        # Calcular mes de manera segura
                        year = current_date.year
                        month = current_date.month - i

                        while month <= 0:
                            month += 12
                            year -= 1

                        month_date = date(year, month, 1)

                        # Calcular fin del mes
                        if i == 0:
                            month_end = ecuador_now.date()
                        else:
                            if month == 12:
                                next_month = date(year + 1, 1, 1)
                            else:
                                next_month = date(year, month + 1, 1)
                            month_end = next_month - timedelta(days=1)

                        month_filter = base_filter & Q(fecha_lectura__date__gte=month_date) & Q(
                            fecha_lectura__date__lte=month_end)

                        month_seconds = EstadisticaLectura.objects.filter(month_filter).aggregate(
                            total=Sum('tiempo_lectura')
                        )['total'] or 0
                        month_minutes = month_seconds // 60

                        reading_progress.append({
                            'date': month_date.strftime('%Y-%m-%d'),
                            'minutes': month_minutes,
                            'seconds': month_seconds
                        })
                    except Exception as e:
                        logger.error(f"Error processing reading progress month {i}: {e}")
                        continue

                reading_progress.reverse()

        except Exception as e:
            logger.error(f"Error generating reading progress: {e}")

        result = {
            'activity_data': activity_data,
            'theme_distribution': theme_distribution,
            'reading_progress': reading_progress
        }

        print(f"Datos de gráficas generados:")
        print(f"  - Actividad: {len(activity_data)} puntos")
        print(f"  - Temas: {len(theme_distribution)} categorías")
        print(f"  - Progreso: {len(reading_progress)} puntos")

        return result

    except Exception as e:
        logger.error(f"Critical error in get_chart_data: {e}")
        # Retornar datos vacíos en caso de error crítico
        return {
            'activity_data': [],
            'theme_distribution': [],
            'reading_progress': []
        }


def generate_library_report(user, perfil=None, time_period='month', format_type='pdf'):
    """Generar reporte de biblioteca en diferentes formatos - CORREGIDO"""
    try:
        print(
            f"Generando reporte: usuario={user.username}, perfil={perfil}, período={time_period}, formato={format_type}")

        # Obtener datos con manejo de errores
        try:
            analytics = get_reading_statistics(user, perfil, time_period)
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            analytics = {
                'total_stories': 0,
                'total_reading_time': '0s',
                'favorite_theme': 'Error'
            }

        try:
            chart_data = get_chart_data(user, perfil, time_period)
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            chart_data = {
                'activity_data': [],
                'theme_distribution': [],
                'reading_progress': []
            }

        try:
            deleted_stories = get_deleted_stories(user, perfil, time_period)
        except Exception as e:
            logger.error(f"Error getting deleted stories: {e}")
            deleted_stories = []

        report_data = {**analytics, **chart_data, 'deleted_stories': deleted_stories}

        if format_type == 'json':
            return report_data
        elif format_type == 'pdf':
            return generate_pdf_report(report_data, user, perfil, time_period)
        else:
            raise ValueError(f"Formato {format_type} no soportado")

    except Exception as e:
        logger.error(f"Critical error in generate_library_report: {e}")
        raise Exception(f"Error generando reporte: {str(e)}")


def get_deleted_stories(user, perfil=None, time_period='month'):
    try:
        start_date, end_date = get_time_range_ecuador(time_period)

        print(f"Obteniendo cuentos eliminados para período: {time_period}")
        print(f"Rango de fechas: {start_date} - {end_date}")

        deleted_stories = []

        try:
            from .models import CuentoEliminado

            queryset = CuentoEliminado.objects.filter(usuario=user)

            if start_date:
                queryset = queryset.filter(fecha_eliminacion__gte=start_date)

            if perfil:
                queryset = queryset.filter(perfil=perfil)
                print(f"Filtrando eliminados por perfil: {perfil.nombre}")

            cuentos_eliminados = queryset.order_by('-fecha_eliminacion')[:15]

            print(f"Cuentos eliminados encontrados: {cuentos_eliminados.count()}")

            for cuento_eliminado in cuentos_eliminados:
                try:
                    deleted_stories.append({
                        'titulo': cuento_eliminado.titulo,
                        'fecha_eliminacion': cuento_eliminado.fecha_eliminacion.strftime('%d de %B de %Y'),
                        'personaje': cuento_eliminado.personaje_principal or 'Sin personaje',
                        'tema': cuento_eliminado.tema_display,
                        'perfil': cuento_eliminado.perfil.nombre if cuento_eliminado.perfil else 'Sin perfil',
                        'fecha_creacion_original': cuento_eliminado.fecha_creacion_original.strftime('%d de %B de %Y'),
                        'motivo': cuento_eliminado.get_motivo_eliminacion_display()
                    })
                except Exception as e:
                    logger.error(f"Error processing deleted story: {e}")
                    continue

            print(f"✅ {len(deleted_stories)} cuentos eliminados procesados para el reporte")

        except ImportError:
            print("Modelo CuentoEliminado no encontrado, usando método alternativo")
            # Método alternativo más seguro
            deleted_stories = []

        except Exception as e:
            print(f"Error obteniendo cuentos eliminados: {str(e)}")
            logger.error(f"Error en get_deleted_stories: {str(e)}")
            deleted_stories = []

        return deleted_stories

    except Exception as e:
        logger.error(f"Critical error in get_deleted_stories: {e}")
        return []


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for (page_num, page_state) in enumerate(self._saved_page_states):
            self.__dict__.update(page_state)
            self.draw_page_number(page_num + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, total_pages):
        try:
            self.setFillColor(colors.HexColor('#374151'))
            self.rect(0, letter[1] - 60, letter[0], 60, fill=1, stroke=0)
            # Logo y título en header
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 16)
            self.drawString(50, letter[1] - 35, "CuentIA")

            # Fecha actual de Ecuador
            self.setFont("Helvetica", 10)
            fecha_actual_ecuador = format_ecuador_datetime(include_time=False)
            self.drawRightString(letter[0] - 50, letter[1] - 35, f"Generado el {fecha_actual_ecuador}")

            # Footer más elegante
            self.setFillColor(colors.HexColor('#f3f4f6'))
            self.rect(0, 0, letter[0], 40, fill=1, stroke=0)

            # Número de página
            self.setFillColor(colors.HexColor('#374151'))
            self.setFont("Helvetica", 9)
            self.drawCentredText(letter[0] / 2, 20, f"Página {page_num} de {total_pages}")

            # Copyright
            self.drawCentredText(letter[0] / 2, 10, "© 2024 CuentIA - Reporte de Lectura Personalizado")
        except Exception as e:
            logger.error(f"Error drawing page elements: {e}")


def generate_pdf_report(analytics, user, perfil, time_period):
    try:
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60,
            canvasmaker=NumberedCanvas
        )

        styles = getSampleStyleSheet()

        # Estilos personalizados con manejo de errores
        try:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#1e293b'),
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=15,
                spaceBefore=20,
                textColor=colors.HexColor('#8b5cf6'),
                fontName='Helvetica-Bold'
            )

            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=10,
                textColor=colors.HexColor('#374151'),
                fontName='Helvetica'
            )
        except Exception as e:
            logger.error(f"Error creating styles: {e}")
            # Usar estilos por defecto
            title_style = styles['Title']
            subtitle_style = styles['Heading2']
            normal_style = styles['Normal']

        story = []

        # Título del reporte con manejo de errores
        try:
            period_names = {
                'week': 'Semanal',
                'month': 'Mensual',
                'year': 'Anual',
                'all_time': 'Histórico'
            }

            title_text = f"Reporte de Lectura {period_names.get(time_period, 'Personalizado')}"
            if perfil:
                title_text += f"<br/><font size='16' color='#64748b'>Perfil: {perfil.nombre}</font>"

            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 20))
        except Exception as e:
            logger.error(f"Error creating title: {e}")
            story.append(Paragraph("Reporte de Lectura", title_style))

        # Información del usuario con manejo de errores
        try:
            period_start = analytics.get('period_start')
            period_end = analytics.get('period_end')

            if period_start:
                fecha_inicio = format_ecuador_datetime(period_start, include_time=False)
                fecha_fin = format_ecuador_datetime(period_end, include_time=False)
                rango_fechas = f"Período: {fecha_inicio} - {fecha_fin}"
            else:
                rango_fechas = "Período: Todos los tiempos"

            fecha_generacion_ecuador = format_ecuador_datetime(include_time=True)

            user_info = f"""
            <para align='center' backColor='#f8fafc' borderColor='#e2e8f0' borderWidth='1' 
                  borderPadding='15' borderRadius='8'>
            <font size='14' color='#1e293b'><b>{user.username.title()}</b></font><br/>
            <font size='11' color='#64748b'>Generado el {fecha_generacion_ecuador}</font><br/>
            <font size='10' color='#9ca3af'>{rango_fechas}</font>
            </para>
            """
            story.append(Paragraph(user_info, normal_style))
            story.append(Spacer(1, 30))
        except Exception as e:
            logger.error(f"Error creating user info: {e}")

        # Resumen ejecutivo con manejo de errores
        try:
            story.append(Paragraph("Resumen Ejecutivo", subtitle_style))

            stats_data = [
                [
                    Paragraph(f"""
                <para align='center' backColor='#f8fafc' borderColor='#d1d5db' 
                      borderWidth='1' borderPadding='20'>
                <font size='11' color='#374151'><b>Total de Cuentos</b></font><br/><br/>
                <font size='20' color='#1f2937'><b>{analytics.get('total_stories', 0)}</b></font><br/><br/>
                <font size='9' color='#6b7280'>cuentos leídos</font>
                </para>
                """, normal_style),

                    Paragraph(f"""
                <para align='center' backColor='#f8fafc' borderColor='#d1d5db' 
                      borderWidth='1' borderPadding='20'>
                <font size='11' color='#374151'><b>Tiempo de Lectura</b></font><br/><br/>
                <font size='20' color='#1f2937'><b>{analytics.get('total_reading_time', '0s')}</b></font><br/><br/>
                <font size='9' color='#6b7280'>tiempo invertido</font>
                </para>
                """, normal_style)
                ],
                [
                    Paragraph(f"""
                <para align='center' backColor='#f8fafc' borderColor='#d1d5db' 
                      borderWidth='1' borderPadding='20'>
                <font size='11' color='#374151'><b>Temas Explorados</b></font><br/><br/>
                <font size='20' color='#1f2937'><b>{analytics.get('themes_explored', 0)}</b></font><br/><br/>
                <font size='9' color='#6b7280'>categorías diferentes</font>
                </para>
                """, normal_style),

                    Paragraph(f"""
                <para align='center' backColor='#f8fafc' borderColor='#d1d5db' 
                      borderWidth='1' borderPadding='20'>
                <font size='11' color='#374151'><b>Tema Favorito</b></font><br/><br/>
                <font size='20' color='#1f2937'><b>{analytics.get('favorite_theme', 'Sin datos')}</b></font><br/><br/>
                <font size='9' color='#6b7280'>más popular</font>
                </para>
                """, normal_style)
                ]
            ]

            stats_table = Table(stats_data, colWidths=[240, 240], rowHeights=[120, 120])
            stats_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))

            story.append(stats_table)
            story.append(Spacer(1, 25))
        except Exception as e:
            logger.error(f"Error creating executive summary: {e}")

        # Distribución por temas con manejo de errores
        try:
            story.append(Paragraph("Distribución por Temas", subtitle_style))

            theme_distribution = analytics.get('theme_distribution', [])
            if theme_distribution:
                theme_table_data = [
                    [Paragraph("<b>Tema</b>", normal_style),
                     Paragraph("<b>Cantidad</b>", normal_style),
                     Paragraph("<b>Porcentaje</b>", normal_style)]
                ]

                total_themes = sum(item['count'] for item in theme_distribution)

                for theme in theme_distribution[:8]:
                    try:
                        percentage = (theme['count'] / total_themes * 100) if total_themes > 0 else 0

                        theme_row = [
                            Paragraph(f"<b>{theme.get('theme', 'Sin tema')}</b>", normal_style),
                            Paragraph(f"<b>{theme.get('count', 0)}</b>", normal_style),
                            Paragraph(f"{percentage:.1f}%", normal_style)
                        ]

                        theme_table_data.append(theme_row)
                    except Exception as e:
                        logger.error(f"Error processing theme row: {e}")
                        continue

                theme_table = Table(theme_table_data, colWidths=[200, 80, 120])
                theme_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9fafb')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')])
                ]))

                story.append(theme_table)
            else:
                story.append(Paragraph("No hay datos de temas disponibles para este período.", normal_style))

            story.append(Spacer(1, 25))
        except Exception as e:
            logger.error(f"Error creating theme distribution: {e}")

        # Recomendaciones con manejo de errores
        try:
            story.append(Paragraph("Recomendaciones Personalizadas", subtitle_style))

            recommendations = []
            total_stories = analytics.get('total_stories', 0)
            themes_explored = analytics.get('themes_explored', 0)
            stories_change = analytics.get('stories_change', 0)

            if total_stories < 5:
                recommendations.append("Considera establecer una meta de lectura semanal para aumentar tu actividad.")

            if themes_explored < 3:
                recommendations.append("Explora nuevos temas para diversificar tu experiencia de lectura.")

            if stories_change > 20:
                recommendations.append("¡Excelente progreso! Mantén este ritmo de lectura.")
            elif stories_change < -10:
                recommendations.append("Tu actividad ha disminuido. ¿Qué tal si estableces recordatorios de lectura?")

            if not recommendations:
                recommendations.append("¡Mantén el excelente hábito de lectura que has desarrollado!")

            recommendations_text = "<para backColor='#eff6ff' borderColor='#bfdbfe' borderWidth='1' borderPadding='15'>"
            for rec in recommendations:
                recommendations_text += f"• {rec}<br/>"
            recommendations_text += "</para>"

            story.append(Paragraph(recommendations_text, normal_style))
            story.append(Spacer(1, 30))
        except Exception as e:
            logger.error(f"Error creating recommendations: {e}")

        # Pie de página final con manejo de errores
        try:
            fecha_generacion_ecuador = format_ecuador_datetime(include_time=True)
            footer_text = f"""
            <para align='center' backColor='#f8fafc' borderColor='#e2e8f0' borderWidth='1' 
                  borderPadding='20' borderRadius='8'>
            <font size='12' color='#8b5cf6'><b>CuentIA - Tu Compañero de Lectura Inteligente</b></font><br/>
            <font size='10' color='#64748b'>Este reporte fue generado automáticamente el {fecha_generacion_ecuador}</font><br/>
            <font size='9' color='#9ca3af'>Continúa explorando el maravilloso mundo de los cuentos personalizados</font><br/>
            <font size='8' color='#d1d5db'>© 2024 CuentIA - Todos los derechos reservados</font>
            </para>
            """
            story.append(Paragraph(footer_text, normal_style))
        except Exception as e:
            logger.error(f"Error creating footer: {e}")

        # Construir el documento con manejo de errores
        try:
            doc.build(story)
            buffer.seek(0)
            pdf_data = buffer.getvalue()

            # Verificar que el PDF no esté vacío
            if len(pdf_data) == 0:
                raise Exception("El PDF generado está vacío")

            return pdf_data
        except Exception as e:
            logger.error(f"Error building PDF: {str(e)}")
            # Crear PDF de error simple
            error_buffer = BytesIO()
            error_doc = SimpleDocTemplate(error_buffer, pagesize=letter)
            error_story = [
                Paragraph("Error al generar el reporte", styles['Title']),
                Paragraph(f"Se produjo un error: {str(e)}", styles['Normal']),
                Paragraph("Por favor, intenta nuevamente o contacta al soporte técnico.", styles['Normal'])
            ]
            error_doc.build(error_story)
            error_buffer.seek(0)
            return error_buffer.getvalue()

    except Exception as e:
        logger.error(f"Critical error in generate_pdf_report: {str(e)}")
        # Crear PDF de error mínimo
        try:
            error_buffer = BytesIO()
            error_doc = SimpleDocTemplate(error_buffer, pagesize=letter)
            error_story = [
                Paragraph("Error Crítico", getSampleStyleSheet()['Title']),
                Paragraph(f"No se pudo generar el reporte: {str(e)}", getSampleStyleSheet()['Normal'])
            ]
            error_doc.build(error_story)
            error_buffer.seek(0)
            return error_buffer.getvalue()
        except:
            # Si todo falla, crear un PDF vacío válido
            empty_buffer = BytesIO()
            empty_doc = SimpleDocTemplate(empty_buffer, pagesize=letter)
            empty_doc.build([Paragraph("Reporte no disponible", getSampleStyleSheet()['Normal'])])
            empty_buffer.seek(0)
            return empty_buffer.getvalue()
