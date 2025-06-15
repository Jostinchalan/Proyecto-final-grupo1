import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.core.exceptions import ValidationError
from .models import Cuento, EstadisticaLectura
from .services import openai_service
from .utils import generar_pdf_cuento
from user.models import Perfil
import threading
import time

logger = logging.getLogger(__name__)


@login_required
def generated_story_view(request, cuento_id):
    """Vista para mostrar el cuento generado - SIN GUARDAR AUTOMÁTICAMENTE"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        logger.info(f"Mostrando cuento {cuento_id} con estado: {cuento.estado}")

        if cuento.estado == 'generando':
            return redirect('stories:generando')
        elif cuento.estado == 'error':
            messages.error(request, 'Hubo un error generando el cuento. Inténtalo de nuevo.')
            return redirect('stories:generar')

        # Marcar como leído
        cuento.marcar_como_leido()

        # Verificar que el cuento tenga contenido para TTS
        if not cuento.contenido or not cuento.contenido.strip():
            logger.warning(f"Cuento {cuento_id} no tiene contenido para TTS")

        # SOLO registrar estadística de lectura si está en biblioteca
        if cuento.en_biblioteca:
            EstadisticaLectura.objects.create(
                usuario=request.user,
                cuento=cuento,
                perfil=cuento.perfil,
                tipo_lectura='texto'
            )

        # Limpiar sesión
        if 'cuento_id' in request.session:
            del request.session['cuento_id']
        if 'datos_generacion' in request.session:
            del request.session['datos_generacion']

        return render(request, 'stories/generated_story.html', {
            'cuento': cuento
        })

    except Exception as e:
        logger.error(f"Error en generated_story_view: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar el cuento.')
        return redirect('stories:generar')


@login_required
def generar_cuento_view(request):
    """Vista para el formulario de generación de cuentos"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            perfil_id = request.POST.get('perfil_id')
            titulo = request.POST.get('titulo', '').strip()
            personaje = request.POST.get('personaje', '').strip()
            nuevo_personaje = request.POST.get('nuevo_personaje', '').strip()
            tema = request.POST.get('tema', '').strip()
            nuevo_tema = request.POST.get('nuevo_tema', '').strip()
            edad = request.POST.get('edad', '')
            longitud = request.POST.get('longitud', '')
            guardar_datos = request.POST.get('guardar_datos') == 'on'

            # Determinar personaje y tema finales
            personaje_final = nuevo_personaje if personaje == 'nuevo' and nuevo_personaje else personaje
            tema_final = nuevo_tema if tema == 'nuevo' and nuevo_tema else tema

            # Validar datos del formulario
            datos_formulario = {
                'titulo': titulo,
                'personaje_principal': personaje_final,
                'tema': tema_final,
                'edad': edad,
                'longitud': longitud,
            }

            # Validaciones básicas
            if not datos_formulario['personaje_principal']:
                messages.error(request, 'El personaje principal es requerido.')
                return render(request, 'stories/generar.html', {
                    'perfiles': Perfil.objects.filter(usuario=request.user)
                })

            if not datos_formulario['tema']:
                messages.error(request, 'Debes seleccionar un tema.')
                return render(request, 'stories/generar.html', {
                    'perfiles': Perfil.objects.filter(usuario=request.user)
                })

            if not datos_formulario['edad']:
                messages.error(request, 'Debes seleccionar la edad del niño.')
                return render(request, 'stories/generar.html', {
                    'perfiles': Perfil.objects.filter(usuario=request.user)
                })

            if not datos_formulario['longitud']:
                messages.error(request, 'Debes seleccionar la longitud del cuento.')
                return render(request, 'stories/generar.html', {
                    'perfiles': Perfil.objects.filter(usuario=request.user)
                })

            # Guardar nuevos datos en el perfil si está marcado
            if guardar_datos and perfil_id:
                try:
                    perfil = Perfil.objects.get(id=perfil_id, usuario=request.user)

                    # Agregar nuevo personaje si no existe
                    if nuevo_personaje and nuevo_personaje not in perfil.personajes_lista():
                        if perfil.personajes_favoritos:
                            perfil.personajes_favoritos += f", {nuevo_personaje}"
                        else:
                            perfil.personajes_favoritos = nuevo_personaje

                    # Agregar nuevo tema si no existe
                    if nuevo_tema and nuevo_tema not in perfil.temas_lista():
                        if perfil.temas_preferidos:
                            perfil.temas_preferidos += f", {nuevo_tema}"
                        else:
                            perfil.temas_preferidos = nuevo_tema

                    perfil.save()
                    messages.success(request, f'Nuevos datos guardados en el perfil de {perfil.nombre}')

                except Perfil.DoesNotExist:
                    pass

            # Obtener el perfil si existe
            perfil = None
            if perfil_id:
                try:
                    perfil = Perfil.objects.get(id=perfil_id, usuario=request.user)
                except Perfil.DoesNotExist:
                    perfil = None

            # Crear el cuento en estado "generando" SIN guardarlo en biblioteca
            cuento = Cuento.objects.create(
                usuario=request.user,
                perfil=perfil,
                titulo=datos_formulario['titulo'] or 'Cuento Mágico',
                personaje_principal=datos_formulario['personaje_principal'],
                tema=datos_formulario['tema'],
                edad=datos_formulario['edad'],
                longitud=datos_formulario['longitud'],
                estado='generando',
                en_biblioteca=False  # NO guardarlo automáticamente
            )

            logger.info(f"Cuento creado con ID: {cuento.id} para usuario: {request.user.username}")

            # Iniciar generación inmediatamente en background
            def generar_en_background():
                try:
                    logger.info(f"Iniciando generacion de cuento ID: {cuento.id}")

                    titulo, contenido, moraleja, imagen_url, imagen_prompt = openai_service.generar_cuento_completo(
                        datos_formulario, user=request.user)

                    # Actualizar el cuento
                    cuento.titulo = titulo
                    cuento.contenido = contenido
                    cuento.moraleja = moraleja
                    cuento.imagen_url = imagen_url
                    cuento.imagen_prompt = imagen_prompt
                    cuento.estado = 'completado'

                    # Calcular tiempo estimado de lectura
                    palabras = len(contenido.split())
                    cuento.tiempo_lectura_estimado = max(60, (palabras / 200) * 60)

                    cuento.save()

                    logger.info(f"Cuento generado exitosamente: {titulo}")

                except Exception as e:
                    logger.error(f"Error generando cuento en background: {str(e)}")
                    cuento.estado = 'error'
                    cuento.save()

            # Iniciar thread
            thread = threading.Thread(target=generar_en_background)
            thread.daemon = True
            thread.start()

            # Guardar datos en sesión y redirigir
            request.session['datos_generacion'] = datos_formulario
            request.session['cuento_id'] = cuento.id

            return redirect('stories:generando')

        except Exception as e:
            logger.error(f"Error en generar_cuento_view: {str(e)}")
            messages.error(request, 'Ocurrió un error al procesar tu solicitud. Inténtalo de nuevo.')
            return render(request, 'stories/generar.html', {
                'perfiles': Perfil.objects.filter(usuario=request.user)
            })

    # GET request - mostrar formulario
    perfiles = Perfil.objects.filter(usuario=request.user)
    return render(request, 'stories/generar.html', {
        'perfiles': perfiles
    })


@login_required
def generando_cuento_view(request):
    """Vista para la página de carga mientras se genera el cuento"""
    cuento_id = request.session.get('cuento_id')
    datos_formulario = request.session.get('datos_generacion')

    if not cuento_id or not datos_formulario:
        messages.error(request, 'No se encontraron datos de generación.')
        return redirect('stories:generar')

    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        logger.info(f"Estado actual del cuento {cuento.id}: {cuento.estado}")

        # Si el cuento ya está completado, redirigir inmediatamente
        if cuento.estado == 'completado':
            logger.info(f"Cuento {cuento.id} completado, redirigiendo...")
            # Limpiar sesión
            if 'cuento_id' in request.session:
                del request.session['cuento_id']
            if 'datos_generacion' in request.session:
                del request.session['datos_generacion']
            return redirect('stories:generated_story', cuento_id=cuento.id)

        # Si hay error, redirigir a generar
        if cuento.estado == 'error':
            logger.error(f"Cuento {cuento.id} tiene error")
            messages.error(request, 'Hubo un error generando el cuento. Inténtalo de nuevo.')
            return redirect('stories:generar')

        return render(request, 'stories/generando.html', {
            'cuento': cuento,
            'datos_formulario': datos_formulario
        })

    except Exception as e:
        logger.error(f"Error en generando_cuento_view: {str(e)}")
        messages.error(request, 'Ocurrió un error durante la generación.')
        return redirect('stories:generar')


@login_required
def check_cuento_status(request, cuento_id):
    """Vista AJAX para verificar el estado del cuento"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        logger.info(f"Verificando estado del cuento {cuento_id}: {cuento.estado}")

        return JsonResponse({
            'estado': cuento.estado,
            'completado': cuento.estado == 'completado',
            'error': cuento.estado == 'error',
            'titulo': cuento.titulo,
            'debug_info': {
                'cuento_id': cuento.id,
                'usuario': cuento.usuario.username,
                'fecha_creacion': cuento.fecha_creacion.isoformat(),
                'contenido_length': len(cuento.contenido) if cuento.contenido else 0
            }
        })

    except Exception as e:
        logger.error(f"Error verificando estado del cuento {cuento_id}: {str(e)}")
        return JsonResponse({
            'estado': 'error',
            'completado': False,
            'error': True,
            'mensaje': str(e)
        })


@login_required
def descargar_pdf_view(request, cuento_id):
    """Vista para descargar el cuento en PDF - VERSIÓN COMPLETAMENTE CORREGIDA"""
    try:
        # Obtener el cuento
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        logger.info(f"🔽 DESCARGA PDF - Cuento ID: {cuento_id}, Título: {cuento.titulo}")
        logger.info(f"🔽 Usuario: {request.user.username}")
        logger.info(f"🔽 Estado del cuento: {cuento.estado}")

        # Verificar que el cuento esté completado
        if cuento.estado != 'completado':
            logger.error(f"❌ Cuento {cuento_id} no está completado, estado: {cuento.estado}")
            messages.error(request, 'El cuento no está listo para descargar.')
            return redirect('stories:generated_story', cuento_id=cuento_id)

        # Verificar que tenga contenido
        if not cuento.contenido or not cuento.contenido.strip():
            logger.error(f"❌ Cuento {cuento_id} no tiene contenido")
            messages.error(request, 'El cuento no tiene contenido para descargar.')
            return redirect('stories:generated_story', cuento_id=cuento_id)

        logger.info(f"✅ Cuento válido para descarga - Contenido: {len(cuento.contenido)} caracteres")

        # Generar PDF
        try:
            logger.info(f"📄 Generando PDF para: {cuento.titulo}")
            pdf_buffer = generar_pdf_cuento(cuento)

            if not pdf_buffer:
                raise Exception("PDF buffer is None")

            pdf_content = pdf_buffer.getvalue()

            if not pdf_content:
                raise Exception("PDF content is empty")

            logger.info(f"✅ PDF generado exitosamente, tamaño: {len(pdf_content)} bytes")

        except Exception as pdf_error:
            logger.error(f"❌ Error generando PDF: {str(pdf_error)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            messages.error(request, 'Error al generar el archivo PDF.')
            return redirect('stories:generated_story', cuento_id=cuento_id)

        # Crear respuesta HTTP con headers correctos para FORZAR DESCARGA
        response = HttpResponse(pdf_content, content_type='application/pdf')

        # Nombre de archivo seguro (sin caracteres especiales)
        titulo_limpio = cuento.titulo.replace(' ', '_').replace('/', '_').replace('\\', '_')
        titulo_limpio = ''.join(c for c in titulo_limpio if c.isalnum() or c in ['_', '-'])
        filename = f"CuentIA_{titulo_limpio}.pdf"

        # Headers CRÍTICOS para forzar descarga
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/pdf'
        response['Content-Length'] = len(pdf_content)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        # Headers adicionales para asegurar descarga
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Transfer-Encoding'] = 'binary'

        # Registrar estadística de descarga
        try:
            EstadisticaLectura.objects.create(
                usuario=request.user,
                cuento=cuento,
                perfil=cuento.perfil,
                tipo_lectura='descarga'
            )
            logger.info(f"📊 Estadística de descarga registrada para cuento {cuento_id}")
        except Exception as stats_error:
            logger.warning(f"⚠️ Error registrando estadística de descarga: {str(stats_error)}")

        logger.info(f"🎉 PDF listo para descarga: {filename}")
        logger.info(f"🎉 Headers de respuesta: {dict(response.items())}")

        return response

    except Exception as e:
        logger.error(f"❌ Error general en descarga PDF: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
        messages.error(request, f'Error al descargar el cuento: {str(e)}')
        return redirect('stories:generated_story', cuento_id=cuento_id)


@login_required
@require_POST
def toggle_favorito_view(request, cuento_id):
    """Vista AJAX para alternar favorito"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)
        es_favorito = cuento.toggle_favorito()

        return JsonResponse({
            'success': True,
            'es_favorito': es_favorito,
            'message': 'Agregado a favoritos' if es_favorito else 'Removido de favoritos'
        })

    except Exception as e:
        logger.error(f"Error toggle favorito: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error al actualizar favorito'
        })


@login_required
@require_POST
def guardar_biblioteca_view(request, cuento_id):
    """Vista para guardar el cuento en la biblioteca - CON CONFIRMACIÓN"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        # Verificar si ya está en biblioteca
        if cuento.en_biblioteca:
            return JsonResponse({
                'success': True,
                'already_saved': True,
                'message': f'El cuento "{cuento.titulo}" ya está en tu biblioteca.'
            })

        # Guardar en biblioteca
        cuento.guardar_en_biblioteca()

        # Registrar estadística
        EstadisticaLectura.objects.create(
            usuario=request.user,
            cuento=cuento,
            perfil=cuento.perfil,
            tipo_lectura='biblioteca'
        )

        logger.info(f"Cuento guardado en biblioteca: {cuento.titulo} por {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': f'¡Cuento "{cuento.titulo}" guardado en tu biblioteca!',
            'redirect_url': '/library/'
        })

    except Exception as e:
        logger.error(f"Error guardando en biblioteca: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error al guardar en la biblioteca.'
        })


@login_required
@require_POST
def eliminar_cuento(request, cuento_id):
    """Vista para eliminar un cuento"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)
        titulo = cuento.titulo

        # Eliminar el cuento
        cuento.delete()

        return JsonResponse({
            'success': True,
            'message': f'Cuento "{titulo}" eliminado correctamente'
        })

    except Exception as e:
        logger.error(f"Error al eliminar cuento {cuento_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error al eliminar el cuento: {str(e)}'
        })


@login_required
def obtener_contenido_cuento(request, cuento_id):
    """Vista para obtener el contenido de un cuento para reproducción"""
    try:
        cuento = get_object_or_404(Cuento, id=cuento_id, usuario=request.user)

        return JsonResponse({
            'success': True,
            'contenido': cuento.contenido,
            'titulo': cuento.titulo
        })

    except Exception as e:
        logger.error(f"Error al obtener contenido del cuento {cuento_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener el contenido: {str(e)}'
        })
