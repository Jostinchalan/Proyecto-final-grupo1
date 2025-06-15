from django.db import models
from django.contrib.auth.models import User
from stories.models import Cuento
from user.models import Perfil
from django.utils import timezone
from datetime import timedelta


class LibraryQuerySet(models.QuerySet):
    """Custom QuerySet for library operations"""

    def completed(self):
        """Filter only completed stories"""
        return self.filter(estado='completado')

    def in_library(self):
        """Filter only stories in library"""
        return self.filter(en_biblioteca=True)

    def by_user(self, user):
        """Filter stories by specific user"""
        return self.filter(usuario=user)

    def by_profile(self, profile_id):
        """Filter by specific profile"""
        if profile_id and profile_id != 'todos':
            return self.filter(perfil_id=profile_id)
        return self

    def by_theme(self, theme):
        """Filter by theme"""
        if theme and theme != 'todos':
            return self.filter(tema__icontains=theme)
        return self

    def search_title(self, title):
        """Search by title"""
        if title:
            return self.filter(titulo__icontains=title)
        return self

    def order_by_date(self, order_by):
        """Order by date criteria"""
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


class LibraryManager:
    """Manager for library operations using the existing Cuento model"""

    @staticmethod
    def get_library_stories(user):
        """Get all completed stories from user for the library"""
        return Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True  # SOLO cuentos en biblioteca
        ).select_related('perfil').order_by('-fecha_creacion')

    @staticmethod
    def get_user_themes(user):
        """Get all unique themes from user's stories IN LIBRARY"""
        return Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True
        ).values_list('tema', flat=True).distinct().order_by('tema')

    @staticmethod
    def get_user_years(user):
        """Get all creation years from user's stories IN LIBRARY"""
        return Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True
        ).dates('fecha_creacion', 'year', order='DESC')

    @staticmethod
    def filter_library_stories(user, filters=None):
        """Filter library stories by criteria"""
        if filters is None:
            filters = {}

        queryset = Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True  # SOLO cuentos en biblioteca
        ).select_related('perfil')

        # Apply filters
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

    @staticmethod
    def search_stories_ajax(user, query):
        """AJAX search for stories IN LIBRARY"""
        if len(query) < 2:
            return Cuento.objects.none()

        return Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True,  # SOLO cuentos en biblioteca
            titulo__icontains=query
        ).select_related('perfil')[:10]

    @staticmethod
    def get_library_statistics(user):
        """Get library statistics for the user"""
        stories = Cuento.objects.filter(
            usuario=user,
            estado='completado',
            en_biblioteca=True  # SOLO cuentos en biblioteca
        )

        return {
            'total_stories': stories.count(),
            'favorite_themes': stories.values('tema').annotate(
                count=models.Count('tema')
            ).order_by('-count')[:3],
            'most_active_profile': stories.values('perfil__nombre').annotate(
                count=models.Count('perfil')
            ).order_by('-count').first(),
            'most_read_story': stories.order_by('-veces_leido').first(),
        }
