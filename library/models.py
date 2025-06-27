from django.db import models
from django.contrib.auth.models import User
from stories.models import Cuento
from user.models import Perfil
from django.utils import timezone
from datetime import timedelta


class LibraryQuerySet(models.QuerySet):
    def completed(self):
        return self.filter(estado='completado')

    def in_library(self):
        return self.filter(en_biblioteca=True)

    def by_user(self, user):
        return self.filter(usuario=user)

    def by_profile(self, profile_id):
        if profile_id and profile_id != 'todos':
            return self.filter(perfil_id=profile_id)
        return self

    def by_theme(self, theme):
        if theme and theme != 'todos':
            return self.filter(tema__icontains=theme)
        return self

    def search_title(self, title):
        if title:
            return self.filter(titulo__icontains=title)
        return self

    def order_by_date(self, order_by):
        if order_by == 'semana_anterior':
            date_limit = timezone.now() - timedelta(days=7)
            return self.filter(fecha_creacion__gte=date_limit)
        elif order_by == 'mes_anterior':
            date_limit = timezone.now() - timedelta(days=30)
            return self.filter(fecha_creacion__gte=date_limit)
        elif order_by and order_by.isdigit():
            year = int(order_by)
            return self.filter(fecha_creacion__year=year)
        return self


# NUEVO MODELO: Sistema de auditoría para cuentos eliminados
class CuentoEliminado(models.Model):

    # Información del cuento eliminado
    cuento_id_original = models.IntegerField(help_text="ID original del cuento eliminado")
    titulo = models.CharField(max_length=200, help_text="Título del cuento eliminado")
    personaje_principal = models.CharField(max_length=100, blank=True, null=True)
    tema = models.CharField(max_length=50, blank=True, null=True)
    contenido_preview = models.TextField(blank=True, null=True, help_text="Primeras 200 palabras del contenido")

    # Información del usuario y perfil
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Usuario que eliminó el cuento")
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True,
                               help_text="Perfil asociado al cuento")

    # Información de la eliminación
    fecha_eliminacion = models.DateTimeField(default=timezone.now, help_text="Fecha y hora de eliminación")
    fecha_creacion_original = models.DateTimeField(help_text="Fecha original de creación del cuento")

    # Metadatos adicionales
    motivo_eliminacion = models.CharField(
        max_length=100,
        choices=[
            ('usuario', 'Eliminado por el usuario'),
            ('admin', 'Eliminado por administrador'),
            ('sistema', 'Eliminado por el sistema'),
            ('limpieza', 'Limpieza automática'),
        ],
        default='usuario'
    )

    ip_eliminacion = models.GenericIPAddressField(null=True, blank=True, help_text="IP desde donde se eliminó")
    user_agent = models.TextField(blank=True, null=True, help_text="User agent del navegador")

    class Meta:
        db_table = 'library_cuento_eliminado'
        verbose_name = 'Cuento Eliminado'
        verbose_name_plural = 'Cuentos Eliminados'
        ordering = ['-fecha_eliminacion']
        indexes = [
            models.Index(fields=['usuario', 'fecha_eliminacion']),
            models.Index(fields=['perfil', 'fecha_eliminacion']),
            models.Index(fields=['cuento_id_original']),
        ]

    def __str__(self):
        return f"{self.titulo} - Eliminado el {self.fecha_eliminacion.strftime('%d/%m/%Y')}"

    @property
    def tema_display(self):
        """Obtener nombre legible del tema"""
        if not self.tema:
            return "Sin tema"

        try:
            # Intentar obtener el nombre legible desde las opciones de Cuento
            from stories.models import Cuento
            for choice in Cuento.TEMA_CHOICES:
                if choice[0] == self.tema:
                    return choice[1]
        except:
            pass

        return self.tema.title()

    def save(self, *args, **kwargs):
        # Truncar contenido_preview si es muy largo
        if self.contenido_preview and len(self.contenido_preview) > 500:
            self.contenido_preview = self.contenido_preview[:500] + "..."

        super().save(*args, **kwargs)


class LibraryManager:

    @staticmethod
    def get_library_stories(user):
        try:
            return Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True
            ).select_related('perfil').order_by('-fecha_creacion')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo cuentos de biblioteca: {e}")
            return Cuento.objects.none()

    @staticmethod
    def get_user_themes(user):
        try:
            return Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True
            ).values_list('tema', flat=True).distinct().order_by('tema')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo temas: {e}")
            return []

    @staticmethod
    def get_user_years(user):
        try:
            return Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True
            ).dates('fecha_creacion', 'year', order='DESC')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo años: {e}")
            return []

    @staticmethod
    def filter_library_stories(user, filters=None):
        if filters is None:
            filters = {}

        try:
            queryset = Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True
            ).select_related('perfil')

            profile_id = filters.get('perfil')
            if profile_id and profile_id != 'todos':
                queryset = queryset.filter(perfil_id=profile_id)

            theme = filters.get('tema')
            if theme and theme != 'todos':
                queryset = queryset.filter(tema__icontains=theme)

            title = filters.get('titulo')
            if title:
                queryset = queryset.filter(titulo__icontains=title)

            order_by = filters.get('ordenar')
            if order_by:
                if order_by == 'semana_anterior':
                    date_limit = timezone.now() - timedelta(days=7)
                    queryset = queryset.filter(fecha_creacion__gte=date_limit)
                elif order_by == 'mes_anterior':
                    date_limit = timezone.now() - timedelta(days=30)
                    queryset = queryset.filter(fecha_creacion__gte=date_limit)
                elif order_by.isdigit():
                    year = int(order_by)
                    queryset = queryset.filter(fecha_creacion__year=year)

            return queryset.order_by('-fecha_creacion')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error filtrando cuentos: {e}")
            return Cuento.objects.none()

    @staticmethod
    def search_stories_ajax(user, query):
        if len(query) < 2:
            return Cuento.objects.none()

        try:
            return Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True,
                titulo__icontains=query
            ).select_related('perfil')[:10]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en búsqueda AJAX: {e}")
            return Cuento.objects.none()

    @staticmethod
    def get_library_statistics(user):
        try:
            stories = Cuento.objects.filter(
                usuario=user,
                estado='completado',
                en_biblioteca=True
            )

            favorite_themes = stories.values('tema').annotate(
                count=models.Count('tema')
            ).order_by('-count')[:3]

            most_active_profile = stories.values('perfil__nombre').annotate(
                count=models.Count('perfil')
            ).order_by('-count').first()

            most_read_story = stories.order_by('-veces_leido').first()

            return {
                'total_stories': stories.count(),
                'favorite_themes': list(favorite_themes),
                'most_active_profile': most_active_profile,
                'most_read_story': most_read_story,
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'total_stories': 0,
                'favorite_themes': [],
                'most_active_profile': None,
                'most_read_story': None,
            }

    @staticmethod
    def registrar_cuento_eliminado(cuento, usuario, request=None, motivo='usuario'):
        try:
            # Obtener información adicional del request si está disponible
            ip_eliminacion = None
            user_agent = None

            if request:
                # Obtener IP real considerando proxies
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_eliminacion = x_forwarded_for.split(',')[0].strip()
                else:
                    ip_eliminacion = request.META.get('REMOTE_ADDR')

                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limitar longitud

            # Crear registro de eliminación
            cuento_eliminado = CuentoEliminado.objects.create(
                cuento_id_original=cuento.id,
                titulo=cuento.titulo,
                personaje_principal=cuento.personaje_principal,
                tema=cuento.tema,
                contenido_preview=cuento.contenido[:500] if cuento.contenido else None,
                usuario=usuario,
                perfil=cuento.perfil,
                fecha_creacion_original=cuento.fecha_creacion,
                motivo_eliminacion=motivo,
                ip_eliminacion=ip_eliminacion,
                user_agent=user_agent
            )

            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Cuento eliminado registrado: {cuento.titulo} (ID: {cuento.id}) por usuario {usuario.username}")

            return cuento_eliminado

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error registrando cuento eliminado: {e}")
            return None
