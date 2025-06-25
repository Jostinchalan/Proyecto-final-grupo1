from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from stories.models import Cuento, EstadisticaLectura
from user.models import Perfil
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
import calendar
import logging

logger = logging.getLogger(__name__)


def landing_view(request):
    """Vista para la página de inicio pública"""
    return render(request, 'landing.html')


@login_required
def dashboard_view(request):
    """Vista principal del dashboard con datos reales y estadísticas completas"""
    try:
        # Cuentos recientes del usuario (últimos 6 para el carrusel)
        cuentos_recientes = Cuento.objects.filter(
            usuario=request.user
        ).order_by('-fecha_creacion')[:6]

        # Perfiles recientes (últimos 6 para mezclar en actividad reciente)
        perfiles_recientes = Perfil.objects.filter(
            usuario=request.user
        ).order_by('-id')[:6]

        # Cuentos populares (favoritos y más leídos)
        cuentos_populares = Cuento.objects.filter(
            usuario=request.user,
            estado='completado'
        ).filter(
            Q(es_favorito=True) | Q(veces_leido__gt=0)
        ).order_by('-veces_leido', '-es_favorito')[:5]

        # Si no hay cuentos populares, mostrar los más recientes completados
        if not cuentos_populares.exists():
            cuentos_populares = Cuento.objects.filter(
                usuario=request.user,
                estado='completado'
            ).order_by('-fecha_creacion')[:3]

        # === ESTADÍSTICAS RÁPIDAS (CORREGIDAS PARA COINCIDIR CON SEGUIMIENTO) ===

        # 1. Total de cuentos (TODOS los cuentos, no solo completados)
        total_cuentos = Cuento.objects.filter(
            usuario=request.user,
            estado='completado'
        ).count()

        # 2. Cuentos este mes (TODOS los cuentos de este mes)
        ahora = timezone.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cuentos_este_mes = Cuento.objects.filter(
            usuario=request.user,
            fecha_creacion__gte=inicio_mes,
            estado='completado'
        ).count()

        # 3. Tiempo total de lectura (basado en EstadisticaLectura)
        tiempo_total_segundos = EstadisticaLectura.objects.filter(
            usuario=request.user
        ).aggregate(
            total=Sum('tiempo_lectura')
        )['total'] or 0

        # Convertir segundos a formato legible
        horas = tiempo_total_segundos // 3600
        minutos = (tiempo_total_segundos % 3600) // 60
        tiempo_lectura_formateado = f"{horas}h {minutos}m"

        # 4. Tema favorito (basado en TODOS los cuentos)
        tema_favorito_data = Cuento.objects.filter(
            usuario=request.user
        ).values('tema').annotate(
            count=Count('tema')
        ).order_by('-count').first()

        tema_favorito = "AVENTURA"  # Default
        if tema_favorito_data and tema_favorito_data['tema']:
            # Obtener el nombre legible del tema
            tema_dict = dict(Cuento.TEMA_CHOICES)
            tema_favorito = tema_dict.get(tema_favorito_data['tema'], tema_favorito_data['tema']).upper()

        # === ACTIVIDAD MENSUAL CORREGIDA (últimas 5 semanas con datos reales) ===
        actividad_mensual = []

        # Calcular las últimas 5 semanas
        for i in range(4, -1, -1):  # 4, 3, 2, 1, 0 (de más antigua a más reciente)
            # Calcular el inicio y fin de cada semana
            dias_atras = i * 7
            fin_semana = ahora - timedelta(days=dias_atras)
            inicio_semana = fin_semana - timedelta(days=6)

            # Contar cuentos creados en esa semana (TODOS los cuentos)
            cuentos_semana = Cuento.objects.filter(
                usuario=request.user,
                fecha_creacion__gte=inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0),
                fecha_creacion__lte=fin_semana.replace(hour=23, minute=59, second=59, microsecond=999999)
            ).count()

            # También contar tiempo de lectura de esa semana
            tiempo_semana = EstadisticaLectura.objects.filter(
                usuario=request.user,
                fecha_lectura__gte=inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0),
                fecha_lectura__lte=fin_semana.replace(hour=23, minute=59, second=59, microsecond=999999)
            ).aggregate(
                total=Sum('tiempo_lectura')
            )['total'] or 0

            actividad_mensual.append({
                'semana': f'S{5 - i}',  # S1, S2, S3, S4, S5
                'cuentos': cuentos_semana,
                'tiempo_minutos': tiempo_semana // 60,
                'inicio': inicio_semana.strftime('%d/%m'),
                'fin': fin_semana.strftime('%d/%m'),
                'porcentaje': 0  # Se calculará después
            })

        # Calcular porcentajes para el gráfico (basado en el máximo)
        max_cuentos = max([semana['cuentos'] for semana in actividad_mensual]) if actividad_mensual else 1
        if max_cuentos == 0:
            max_cuentos = 1  # Evitar división por cero

        for semana in actividad_mensual:
            # Asegurar que siempre haya una altura mínima visible
            if semana['cuentos'] == 0:
                semana['porcentaje'] = 5  # 5% mínimo para mostrar la barra
            else:
                semana['porcentaje'] = max(15, (semana['cuentos'] / max_cuentos) * 85)  # Entre 15% y 85%

        # === ESTADÍSTICAS ADICIONALES ===

        # Cambio porcentual vs mes anterior
        mes_anterior = inicio_mes - timedelta(days=1)
        inicio_mes_anterior = mes_anterior.replace(day=1)

        cuentos_mes_anterior = Cuento.objects.filter(
            usuario=request.user,
            fecha_creacion__gte=inicio_mes_anterior,
            fecha_creacion__lt=inicio_mes
        ).count()

        cambio_porcentual = 0
        if cuentos_mes_anterior > 0:
            cambio_porcentual = round(((cuentos_este_mes - cuentos_mes_anterior) / cuentos_mes_anterior) * 100, 1)

        # Tiempo de lectura promedio por cuento
        tiempo_promedio = 0
        if total_cuentos > 0:
            tiempo_promedio = tiempo_total_segundos // total_cuentos // 60  # en minutos

        context = {
            # === DATOS ORIGINALES (mantenidos) ===
            'cuentos_recientes': cuentos_recientes,
            'perfiles_recientes': perfiles_recientes,
            'cuentos_populares': cuentos_populares,

            # === ESTADÍSTICAS RÁPIDAS (corregidas) ===
            'total_cuentos': total_cuentos,
            'cuentos_este_mes': cuentos_este_mes,
            'tiempo_lectura': tiempo_lectura_formateado,
            'tema_favorito': tema_favorito,

            # === ACTIVIDAD MENSUAL (corregida) ===
            'actividad_mensual': actividad_mensual,
            'cambio_porcentual': cambio_porcentual,
            'tiempo_promedio': tiempo_promedio,
            'tiempo_total_segundos': tiempo_total_segundos,
        }

        logger.info(
            f"Dashboard loaded for {request.user.username} - {total_cuentos} cuentos, {tiempo_lectura_formateado} tiempo")
        return render(request, 'dashboard.html', context)

    except Exception as e:
        logger.error(f"Error in dashboard_view: {str(e)}")
        # En caso de error, mostrar dashboard básico
        context = {
            'cuentos_recientes': [],
            'perfiles_recientes': [],
            'cuentos_populares': [],
            'total_cuentos': 0,
            'cuentos_este_mes': 0,
            'tiempo_lectura': '0h 0m',
            'tema_favorito': 'AVENTURA',
            'actividad_mensual': [
                {'semana': f'S{i + 1}', 'cuentos': 0, 'tiempo_minutos': 0, 'porcentaje': 5, 'inicio': '01/01',
                 'fin': '07/01'}
                for i in range(5)
            ],
            'cambio_porcentual': 0,
            'tiempo_promedio': 0,
            'tiempo_total_segundos': 0,
        }
        return render(request, 'dashboard.html', context)
