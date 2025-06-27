# user/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import json
import logging
import time
import socket
import re
from datetime import datetime

from .forms import (
    PerfilForm, RegistroForm, LoginForm, UserUpdateForm,
    ProfileUpdateForm, SettingsUpdateForm, CustomPasswordChangeForm
)
from .models import Perfil, UserProfile, UserSettings
from .email_utils import enviar_correo_bienvenida_async

logger = logging.getLogger(__name__)


@login_required
def create_perfil(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.usuario = request.user
            perfil.save()
            messages.success(request, f'¡Perfil de {perfil.nombre} creado exitosamente!')
            return redirect('user:perfil_list')
    else:
        storage = messages.get_messages(request)
        storage.used = True
        form = PerfilForm()

    return render(request, 'user/create_perfil.html', {'form': form})


@login_required
def editar_perfil(request, pk):
    """Vista para editar un perfil existente"""
    perfil = get_object_or_404(Perfil, pk=pk, usuario=request.user)

    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Perfil de {perfil.nombre} actualizado exitosamente!')
            return redirect('user:perfil_list')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        storage = messages.get_messages(request)
        storage.used = True
        form = PerfilForm(instance=perfil)

    return render(request, 'user/editar_perfil.html', {
        'form': form,
        'perfil': perfil,
        'is_editing': True
    })


@login_required
def eliminar_perfil(request, pk):
    """Vista para eliminar un perfil"""
    perfil = get_object_or_404(Perfil, pk=pk, usuario=request.user)

    if request.method == 'POST':
        nombre_perfil = perfil.nombre
        perfil.delete()
        messages.success(request, f'Perfil de {nombre_perfil} eliminado exitosamente.')
        return redirect('user:perfil_list')

    return render(request, 'user/eliminar_perfil.html', {'perfil': perfil})


@login_required
@require_POST
def eliminar_perfil_ajax(request, pk):
    """Vista AJAX para eliminar perfil con confirmación"""
    try:
        perfil = get_object_or_404(Perfil, pk=pk, usuario=request.user)
        nombre_perfil = perfil.nombre
        perfil.delete()

        return JsonResponse({
            'success': True,
            'message': f'Perfil de {nombre_perfil} eliminado exitosamente.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error al eliminar el perfil. Inténtalo de nuevo.'
        })


@login_required
def perfil_list(request):
    """Vista para listar perfiles infantiles"""
    perfiles = Perfil.objects.filter(usuario=request.user)
    return render(request, 'user/perfil_list.html', {'perfiles': perfiles})


@login_required
@csrf_exempt
@require_POST
def upload_perfil_photo(request, pk=None):
    """Vista AJAX para subir foto de perfil infantil"""
    try:
        if pk:
            perfil = get_object_or_404(Perfil, pk=pk, usuario=request.user)
        else:
            perfil = None

        if 'foto_perfil' in request.FILES:
            foto = request.FILES['foto_perfil']

            if foto.size > 5 * 1024 * 1024:  # 5MB
                return JsonResponse({
                    'success': False,
                    'message': 'La imagen no puede ser mayor a 5MB.'
                })

            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if not any(foto.name.lower().endswith(ext) for ext in valid_extensions):
                return JsonResponse({
                    'success': False,
                    'message': 'Solo se permiten archivos JPG, JPEG, PNG o GIF.'
                })

            if perfil:
                perfil.foto_perfil = foto
                perfil.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Foto actualizada exitosamente.',
                    'foto_url': perfil.foto_perfil.url
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Foto cargada temporalmente.',
                    'foto_url': '/media/temp/placeholder.jpg'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se recibió ninguna imagen.'
            })

    except Exception as e:
        logger.error(f"Error al subir foto de perfil: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error al procesar la imagen.'
        })


class ContraseñaConf(PasswordResetConfirmView):
    template_name = 'user/password_reset/password_reset_confirm.html'
    success_url = reverse_lazy('user:login')

    def form_valid(self, form):
        messages.success(self.request, "¡Contraseña cambiada exitosamente! Ahora podés iniciar sesión.")
        return super().form_valid(form)


def logout_view(request):
    logout(request)
    return redirect('landing')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('user:loading')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            send_login_notification(form.get_user(), request)

            return redirect('user:loading')
    else:
        form = LoginForm()

    return render(request, 'user/login.html', {'form': form})


def registro_view(request):
    """Vista para la página de registro con envío automático de correo de bienvenida"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')

            print(f"🔄 Usuario creado: {username} - Email: {email}")

            try:
                from .email_utils import enviar_correo_bienvenida_async
                enviar_correo_bienvenida_async(user)
                print(f"📧 Proceso de envío de correo iniciado para {email}")
                logger.info(f"Proceso de envío de correo iniciado para {email}")
            except Exception as e:
                print(f"❌ Error al iniciar envío de correo para {email}: {str(e)}")
                logger.error(f"Error al iniciar envío de correo para {email}: {str(e)}")

            messages.success(
                request,
                f'¡Cuenta creada para {username}! Te hemos enviado un correo de bienvenida a {email}.'
            )
            return redirect('user:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = RegistroForm()

    return render(request, 'user/register.html', {'form': form})


@login_required
def loading_view(request):
    """Vista para la pantalla de carga después del login"""
    return render(request, 'user/loading.html')


@login_required
def dashboard_data_view(request):
    """Vista que simula la carga de datos del dashboard"""
    time.sleep(2)

    data = {
        'success': True,
        'message': 'Datos cargados exitosamente',
        'redirect_url': '/dashboard/'
    }

    return JsonResponse(data)


@login_required
def settings_view(request):
    """Vista mejorada para configuraciones con guardado persistente"""
    # Asegurar que el usuario tenga configuraciones
    settings_obj, created = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        print(f"🔧 Procesando formulario tipo: {form_type}")
        print(f"📦 Datos POST recibidos: {dict(request.POST)}")

        if form_type == 'avatar':
            # Manejar solo la subida de avatar
            if 'avatar' in request.FILES:
                settings_obj.avatar = request.FILES['avatar']
                settings_obj.save()
                messages.success(request, 'Foto de perfil actualizada exitosamente.')
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No se recibió ninguna imagen'})

        elif form_type == 'password':
            # Manejar cambio de contraseña
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada exitosamente.')
                return redirect('user:settings')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, f"Error en {field}: {error}")

        else:
            # MANEJAR ACTUALIZACIÓN DE PERFIL PRINCIPAL (username y email)
            print("👤 Procesando actualización de perfil principal")

            # Obtener datos del formulario
            new_username = request.POST.get('username', '').strip()
            new_email = request.POST.get('email', '').strip()

            print(f"📝 Nuevo username: {new_username}")
            print(f"📧 Nuevo email: {new_email}")
            print(f"🔍 Username actual: {request.user.username}")
            print(f"🔍 Email actual: {request.user.email}")

            # Validaciones
            errors = []

            # Validar username
            if not new_username:
                errors.append("El nombre de usuario es requerido.")
            elif new_username != request.user.username:
                # Verificar que no exista otro usuario con ese username
                from django.contrib.auth.models import User
                if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                    errors.append("Este nombre de usuario ya está en uso.")

            # Validar email
            if not new_email:
                errors.append("El correo electrónico es requerido.")
            elif new_email != request.user.email:
                # Verificar formato de email
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, new_email):
                    errors.append("Formato de correo electrónico inválido.")
                else:
                    # Verificar que no exista otro usuario con ese email
                    from django.contrib.auth.models import User
                    if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                        errors.append("Este correo electrónico ya está registrado.")

            if errors:
                for error in errors:
                    messages.error(request, error)
                print(f"❌ Errores de validación: {errors}")
            else:
                # GUARDAR CAMBIOS EN LA BASE DE DATOS
                try:
                    # Actualizar usuario
                    user = request.user
                    user.username = new_username
                    user.email = new_email
                    user.save()

                    print(f"✅ Usuario actualizado exitosamente")
                    print(f"✅ Nuevo username en BD: {user.username}")
                    print(f"✅ Nuevo email en BD: {user.email}")

                    # Verificar que se guardó correctamente
                    user.refresh_from_db()
                    print(f"🔍 Verificación - Username en BD: {user.username}")
                    print(f"🔍 Verificación - Email en BD: {user.email}")

                    messages.success(request, 'Información personal actualizada exitosamente.')

                    # Log para auditoría
                    logger.info(
                        f"Usuario {request.user.pk} actualizó su perfil - Username: {new_username}, Email: {new_email}")

                    return redirect('user:settings')

                except Exception as e:
                    error_msg = f"Error al guardar los cambios: {str(e)}"
                    messages.error(request, error_msg)
                    print(f"❌ {error_msg}")
                    logger.error(f"Error actualizando perfil de usuario {request.user.pk}: {str(e)}")

    # Preparar formularios para GET request
    user_form = UserUpdateForm(instance=request.user)
    settings_form = SettingsUpdateForm(instance=settings_obj)
    password_form = CustomPasswordChangeForm(request.user)

    context = {
        'user_form': user_form,
        'settings_form': settings_form,
        'password_form': password_form,
    }

    return render(request, 'user/settings.html', context)


@login_required
@csrf_exempt
def update_preferences(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            settings_obj, created = UserSettings.objects.get_or_create(user=request.user)

            logger.info(f"🔧 Actualizando preferencias para usuario: {request.user.username}")
            logger.info(f"📦 Datos recibidos: {data}")

            if 'email_notifications' in data:
                settings_obj.email_notifications = data['email_notifications']
                logger.info(f"📧 Email notifications: {data['email_notifications']}")

            if 'dark_mode' in data:
                settings_obj.dark_mode = data['dark_mode']
                logger.info(f"🌙 Dark mode: {data['dark_mode']}")

            if 'language' in data:
                nuevo_idioma = data['language']
                idiomas_validos = ['es', 'en', 'de', 'fr']

                if nuevo_idioma in idiomas_validos:
                    settings_obj.language = nuevo_idioma
                    logger.info(f"🌍 Idioma cambiado a: {nuevo_idioma} para usuario {request.user.username}")
                else:
                    logger.warning(f"⚠️ Idioma inválido recibido: {nuevo_idioma}")
                    return JsonResponse({'status': 'error', 'message': f'Idioma no válido: {nuevo_idioma}'})

            settings_obj.save()
            logger.info(f"✅ Configuraciones guardadas exitosamente para {request.user.username}")

            settings_verificacion = UserSettings.objects.get(user=request.user)
            logger.info(f"🔍 Verificación - Idioma en BD: {settings_verificacion.language}")

            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"❌ Error actualizando preferencias para {request.user.username}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def verify_user_data(request):
    """Vista para verificar que los datos del usuario están actualizados"""
    user = request.user
    user.refresh_from_db()

    data = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }

    return JsonResponse(data)


@login_required
@csrf_exempt
@require_POST
def validate_username(request):
    """Validar nombre de usuario en tiempo real"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()

        if not username:
            return JsonResponse({
                'valid': False,
                'message': 'El nombre de usuario es requerido.'
            })

        if username == request.user.username:
            return JsonResponse({
                'valid': False,
                'message': 'El nuevo nombre debe ser diferente al actual.'
            })

        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
            return JsonResponse({
                'valid': False,
                'message': 'Este nombre de usuario ya está en uso.'
            })

        return JsonResponse({
            'valid': True,
            'message': 'Nombre de usuario disponible.'
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'Error al validar el nombre de usuario.'
        })


@login_required
@csrf_exempt
@require_POST
def validate_email(request):
    """Validar email en tiempo real"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()

        if not email:
            return JsonResponse({
                'valid': False,
                'message': 'El correo electrónico es requerido.'
            })

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return JsonResponse({
                'valid': False,
                'message': 'Formato de correo electrónico inválido.'
            })

        if email == request.user.email:
            return JsonResponse({
                'valid': False,
                'message': 'El nuevo correo debe ser diferente al actual.'
            })

        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
            return JsonResponse({
                'valid': False,
                'message': 'Este correo electrónico ya está registrado.'
            })

        return JsonResponse({
            'valid': True,
            'message': 'Correo electrónico disponible.'
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'Error al validar el correo electrónico.'
        })


@login_required
@csrf_exempt
@require_POST
def validate_current_password(request):
    """Validar contraseña actual en tiempo real"""
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password', '')

        if not current_password:
            return JsonResponse({
                'valid': False,
                'message': 'La contraseña actual es requerida.'
            })

        if not request.user.check_password(current_password):
            return JsonResponse({
                'valid': False,
                'message': 'Contraseña actual incorrecta!'
            })

        return JsonResponse({
            'valid': True,
            'message': 'Contraseña actual correcta.'
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'Error al validar la contraseña actual.'
        })


@login_required
@csrf_exempt
@require_POST
def validate_new_password(request):
    """Validar nueva contraseña en tiempo real"""
    try:
        data = json.loads(request.body)
        new_password = data.get('new_password', '')

        if not new_password:
            return JsonResponse({
                'valid': False,
                'message': 'La nueva contraseña es requerida.'
            })

        errors = []

        if len(new_password) < 8:
            errors.append("Debe tener al menos 8 caracteres")

        if not re.search(r'[A-Z]', new_password):
            errors.append("Debe contener al menos una mayúscula")

        if not re.search(r'[a-z]', new_password):
            errors.append("Debe contener al menos una minúscula")

        if not re.search(r'\d', new_password):
            errors.append("Debe contener al menos un número")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            errors.append("Debe contener al menos un carácter especial")

        if request.user.check_password(new_password):
            errors.append("Debe ser diferente a la contraseña actual")

        if errors:
            return JsonResponse({
                'valid': False,
                'message': 'Contraseña inválida!',
                'errors': errors
            })

        return JsonResponse({
            'valid': True,
            'message': 'Contraseña válida.'
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'Error al validar la nueva contraseña.'
        })


@login_required
@csrf_exempt
@require_POST
def validate_confirm_password(request):
    """Validar confirmación de contraseña en tiempo real"""
    try:
        data = json.loads(request.body)
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not confirm_password:
            return JsonResponse({
                'valid': False,
                'message': 'La confirmación de contraseña es requerida.'
            })

        if new_password != confirm_password:
            return JsonResponse({
                'valid': False,
                'message': 'Contraseñas no coinciden!'
            })

        return JsonResponse({
            'valid': True,
            'message': 'Las contraseñas coinciden.'
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'Error al validar la confirmación de contraseña.'
        })


def get_client_ip(request):
    """Obtener la IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_device_info(request):
    """Extraer información del dispositivo desde el User-Agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    browser = 'Desconocido'
    if 'Chrome' in user_agent:
        browser = 'Google Chrome'
    elif 'Firefox' in user_agent:
        browser = 'Mozilla Firefox'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser = 'Safari'
    elif 'Edge' in user_agent:
        browser = 'Microsoft Edge'
    elif 'Opera' in user_agent:
        browser = 'Opera'

    os = 'Desconocido'
    if 'Windows' in user_agent:
        os = 'Windows'
    elif 'Mac' in user_agent:
        os = 'macOS'
    elif 'Linux' in user_agent:
        os = 'Linux'
    elif 'Android' in user_agent:
        os = 'Android'
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        os = 'iOS'

    device = 'Computadora'
    if 'Mobile' in user_agent or 'Android' in user_agent:
        device = 'Móvil'
    elif 'Tablet' in user_agent or 'iPad' in user_agent:
        device = 'Tablet'

    return {
        'browser': browser,
        'os': os,
        'device': device,
        'user_agent': user_agent
    }


def get_hostname_from_ip(ip_address):
    """Obtener hostname desde la IP (ubicación aproximada)"""
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except:
        return f"IP: {ip_address}"


def send_login_notification(user, request):
    """Función mejorada para enviar notificación de login con HTML"""
    try:
        settings_obj, created = UserSettings.objects.get_or_create(user=user)

        if settings_obj.email_notifications:
            print(f"📧 Enviando notificación de login para {user.username}")

            ip_address = get_client_ip(request)
            device_info = get_device_info(request)
            hostname = get_hostname_from_ip(ip_address)
            current_time = datetime.now()

            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'CuentIA'),
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                'timestamp': current_time,
                'ip_address': ip_address,
                'device_info': device_info,
                'hostname': hostname,
            }

            subject = f'🔐 Nuevo inicio de sesión detectado - {context["site_name"]}'

            try:
                html_content = render_to_string('user/email/notification.html', context)
                print("✅ Template HTML de notificación renderizado correctamente")
            except Exception as e:
                print(f"❌ Error renderizando template HTML de notificación: {e}")
                html_content = None

            try:
                text_content = render_to_string('user/email/notification.txt', context)
                print("✅ Template TXT de notificación renderizado correctamente")
            except Exception as e:
                print(f"❌ Error renderizando template TXT de notificación: {e}")
                text_content = f"""
🔐 {context['site_name']} - Nuevo inicio de sesión detectado

¡Hola {user.username}!

Hemos detectado un nuevo inicio de sesión en tu cuenta el {current_time.strftime('%d/%m/%Y a las %H:%M:%S')}.

DETALLES:
- IP: {ip_address}
- Dispositivo: {device_info['device']}
- Navegador: {device_info['browser']}
- Sistema: {device_info['os']}

Si no fuiste tú, cambia tu contraseña inmediatamente.

El equipo de {context['site_name']}
                """

            print(f"📧 Preparando email de notificación para {user.email}")

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            if html_content:
                email.attach_alternative(html_content, "text/html")

            print("📤 Enviando email de notificación...")

            result = email.send(fail_silently=False)

            if result:
                print(f"✅ Notificación de login enviada exitosamente a {user.email}")
                logger.info(f"✅ Notificación de login enviada exitosamente a {user.email}")
                logger.info(
                    f"🔐 Login detectado - Usuario: {user.username}, IP: {ip_address}, Dispositivo: {device_info['device']}, Navegador: {device_info['browser']}, Hora: {current_time.strftime('%d/%m/%Y %H:%M:%S')}")
            else:
                print(f"❌ No se pudo enviar la notificación a {user.email}")
                logger.error(f"❌ No se pudo enviar la notificación a {user.email}")

    except Exception as e:
        error_msg = f"❌ Error enviando notificación de login a {user.email}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
