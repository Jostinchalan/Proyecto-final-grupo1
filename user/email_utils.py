# user/email_utils.py (versión mejorada y simplificada)
# user/email_utils.py (versión mejorada y simplificada)
from django.core.mail import get_connection
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
import traceback

logger = logging.getLogger(__name__)


def enviar_correo_bienvenida_async(user):
    """Envía correo de bienvenida de forma síncrona (más confiable)"""
    try:
        print(f"🔄 Iniciando envío de correo de bienvenida para {user.email}")

        # Contexto para el template
        context = {
            'user': user,
            'site_name': getattr(settings, 'SITE_NAME', 'CuentIA'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }

        # Renderizar templates
        subject = f'¡Bienvenido a {context["site_name"]}!'

        try:
            html_content = render_to_string('user/email/bienvenida.html', context)
            print("✅ Template HTML renderizado correctamente")
        except Exception as e:
            print(f"❌ Error renderizando template HTML: {e}")
            html_content = None

        try:
            text_content = render_to_string('user/email/bienvenida.txt', context)
            print("✅ Template TXT renderizado correctamente")
        except Exception as e:
            print(f"❌ Error renderizando template TXT: {e}")
            # Fallback a texto simple
            text_content = f"""
¡Hola {user.username}!

¡Bienvenido a {context['site_name']}! 🎉

Tu cuenta ha sido creada exitosamente. Ya puedes comenzar a crear cuentos personalizados.

Visita: {context['site_url']}

¡Gracias por unirte a nosotros!

El equipo de {context['site_name']} 🤖✨
            """

        print(f"📧 Preparando email para {user.email}")

        # Crear email
        if html_content:
            # Email con HTML y texto
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
        else:
            # Solo texto si hay problemas con HTML
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

        print("📤 Enviando email...")

        # Enviar email
        result = email.send(fail_silently=False)

        if result:
            print(f"✅ Correo de bienvenida enviado exitosamente a {user.email}")
            logger.info(f"✅ Correo de bienvenida enviado exitosamente a {user.email}")
        else:
            print(f"❌ No se pudo enviar el correo a {user.email}")
            logger.error(f"❌ No se pudo enviar el correo a {user.email}")

    except Exception as e:
        error_msg = f"❌ Error enviando correo de bienvenida a {user.email}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)


def enviar_correo_reset_async(user, uid, token, domain, protocol):
    """Envía correo de reset de contraseña de forma síncrona"""
    try:
        print(f"🔄 Iniciando envío de correo de reset para {user.email}")

        # Contexto para el template
        context = {
            'user': user,
            'uid': uid,
            'token': token,
            'domain': domain,
            'protocol': protocol,
            'site_name': getattr(settings, 'SITE_NAME', 'CuentIA'),
        }

        # Renderizar templates
        subject = f'Restablecer contraseña - {context["site_name"]}'

        try:
            html_content = render_to_string('user/password_reset/password_reset_email.html', context)
            print("✅ Template HTML de reset renderizado correctamente")
        except Exception as e:
            print(f"❌ Error renderizando template HTML de reset: {e}")
            html_content = None

        try:
            text_content = render_to_string('user/password_reset/password_reset_email.txt', context)
            print("✅ Template TXT de reset renderizado correctamente")
        except Exception as e:
            print(f"❌ Error renderizando template TXT de reset: {e}")
            # Fallback a texto simple
            text_content = f"""
Hola {user.username},

Has solicitado restablecer tu contraseña en {context['site_name']}.

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{protocol}://{domain}/user/reset/{uid}/{token}/

Si no solicitaste este cambio, puedes ignorar este correo.

El equipo de {context['site_name']}
            """

        print(f"📧 Preparando email de reset para {user.email}")

        # Crear email
        if html_content:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
        else:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

        print("📤 Enviando email de reset...")

        # Enviar email
        result = email.send(fail_silently=False)

        if result:
            print(f"✅ Correo de reset enviado exitosamente a {user.email}")
            logger.info(f"✅ Correo de reset enviado exitosamente a {user.email}")
        else:
            print(f"❌ No se pudo enviar el correo de reset a {user.email}")
            logger.error(f"❌ No se pudo enviar el correo de reset a {user.email}")

    except Exception as e:
        error_msg = f"❌ Error enviando correo de reset a {user.email}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)


def test_email_connection():
    """Función para probar la conexión de email"""
    try:
        print("🔄 Probando conexión de email...")
        print(f"📧 Host: {settings.EMAIL_HOST}")
        print(f"📧 Port: {settings.EMAIL_PORT}")
        print(f"📧 User: {settings.EMAIL_HOST_USER}")
        print(f"📧 Use TLS: {settings.EMAIL_USE_TLS}")

        connection = get_connection()
        connection.open()
        print("✅ Conexión de email exitosa")
        connection.close()
        return True

    except Exception as e:
        print(f"❌ Error en conexión de email: {str(e)}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False
