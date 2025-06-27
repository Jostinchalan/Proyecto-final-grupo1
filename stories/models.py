from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from user.models import Perfil

class Cuento(models.Model):
    TEMA_CHOICES = [
        ('aventura', 'Aventura'),
        ('amistad', 'Amistad'),
        ('familia', 'Familia'),
        ('fantasia', 'Fantasía'),
        ('ciencia_ficcion', 'Ciencia Ficción'),
        ('misterio', 'Misterio'),
        ('humor', 'Humor'),
        ('educativo', 'Educativo'),
        ('valores', 'Valores'),
        ('naturaleza', 'Naturaleza'),
    ]

    ESTADO_CHOICES = [
        ('generando', 'Generando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.TextField()
    personaje_principal = models.TextField()
    tema = models.CharField(max_length=50, choices=TEMA_CHOICES)
    edad = models.CharField(max_length=20)
    longitud = models.CharField(max_length=20)
    contenido = models.TextField(blank=True)
    moraleja = models.TextField(blank=True)
    imagen_url = models.TextField(blank=True, null=True)
    imagen_prompt = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='generando')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    tiempo_lectura_estimado = models.IntegerField(default=300)  # en segundos
    veces_leido = models.IntegerField(default=0)
    es_favorito = models.BooleanField(default=False)
    en_biblioteca = models.BooleanField(default=False)  # NUEVO CAMPO

    def get_tema_display(self):
        return dict(self.TEMA_CHOICES).get(self.tema, self.tema)

    def marcar_como_leido(self):
        self.veces_leido += 1
        self.save(update_fields=['veces_leido'])

    def toggle_favorito(self):
        self.es_favorito = not self.es_favorito
        self.save(update_fields=['es_favorito'])
        return self.es_favorito

    def guardar_en_biblioteca(self):
        """Método para guardar el cuento en la biblioteca"""
        self.en_biblioteca = True
        self.save(update_fields=['en_biblioteca'])

    def __str__(self):
        return self.titulo

    class Meta:
        ordering = ['-fecha_creacion']


class EstadisticaLectura(models.Model):
    TIPO_LECTURA_CHOICES = [
        ('texto', 'Lectura de Texto'),
        ('audio', 'Escucha de Audio'),
        ('biblioteca', 'Desde Biblioteca'),
        ('descarga', 'Descarga PDF'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cuento = models.ForeignKey(Cuento, on_delete=models.CASCADE)
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_lectura = models.DateTimeField(auto_now_add=True)
    tiempo_lectura = models.IntegerField(default=0)  # en segundos
    tipo_lectura = models.TextField()

    class Meta:
        verbose_name = "Estadística de Lectura"
        verbose_name_plural = "Estadísticas de Lectura"
        indexes = [
            models.Index(fields=['usuario', 'perfil', 'fecha_lectura']),
            models.Index(fields=['cuento', 'perfil']),
        ]

    def __str__(self):
        perfil_name = self.perfil.nombre if self.perfil else "Sin perfil"
        return f"{self.cuento.titulo} - {perfil_name} - {self.tiempo_lectura}s"
