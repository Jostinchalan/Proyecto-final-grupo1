from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from stories.models import Cuento, EstadisticaLectura
from user.models import Perfil
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def landing_view(request):
    """Vista para la página de inicio pública"""
    return render(request, 'landing.html')


@login_required
def dashboard_view(request):
    """Vista principal del dashboard con datos reales y carrusel"""
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

        # Estadísticas para el sidebar derecho
        total_cuentos = Cuento.objects.filter(
            usuario=request.user,
            estado='completado'
        ).count()

        # Cuentos este mes
        inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cuentos_este_mes = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            fecha_creacion__gte=inicio_mes
        ).count()

        # Tiempo total de lectura
        tiempo_total = EstadisticaLectura.objects.filter(
            usuario=request.user
        ).aggregate(
            total=Sum('tiempo_lectura')
        )['total'] or 0

        # Convertir segundos a formato legible
        horas = (tiempo_total // 3600) if tiempo_total else 0
        minutos = ((tiempo_total % 3600) // 60) if tiempo_total else 0
        tiempo_lectura_formateado = f"{horas}h {minutos}m"

        # Tema favorito
        tema_favorito_data = Cuento.objects.filter(
            usuario=request.user,
            estado='completado'
        ).values('tema').annotate(
            count=Count('tema')
        ).order_by('-count').first()

        tema_favorito = "AVENTURA"  # Default
        if tema_favorito_data:
            # Obtener el nombre legible del tema
            for choice in Cuento.TEMA_CHOICES:
                if choice[0] == tema_favorito_data['tema']:
                    tema_favorito = choice[1].upper()
                    break

        context = {
            'cuentos_recientes': cuentos_recientes,
            'perfiles_recientes': perfiles_recientes,
            'cuentos_populares': cuentos_populares,
            'total_cuentos': total_cuentos,
            'cuentos_este_mes': cuentos_este_mes,
            'tiempo_lectura': tiempo_lectura_formateado,
            'tema_favorito': tema_favorito,
        }

        logger.info(f"Dashboard loaded for {request.user.username}")
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
        }
        return render(request, 'dashboard.html', context)
