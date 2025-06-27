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
    return render(request, 'landing.html')


@login_required
def dashboard_view(request):
    try:
        cuentos_recientes = Cuento.objects.filter(
            usuario=request.user
        ).order_by('-fecha_creacion')[:6]

        perfiles_recientes = Perfil.objects.filter(
            usuario=request.user
        ).order_by('-id')[:6]

        cuentos_populares = Cuento.objects.filter(
            usuario=request.user,
            estado='completado'
        ).filter(
            Q(es_favorito=True) | Q(veces_leido__gt=0)
        ).order_by('-veces_leido', '-es_favorito')[:5]

        if not cuentos_populares.exists():
            cuentos_populares = Cuento.objects.filter(
                usuario=request.user,
                estado='completado'
            ).order_by('-fecha_creacion')[:3]
        total_cuentos = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).count()

        ahora = timezone.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cuentos_este_mes = Cuento.objects.filter(
            usuario=request.user,
            fecha_creacion__gte=inicio_mes,
            estado='completado',
            en_biblioteca=True
        ).count()
        tiempo_total_segundos = EstadisticaLectura.objects.filter(
            usuario=request.user
        ).aggregate(
            total=Sum('tiempo_lectura')
        )['total'] or 0

        if tiempo_total_segundos >= 3600:
            horas = tiempo_total_segundos // 3600
            minutos = (tiempo_total_segundos % 3600) // 60
            tiempo_lectura_formateado = f"{horas}h {minutos}m"
        elif tiempo_total_segundos >= 60:
            minutos = tiempo_total_segundos // 60
            tiempo_lectura_formateado = f"{minutos}m"
        else:
            tiempo_lectura_formateado = f"{tiempo_total_segundos}s"
        tema_favorito_data = Cuento.objects.filter(
            usuario=request.user,
            estado='completado',
            en_biblioteca=True
        ).values('tema').annotate(
            count=Count('tema')
        ).order_by('-count').first()

        tema_favorito = "Sin datos"
        if tema_favorito_data and tema_favorito_data['tema']:
            try:
                tema_dict = dict(Cuento.TEMA_CHOICES)
                tema_favorito = tema_dict.get(tema_favorito_data['tema'], tema_favorito_data['tema']).upper()
            except:
                tema_favorito = tema_favorito_data['tema'].upper()
        print(f"\n === CALCULANDO ACTIVIDAD MENSUAL SINCRONIZADA ===")

        actividad_semanal = []

        for i in range(4, -1, -1):
            dias_atras = i * 7
            fin_semana = ahora - timedelta(days=dias_atras)
            inicio_semana = fin_semana - timedelta(days=6)
            cuentos_semana = Cuento.objects.filter(
                usuario=request.user,
                fecha_creacion__gte=inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0),
                fecha_creacion__lte=fin_semana.replace(hour=23, minute=59, second=59, microsecond=999999),
                estado='completado',
                en_biblioteca=True
            ).count()
            tiempo_semana_segundos = EstadisticaLectura.objects.filter(
                usuario=request.user,
                fecha_lectura__gte=inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0),
                fecha_lectura__lte=fin_semana.replace(hour=23, minute=59, second=59, microsecond=999999)
            ).aggregate(total=Sum('tiempo_lectura'))['total'] or 0

            tiempo_semana_minutos = tiempo_semana_segundos // 60

            semana_info = {
                'semana': f'S{5 - i}',
                'cuentos': cuentos_semana,
                'tiempo_minutos': tiempo_semana_minutos,
                'fecha_inicio': inicio_semana.strftime('%d/%m'),
                'fecha_fin': fin_semana.strftime('%d/%m'),
                'altura_barra': 20
            }

            actividad_semanal.append(semana_info)
            print(
                f" {semana_info['semana']}: {cuentos_semana} cuentos, {tiempo_semana_minutos}min ({semana_info['fecha_inicio']}-{semana_info['fecha_fin']})")
        max_cuentos_semana = max([s['cuentos'] for s in actividad_semanal]) if actividad_semanal else 1
        if max_cuentos_semana == 0:
            max_cuentos_semana = 1
        print(f"Máximo cuentos por semana: {max_cuentos_semana}")
        for semana in actividad_semanal:
            if semana['cuentos'] == 0:
                semana['altura_barra'] = 20
            else:
                proporcion = semana['cuentos'] / max_cuentos_semana
                semana['altura_barra'] = round(20 + (proporcion * 70), 1)  # Entre 20% y 90%
        print(f" ALTURAS CALCULADAS:")
        for s in actividad_semanal:
            print(f"   {s['semana']}: {s['cuentos']} cuentos → {s['altura_barra']}% altura")
        mes_anterior = inicio_mes - timedelta(days=1)
        inicio_mes_anterior = mes_anterior.replace(day=1)

        cuentos_mes_anterior = Cuento.objects.filter(
            usuario=request.user,
            fecha_creacion__gte=inicio_mes_anterior,
            fecha_creacion__lt=inicio_mes,
            estado='completado',
            en_biblioteca=True
        ).count()

        cambio_porcentual = 0
        if cuentos_mes_anterior > 0:
            cambio_porcentual = round(((cuentos_este_mes - cuentos_mes_anterior) / cuentos_mes_anterior) * 100, 1)
        tiempo_promedio = 0
        if total_cuentos > 0:
            tiempo_promedio = tiempo_total_segundos // total_cuentos // 60  # en minutos
        total_cuentos_5_semanas = sum([s['cuentos'] for s in actividad_semanal])
        total_tiempo_5_semanas = sum([s['tiempo_minutos'] for s in actividad_semanal])

        promedio_minutos_por_cuento = 0
        if total_cuentos_5_semanas > 0:
            promedio_minutos_por_cuento = round(total_tiempo_5_semanas / total_cuentos_5_semanas, 1)

        context = {
            'cuentos_recientes': cuentos_recientes,
            'perfiles_recientes': perfiles_recientes,
            'cuentos_populares': cuentos_populares,

            'total_cuentos': total_cuentos,
            'cuentos_este_mes': cuentos_este_mes,
            'tiempo_lectura': tiempo_lectura_formateado,
            'tema_favorito': tema_favorito,

            'actividad_semanal': actividad_semanal,
            'cambio_porcentual': cambio_porcentual,
            'tiempo_promedio': tiempo_promedio,
            'tiempo_total_segundos': tiempo_total_segundos,

            'total_cuentos_5_semanas': total_cuentos_5_semanas,
            'total_tiempo_5_semanas': total_tiempo_5_semanas,
            'promedio_minutos_por_cuento': promedio_minutos_por_cuento,
        }

        print(f"DASHBOARD FINAL SINCRONIZADO:")
        print(f"Total cuentos: {total_cuentos}")
        print(f"Cuentos este mes: {cuentos_este_mes}")
        print(f"Tiempo lectura: {tiempo_lectura_formateado}")
        print(f"Tema favorito: {tema_favorito}")
        print(f"Cuentos últimas 5 semanas: {total_cuentos_5_semanas}")
        print(f"Tiempo últimas 5 semanas: {total_tiempo_5_semanas}min")
        actividad_debug = []
        for s in actividad_semanal:
            actividad_debug.append(f"{s['semana']}:{s['cuentos']}({s['altura_barra']:.1f}%)")
        print(f"Actividad: {' | '.join(actividad_debug)}")
        print(f"=== FIN ACTIVIDAD MENSUAL SINCRONIZADA ===\n")

        logger.info(
            f"Dashboard sincronizado para {request.user.username} - {total_cuentos} cuentos, {tiempo_lectura_formateado} tiempo, actividad: {total_cuentos_5_semanas} cuentos en 5 semanas"
        )

        return render(request, 'dashboard.html', context)

    except Exception as e:
        logger.error(f"Error in dashboard_view: {str(e)}")
        context = {
            'cuentos_recientes': [],
            'perfiles_recientes': [],
            'cuentos_populares': [],
            'total_cuentos': 0,
            'cuentos_este_mes': 0,
            'tiempo_lectura': '0s',
            'tema_favorito': 'Sin datos',
            'actividad_semanal': [
                {'semana': f'S{i + 1}', 'cuentos': 0, 'tiempo_minutos': 0, 'altura_barra': 10, 'fecha_inicio': '01/01',
                 'fecha_fin': '07/01'}
                for i in range(5)
            ],
            'cambio_porcentual': 0,
            'tiempo_promedio': 0,
            'tiempo_total_segundos': 0,
            'total_cuentos_5_semanas': 0,
            'total_tiempo_5_semanas': 0,
        }
        return render(request, 'dashboard.html', context)
