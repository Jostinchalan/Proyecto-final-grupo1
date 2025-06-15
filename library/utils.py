#library/utils.py
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Sum, Avg, Q
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import logging
from stories.models import Cuento, EstadisticaLectura
from user.models import Perfil

logger = logging.getLogger(__name__)


def get_time_range(time_period):
    """Obtener rango de fechas basado en período"""
    now = timezone.now()

    if time_period == 'week':
        start_date = now - timedelta(days=7)
    elif time_period == 'month':
        start_date = now - timedelta(days=30)
    elif time_period == 'year':
        start_date = now - timedelta(days=365)
    else:  # 'all_time'
        start_date = None

    return start_date, now


def get_reading_statistics(user, perfil=None, time_period='week'):
    """Obtener estadísticas de lectura para un usuario o perfil específico - MEJORADA"""
    start_date, end_date = get_time_range(time_period)

    print(f"📊 Calculando estadísticas para período: {time_period}")
    print(f"📅 Rango de fechas: {start_date} - {end_date}")

    # Filtros base
    sessions_filter = Q(usuario=user)
    stories_filter = Q(usuario=user, estado='completado', en_biblioteca=True)  # Solo biblioteca

    # Si se especifica un perfil, filtrar por él
    if perfil:
        sessions_filter &= Q(perfil=perfil)
        stories_filter &= Q(perfil=perfil)
        print(f"👤 Filtrando por perfil: {perfil.nombre}")

    # Filtrar por fecha si es necesario
    if start_date:
        sessions_filter &= Q(fecha_lectura__gte=start_date)
        stories_filter &= Q(fecha_creacion__gte=start_date)

    # Obtener sesiones de lectura y cuentos
    sessions = EstadisticaLectura.objects.filter(sessions_filter)
    stories = Cuento.objects.filter(stories_filter)

    print(f"📚 Cuentos encontrados: {stories.count()}")
    print(f"📖 Sesiones de lectura: {sessions.count()}")

    # Estadísticas básicas
    total_stories = stories.count()
    total_reading_time_seconds = sessions.aggregate(
        total=Sum('tiempo_lectura')
    )['total'] or 0

    # Convertir segundos a formato legible
    total_hours = total_reading_time_seconds // 3600
    total_minutes = (total_reading_time_seconds % 3600) // 60
    total_seconds_remainder = total_reading_time_seconds % 60

    if total_hours > 0:
        time_display = f"{total_hours}h {total_minutes}m"
    elif total_minutes > 0:
        time_display = f"{total_minutes}m {total_seconds_remainder}s"
    else:
        time_display = f"{total_seconds_remainder}s"

    # Cuentos por semana (promedio)
    if time_period == 'week':
        stories_per_week = total_stories  # En una semana
    elif time_period == 'month':
        stories_per_week = round(total_stories / 4.33, 1)  # Promedio semanal en un mes
    else:  # year
        stories_per_week = round(total_stories / 52, 1)  # Promedio semanal en un año

    # Temas explorados
    theme_counts = stories.values('tema').annotate(
        count=Count('id')
    ).order_by('-count')
    themes_explored = len(theme_counts)

    # Tema favorito
    favorite_theme = theme_counts.first()
    favorite_theme_name = "Sin datos"
    if favorite_theme and favorite_theme['count'] > 0:
        theme_code = favorite_theme['tema']
        # Obtener nombre legible del tema
        try:
            for choice in Cuento.TEMA_CHOICES:
                if choice[0] == theme_code:
                    favorite_theme_name = choice[1]
                    break
            if favorite_theme_name == "Sin datos":
                favorite_theme_name = theme_code.title()
        except:
            favorite_theme_name = theme_code.title() if theme_code else "Sin datos"

    # Calcular cambios porcentuales
    stories_change = 0
    time_change = 0

    if start_date:
        # Período anterior para comparación
        period_duration = end_date - start_date
        prev_start = start_date - period_duration
        prev_sessions_filter = Q(usuario=user, fecha_lectura__gte=prev_start, fecha_lectura__lt=start_date)
        prev_stories_filter = Q(usuario=user, estado='completado', en_biblioteca=True, fecha_creacion__gte=prev_start,
                                fecha_creacion__lt=start_date)

        if perfil:
            prev_sessions_filter &= Q(perfil=perfil)
            prev_stories_filter &= Q(perfil=perfil)

        prev_sessions = EstadisticaLectura.objects.filter(prev_sessions_filter)
        prev_stories_count = Cuento.objects.filter(prev_stories_filter).count()
        prev_time = prev_sessions.aggregate(total=Sum('tiempo_lectura'))['total'] or 0

        if prev_stories_count > 0:
            stories_change = ((total_stories - prev_stories_count) / prev_stories_count) * 100
        elif total_stories > 0:
            stories_change = 100  # 100% de incremento si antes era 0

        if prev_time > 0:
            time_change = ((total_reading_time_seconds - prev_time) / prev_time) * 100
        elif total_reading_time_seconds > 0:
            time_change = 100  # 100% de incremento si antes era 0

    result = {
        'total_stories': total_stories,
        'total_reading_time': time_display,
        'total_reading_time_seconds': total_reading_time_seconds,
        'stories_per_week': stories_per_week,
        'themes_explored': themes_explored,
        'favorite_theme': favorite_theme_name,
        'stories_change': round(stories_change, 1),
        'time_change': round(time_change, 1),
        'average_session_time': sessions.aggregate(
            avg=Avg('tiempo_lectura')
        )['avg'] or 0,
    }

    print(f"✅ Estadísticas calculadas: {result}")
    return result


def get_chart_data(user, perfil=None, time_period='week'):
    """Obtener datos para gráficos de D3.js - MEJORADA"""
    start_date, end_date = get_time_range(time_period)

    print(f"📈 Generando datos de gráficas para período: {time_period}")

    # Filtros base
    base_filter = Q(usuario=user)
    if perfil:
        base_filter &= Q(perfil=perfil)
        print(f"👤 Filtrando gráficas por perfil: {perfil.nombre}")
    if start_date:
        base_filter &= Q(fecha_lectura__gte=start_date)

    # Actividad de lectura (últimos días según período)
    activity_data = []

    # Determinar número de días según período
    if time_period == 'week':
        days_range = 7
    elif time_period == 'month':
        days_range = 30
    else:  # year
        days_range = 12

    if time_period == 'year':
        # Para año usamos meses en lugar de días
        months_data = {}
        for i in range(12):
            current_date = timezone.now().date()
            month_date = current_date - timedelta(days=30 * i)
            month_key = month_date.strftime('%Y-%m')
            months_data[month_key] = {
                'month': month_date.strftime('%b'),
                'date': month_date.strftime('%Y-%m-%d'),
                'stories': 0
            }

        # Contar cuentos por mes
        month_counts = EstadisticaLectura.objects.filter(base_filter).extra(
            select={'month': "to_char(fecha_lectura, 'YYYY-MM')"}
        ).values('month').annotate(count=Count('cuento', distinct=True))

        for item in month_counts:
            if item['month'] in months_data:
                months_data[item['month']]['stories'] = item['count']

        activity_data = list(months_data.values())
        activity_data.reverse()  # Orden cronológico

    else:
        # Para semana y mes, contar por día
        for i in range(days_range):
            current_date = timezone.now().date()
            day = current_date - timedelta(days=i)
            day_filter = base_filter & Q(fecha_lectura__date=day)

            day_count = EstadisticaLectura.objects.filter(day_filter).values('cuento').distinct().count()

            activity_data.append({
                'day': day.strftime('%a') if time_period == 'week' else day.day,
                'date': day.strftime('%Y-%m-%d'),
                'stories': day_count
            })

        activity_data.reverse()  # Orden cronológico

    # Distribución por temas
    theme_distribution = []

    theme_filter = Q(usuario=user, estado='completado', en_biblioteca=True)
    if perfil:
        theme_filter &= Q(perfil=perfil)
    if start_date:
        theme_filter &= Q(fecha_creacion__gte=start_date)

    theme_counts = Cuento.objects.filter(theme_filter).values('tema').annotate(
        count=Count('id')
    ).order_by('-count')

    # Convertir a formato para D3.js y obtener nombres legibles
    for item in theme_counts:
        if item['count'] > 0:  # Solo incluir temas con cuentos
            theme_code = item['tema']
            theme_name = theme_code

            # Obtener nombre legible del tema
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

    # Datos de progreso de lectura (tiempo por día)
    reading_progress = []

    if time_period in ['week', 'month']:
        for i in range(days_range):
            current_date = timezone.now().date()
            day = current_date - timedelta(days=i)
            day_filter = base_filter & Q(fecha_lectura__date=day)

            day_seconds = EstadisticaLectura.objects.filter(day_filter).aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0
            day_minutes = day_seconds // 60  # Convertir a minutos

            reading_progress.append({
                'date': day.strftime('%Y-%m-%d'),
                'minutes': day_minutes,
                'seconds': day_seconds
            })

        reading_progress.reverse()
    else:  # year
        # Para año usamos meses
        for i in range(12):
            current_date = timezone.now().date()
            month_date = current_date - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)

            if i == 0:
                month_end = timezone.now().date()
            else:
                if month_start.month == 12:
                    next_month = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1)
                month_end = next_month - timedelta(days=1)

            month_filter = base_filter & Q(fecha_lectura__date__gte=month_start) & Q(fecha_lectura__date__lte=month_end)

            month_seconds = EstadisticaLectura.objects.filter(month_filter).aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0
            month_minutes = month_seconds // 60

            reading_progress.append({
                'date': month_date.strftime('%Y-%m-%d'),
                'minutes': month_minutes,
                'seconds': month_seconds
            })

        reading_progress.reverse()

    result = {
        'activity_data': activity_data,
        'theme_distribution': theme_distribution,
        'reading_progress': reading_progress
    }

    print(f"📊 Datos de gráficas generados:")
    print(f"  - Actividad: {len(activity_data)} puntos")
    print(f"  - Temas: {len(theme_distribution)} categorías")
    print(f"  - Progreso: {len(reading_progress)} puntos")

    return result


def get_chart_data(user, perfil=None, time_period='month'):
    """Obtener datos para gráficos de D3.js"""
    start_date, end_date = get_time_range(time_period)

    # Filtros base
    base_filter = Q(usuario=user)
    if perfil:
        base_filter &= Q(perfil=perfil)
    if start_date:
        base_filter &= Q(fecha_lectura__gte=start_date)

    # Actividad de lectura (últimos días según período)
    activity_data = []

    # Determinar número de días según período
    if time_period == 'week':
        days_range = 7
    elif time_period == 'month':
        days_range = 30
    else:  # year
        days_range = 12

    if time_period == 'year':
        # Para año usamos meses en lugar de días
        months_data = {}
        for i in range(12):
            # Usar la fecha actual sin ajustes para evitar problemas de zona horaria
            current_date = timezone.now().date()
            month_date = current_date - timedelta(days=30 * i)
            month_key = month_date.strftime('%Y-%m')
            months_data[month_key] = {
                'month': month_date.strftime('%b'),
                'date': month_date.strftime('%Y-%m-%d'),
                'stories': 0
            }

        # Contar cuentos por mes
        month_counts = EstadisticaLectura.objects.filter(base_filter).extra(
            select={'month': "to_char(fecha_lectura, 'YYYY-MM')"}
        ).values('month').annotate(count=Count('cuento', distinct=True))

        for item in month_counts:
            if item['month'] in months_data:
                months_data[item['month']]['stories'] = item['count']

        activity_data = list(months_data.values())
        activity_data.reverse()  # Orden cronológico

    else:
        # Para semana y mes, contar por día
        for i in range(days_range):
            # Usar la fecha actual sin ajustes de zona horaria
            current_date = timezone.now().date()
            day = current_date - timedelta(days=i)
            day_filter = base_filter & Q(fecha_lectura__date=day)

            day_count = EstadisticaLectura.objects.filter(day_filter).values('cuento').distinct().count()

            activity_data.append({
                'day': day.strftime('%a') if time_period == 'week' else day.day,
                'date': day.strftime('%Y-%m-%d'),
                'stories': day_count
            })

        activity_data.reverse()  # Orden cronológico

    # Distribución por temas
    theme_distribution = []

    theme_filter = Q(usuario=user, estado='completado')
    if perfil:
        theme_filter &= Q(perfil=perfil)
    if start_date:
        theme_filter &= Q(fecha_creacion__gte=start_date)

    theme_counts = Cuento.objects.filter(theme_filter).values('tema').annotate(
        count=Count('id')
    ).order_by('-count')

    # Convertir a formato para D3.js y obtener nombres legibles
    for item in theme_counts:
        theme_code = item['tema']
        theme_name = theme_code

        # Obtener nombre legible del tema
        for choice in Cuento.TEMA_CHOICES:
            if choice[0] == theme_code:
                theme_name = choice[1]
                break

        theme_distribution.append({
            'theme': theme_name,
            'count': item['count']
        })

    # Datos de progreso de lectura (tiempo por día)
    reading_progress = []

    if time_period in ['week', 'month']:
        for i in range(days_range):
            current_date = timezone.now().date()
            day = current_date - timedelta(days=i)
            day_filter = base_filter & Q(fecha_lectura__date=day)

            day_seconds = EstadisticaLectura.objects.filter(day_filter).aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0
            day_minutes = day_seconds // 60  # Convertir a minutos

            reading_progress.append({
                'date': day.strftime('%Y-%m-%d'),
                'minutes': day_minutes,
                'seconds': day_seconds
            })

        reading_progress.reverse()
    else:  # year
        # Para año usamos meses
        for i in range(12):
            current_date = timezone.now().date()
            month_date = current_date - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)

            if i == 0:
                month_end = timezone.now().date()
            else:
                if month_start.month == 12:
                    next_month = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1)
                month_end = next_month - timedelta(days=1)

            month_filter = base_filter & Q(fecha_lectura__date__gte=month_start) & Q(fecha_lectura__date__lte=month_end)

            month_seconds = EstadisticaLectura.objects.filter(month_filter).aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0
            month_minutes = month_seconds // 60

            reading_progress.append({
                'date': month_date.strftime('%Y-%m-%d'),
                'minutes': month_minutes,
                'seconds': month_seconds
            })

        reading_progress.reverse()

    return {
        'activity_data': activity_data,
        'theme_distribution': theme_distribution,
        'reading_progress': reading_progress
    }


def generate_library_report(user, perfil=None, time_period='month', format_type='pdf'):
    """Generar reporte de biblioteca en diferentes formatos"""
    analytics = get_reading_statistics(user, perfil, time_period)
    chart_data = get_chart_data(user, perfil, time_period)

    # Combinar datos
    report_data = {**analytics, **chart_data}

    if format_type == 'json':
        return report_data

    elif format_type == 'pdf':
        return generate_pdf_report(report_data, user, perfil, time_period)

    else:
        raise ValueError(f"Formato {format_type} no soportado")


def generate_pdf_report(analytics, user, perfil, time_period):
    """Generar reporte PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Título
    title = f"Reporte de Lectura - {time_period.replace('_', ' ').title()}"
    if perfil:
        title += f" - {perfil.nombre}"

    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    # Estadísticas principales
    stats_data = [
        ['Métrica', 'Valor'],
        ['Total de cuentos', str(analytics['total_stories'])],
        ['Tiempo de lectura', analytics['total_reading_time']],
        ['Temas explorados', str(analytics['themes_explored'])],
        ['Tema favorito', str(analytics['favorite_theme'])],
        ['Cuentos por semana', str(analytics['stories_per_week'])],
    ]

    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(stats_table)
    story.append(Spacer(1, 12))

    # Información de distribución de temas
    story.append(Paragraph("Distribución por Temas", styles['Heading2']))
    story.append(Spacer(1, 6))

    theme_data = [['Tema', 'Cantidad']]
    for theme in analytics['theme_distribution'][:5]:  # Top 5 temas
        theme_data.append([theme['theme'], str(theme['count'])])

    theme_table = Table(theme_data)
    theme_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(theme_table)
    story.append(Spacer(1, 20))

    # Pie de página
    story.append(
        Paragraph(f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} para {user.username}", styles['Normal']))
    story.append(Paragraph("© 2024 CuentIA - Todos los derechos reservados", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
