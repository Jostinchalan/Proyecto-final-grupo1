from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class Perfil(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='perfiles_infantiles')
    nombre = models.CharField(max_length=30)
    edad = models.PositiveSmallIntegerField()

    # NUEVO CAMPO PARA FOTO DE PERFIL
    foto_perfil = models.ImageField(
        upload_to='perfiles_infantiles/',
        null=True,
        blank=True,
        verbose_name="Foto de perfil",
        help_text="Sube una foto para el perfil del niño/a"
    )

    GENEROS = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
        ('N', 'No especificado'),
    ]
    genero = models.CharField(max_length=1, choices=GENEROS, default='N')

    # Nuevos campos reemplazando 'intereses'
    temas_preferidos = models.TextField(
        blank=True,
        verbose_name="Temas de cuentos preferidos",
        help_text="Ejemplo: amistad, aventura, misterio"
    )
    personajes_favoritos = models.TextField(
        blank=True,
        verbose_name="Personajes preferidos",
        help_text="Ejemplo: robots, héroes, dragones"
    )

    def temas_lista(self):
        """Devuelve la lista de temas preferidos ya limpios."""
        return [tema.strip() for tema in self.temas_preferidos.split(',') if tema.strip()]

    def personajes_lista(self):
        """Devuelve la lista de personajes favoritos ya limpios."""
        return [personaje.strip() for personaje in self.personajes_favoritos.split(',') if personaje.strip()]

    def __str__(self):
        return f"{self.nombre} ({self.get_genero_display()})"


# NUEVAS FUNCIONALIDADES - CONFIGURACIONES DE USUARIO
class UserProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('es', 'Español'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email_notifications = models.BooleanField(default=True)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='es')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class UserSettings(models.Model):
    LANGUAGE_CHOICES = [
        ('es', 'Español'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email_notifications = models.BooleanField(default=True)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='es')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuraciones de {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_settings(sender, instance, **kwargs):
    if hasattr(instance, 'settings'):
        instance.settings.save()
