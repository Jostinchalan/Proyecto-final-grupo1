from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.flowables import HRFlowable
from io import BytesIO
import requests
from PIL import Image as PILImage
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)


def get_longitud_display(longitud_value):
    """
    Función auxiliar para obtener el display de longitud
    """
    longitud_choices = {
        'corto': 'Corto (1-2 minutos)',
        'medio': 'Medio (3-5 minutos)',
        'largo': 'Largo (5+ minutos)',
        'muy_corto': 'Muy Corto (menos de 1 minuto)',
        'muy_largo': 'Muy Largo (10+ minutos)'
    }

    return longitud_choices.get(longitud_value, longitud_value.title() if longitud_value else 'No especificado')


def generar_pdf_cuento(cuento):
    """Genera un PDF atractivo y profesional del cuento"""
    try:
        logger.info(f"🔄 Iniciando generación de PDF para cuento: {cuento.titulo}")

        buffer = BytesIO()

        # Crear documento PDF con márgenes personalizados
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Estilos personalizados
        styles = getSampleStyleSheet()

        # Estilo para el título principal
        titulo_style = ParagraphStyle(
            'TituloCustom',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7C3AED'),
            fontName='Helvetica-Bold',
            leading=32
        )

        # Estilo para subtítulos
        subtitulo_style = ParagraphStyle(
            'SubtituloCustom',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#6B7280'),
            fontName='Helvetica-Bold'
        )

        # Estilo para el contenido del cuento
        contenido_style = ParagraphStyle(
            'ContenidoCustom',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=16,
            alignment=TA_JUSTIFY,
            leftIndent=20,
            rightIndent=20,
            fontName='Helvetica',
            leading=20
        )

        # Estilo para la moraleja
        moraleja_style = ParagraphStyle(
            'MoralejaCustom',
            parent=styles['Normal'],
            fontSize=13,
            spaceAfter=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#059669'),
            fontName='Helvetica-Oblique',
            borderWidth=2,
            borderColor=colors.HexColor('#10B981'),
            borderPadding=15,
            backColor=colors.HexColor('#ECFDF5'),
            leading=18
        )

        # Estilo para metadatos
        meta_style = ParagraphStyle(
            'MetaCustom',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#9CA3AF'),
            fontName='Helvetica'
        )

        # Contenido del PDF
        story = []

        # Encabezado decorativo
        story.append(Spacer(1, 20))

        # Logo/Marca
        story.append(Paragraph("✨ CuentIA ✨", subtitulo_style))
        story.append(Spacer(1, 10))

        # Línea decorativa
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#7C3AED')))
        story.append(Spacer(1, 30))

        # Título del cuento
        story.append(Paragraph(cuento.titulo.upper(), titulo_style))
        story.append(Spacer(1, 20))

        # Metadatos del cuento - CORREGIDO
        try:
            tema_display = cuento.get_tema_display() if hasattr(cuento, 'get_tema_display') else cuento.tema
        except:
            tema_display = cuento.tema if hasattr(cuento, 'tema') else 'No especificado'

        try:
            edad_display = cuento.edad if hasattr(cuento, 'edad') else 'No especificado'
        except:
            edad_display = 'No especificado'

        meta_info = f"""
        <b>Personaje Principal:</b> {cuento.personaje_principal}<br/>
        <b>Tema:</b> {tema_display}<br/>
        <b>Edad Recomendada:</b> {edad_display}<br/>
        <b>Fecha de Creación:</b> {cuento.fecha_creacion.strftime('%d de %B de %Y')}
        """
        story.append(Paragraph(meta_info, meta_style))
        story.append(Spacer(1, 30))

        # Imagen del cuento (si existe)
        if hasattr(cuento, 'imagen_url') and cuento.imagen_url and not cuento.imagen_url.startswith('/static'):
            try:
                # Descargar imagen
                response = requests.get(cuento.imagen_url, timeout=15)
                if response.status_code == 200:
                    img_buffer = BytesIO(response.content)

                    # Procesar imagen con PIL
                    pil_img = PILImage.open(img_buffer)

                    # Calcular dimensiones manteniendo aspecto
                    max_width = 5 * inch
                    max_height = 4 * inch

                    img_width, img_height = pil_img.size
                    aspect_ratio = img_width / img_height

                    if aspect_ratio > max_width / max_height:
                        new_width = max_width
                        new_height = max_width / aspect_ratio
                    else:
                        new_height = max_height
                        new_width = max_height * aspect_ratio

                    # Crear imagen para ReportLab
                    img_buffer.seek(0)
                    img = Image(img_buffer, width=new_width, height=new_height)
                    img.hAlign = 'CENTER'

                    story.append(img)
                    story.append(Spacer(1, 30))

            except Exception as e:
                logger.error(f"Error agregando imagen al PDF: {str(e)}")
                # Agregar placeholder si falla la imagen
                story.append(Paragraph("📚 Ilustración del Cuento 📚", subtitulo_style))
                story.append(Spacer(1, 20))

        # Línea decorativa antes del contenido
        story.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor('#E5E7EB')))
        story.append(Spacer(1, 20))

        # Contenido del cuento
        story.append(Paragraph("<b>Historia:</b>", subtitulo_style))
        story.append(Spacer(1, 15))

        # Dividir contenido en párrafos
        if hasattr(cuento, 'contenido') and cuento.contenido:
            paragrafos = cuento.contenido.split('\n\n')
            for i, paragrafo in enumerate(paragrafos):
                if paragrafo.strip():
                    # Agregar letra capital al primer párrafo
                    if i == 0 and len(paragrafo.strip()) > 0:
                        primera_letra = paragrafo.strip()[0].upper()
                        resto_texto = paragrafo.strip()[1:]
                        paragrafo_formateado = f'<font size="24" color="#7C3AED"><b>{primera_letra}</b></font>{resto_texto}'
                        story.append(Paragraph(paragrafo_formateado, contenido_style))
                    else:
                        story.append(Paragraph(paragrafo.strip(), contenido_style))
                    story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("Contenido no disponible", contenido_style))

        # Moraleja
        if hasattr(cuento, 'moraleja') and cuento.moraleja:
            story.append(Spacer(1, 30))
            story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor('#10B981')))
            story.append(Spacer(1, 20))

            moraleja_texto = f"<b>✨ Moraleja ✨</b><br/><br/>{cuento.moraleja}"
            story.append(Paragraph(moraleja_texto, moraleja_style))

        # Pie de página
        story.append(Spacer(1, 40))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E7EB')))
        story.append(Spacer(1, 20))

        # Información adicional - CORREGIDO
        try:
            # Obtener longitud de forma segura
            if hasattr(cuento, 'get_longitud_display'):
                longitud_display = cuento.get_longitud_display()
            elif hasattr(cuento, 'longitud'):
                longitud_display = get_longitud_display(cuento.longitud)
            else:
                longitud_display = 'No especificado'

            # Obtener tiempo de lectura de forma segura
            if hasattr(cuento, 'tiempo_lectura_estimado') and cuento.tiempo_lectura_estimado:
                tiempo_lectura = int(cuento.tiempo_lectura_estimado // 60)
            else:
                tiempo_lectura = 'No especificado'

            # Obtener veces leído de forma segura
            if hasattr(cuento, 'veces_leido'):
                veces_leido = cuento.veces_leido
            else:
                veces_leido = 0

            info_adicional = f"""
            <b>Estadísticas del Cuento:</b><br/>
            • Longitud: {longitud_display}<br/>
            • Tiempo estimado de lectura: {tiempo_lectura} minutos<br/>
            • Veces leído: {veces_leido}<br/>
            • Generado con Inteligencia Artificial por CuentIA<br/><br/>

            <i>"Donde la imaginación cobra vida a través de la tecnología"</i>
            """

        except Exception as e:
            logger.error(f"Error generando información adicional: {str(e)}")
            info_adicional = """
            <b>Estadísticas del Cuento:</b><br/>
            • Generado con Inteligencia Artificial por CuentIA<br/><br/>

            <i>"Donde la imaginación cobra vida a través de la tecnología"</i>
            """

        story.append(Paragraph(info_adicional, meta_style))

        # Construir PDF
        doc.build(story)
        logger.info(f"✅ PDF generado exitosamente para el cuento: {cuento.titulo}")
        logger.info(f"📊 Tamaño del PDF: {len(buffer.getvalue())} bytes")

        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"❌ Error generando PDF para cuento {cuento.id}: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise e
