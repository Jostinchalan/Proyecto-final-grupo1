import logging
from django.conf import settings
from decouple import config
from typing import Dict, Optional, Tuple
import time
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        # Obtener la clave API de las variables de entorno o configuración
        self.api_key = config('OPENAI_API_KEY', default='')
        self.client = None

        if self.api_key:
            try:
                if not self.api_key.startswith('sk-'):
                    logger.warning("OPENAI_API_KEY no tiene el formato correcto (debe comenzar con 'sk-')")
                self.client = OpenAI(api_key=self.api_key)
                logger.info("Cliente OpenAI inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando cliente OpenAI: {str(e)}")
        else:
            logger.warning("OPENAI_API_KEY no configurada - usando modo fallback")

    def generar_cuento_completo(self, datos_formulario: Dict, user=None) -> Tuple[str, str, str, str, str]:
        try:
            idioma = self._obtener_idioma_usuario(user)
            logger.info(f" Generando cuento en idioma: {idioma} para usuario: {user.username if user else 'Anónimo'}")
            logger.info(f"Iniciando generacion de cuento para: {datos_formulario.get('personaje_principal', 'N/A')}")

            if not self.client:
                logger.info("Cliente OpenAI no disponible, usando fallback")
                return self._generar_cuento_fallback(datos_formulario, idioma)
            logger.info("Intentando generar texto del cuento con IA...")
            try:
                titulo, contenido, moraleja = self._generar_texto_cuento(datos_formulario, idioma)
                logger.info("Texto del cuento generado con IA exitosamente")
            except Exception as e:
                logger.warning(f"Error con IA, usando fallback para texto: {str(e)}")
                titulo, contenido, moraleja = self._generar_cuento_fallback(datos_formulario, idioma)[:3]

            logger.info("Intentando generar imagen del cuento...")
            try:
                imagen_url, imagen_prompt = self._generar_imagen_cuento(titulo, contenido, datos_formulario['tema'],
                                                                        idioma)
                logger.info("Imagen generada exitosamente")
            except Exception as e:
                logger.warning(f"Error generando imagen, usando placeholder: {str(e)}")
                imagen_url = "/static/images/cuento-placeholder.png"
                imagen_prompt = "Imagen placeholder para el cuento"

            logger.info(f" Cuento generado exitosamente en {idioma}: {titulo}")
            return titulo, contenido, moraleja, imagen_url, imagen_prompt

        except Exception as e:
            logger.error(f"Error generando cuento completo: {str(e)}")
            idioma = self._obtener_idioma_usuario(user)
            return self._generar_cuento_fallback(datos_formulario, idioma)

    def _generar_texto_cuento(self, datos: Dict, idioma: str = 'es') -> Tuple[str, str, str]:
        if not self.client:
            raise Exception("Cliente OpenAI no disponible")
        prompt = self._construir_prompt_cuento(datos, idioma)
        logger.info(f" Enviando prompt a OpenAI en idioma: {idioma}")
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": self._obtener_system_prompt(idioma)
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.8,
            presence_penalty=0.2,
            frequency_penalty=0.1
        )

        contenido_completo = response.choices[0].message.content.strip()
        logger.info(f" Respuesta recibida de OpenAI: {len(contenido_completo)} caracteres")
        titulo, contenido, moraleja = self._procesar_respuesta_cuento(contenido_completo, datos, idioma)
        return titulo, contenido, moraleja

    def _generar_imagen_cuento(self, titulo: str, contenido: str, tema: str, idioma: str = 'es') -> Tuple[str, str]:
        if not self.client:
            raise Exception("Cliente OpenAI no disponible")
        prompt_imagen = self._construir_prompt_imagen(titulo, contenido, tema, idioma)
        logger.info(" Generando imagen con DALL-E...")
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt_imagen,
            size="1024x1024",
            quality="hd",
            style="vivid",
            n=1,
        )

        imagen_url = response.data[0].url

        logger.info("Imagen generada exitosamente")
        return imagen_url, prompt_imagen

    def _construir_prompt_cuento(self, datos: Dict, idioma: str = 'es') -> str:
        logger.info(f"🔧 Construyendo prompt en idioma: {idioma}")
        edad_descripciones = {
            'es': {
                '3-5': 'niños de 3 a 5 años (preescolar) - usa vocabulario muy simple, frases cortas y conceptos básicos',
                '6-8': 'niños de 6 a 8 años (primaria temprana) - vocabulario intermedio, puede incluir aventuras simples',
                '9-12': 'niños de 9 a 12 años (primaria tardía) - vocabulario más avanzado, tramas más complejas'
            },
            'en': {
                '3-5': 'children aged 3 to 5 years (preschool) - use very simple vocabulary, short sentences and basic concepts',
                '6-8': 'children aged 6 to 8 years (early elementary) - intermediate vocabulary, can include simple adventures',
                '9-12': 'children aged 9 to 12 years (late elementary) - more advanced vocabulary, more complex plots'
            },
            'de': {
                '3-5': 'Kinder von 3 bis 5 Jahren (Vorschule) - verwende sehr einfaches Vokabular, kurze Sätze und grundlegende Konzepte',
                '6-8': 'Kinder von 6 bis 8 Jahren (frühe Grundschule) - mittleres Vokabular, kann einfache Abenteuer enthalten',
                '9-12': 'Kinder von 9 bis 12 Jahren (späte Grundschule) - fortgeschritteneres Vokabular, komplexere Handlungen'
            },
            'fr': {
                '3-5': 'enfants de 3 à 5 ans (préscolaire) - utilise un vocabulaire très simple, des phrases courtes et des concepts de base',
                '6-8': 'enfants de 6 à 8 ans (primaire précoce) - vocabulaire intermédiaire, peut inclure des aventures simples',
                '9-12': 'enfants de 9 à 12 ans (primaire tardive) - vocabulaire plus avancé, intrigues plus complexes'
            }
        }

        longitud_descripciones = {
            'es': {
                'corto': 'un cuento corto de 3-4 párrafos (2-3 minutos de lectura)',
                'medio': 'un cuento de longitud media de 6-8 párrafos (5-7 minutos de lectura)',
                'largo': 'un cuento largo de 10-12 párrafos (10-15 minutos de lectura)'
            },
            'en': {
                'corto': 'a short story of 3-4 paragraphs (2-3 minutes reading)',
                'medio': 'a medium-length story of 6-8 paragraphs (5-7 minutes reading)',
                'largo': 'a long story of 10-12 paragraphs (10-15 minutes reading)'
            },
            'de': {
                'corto': 'eine kurze Geschichte von 3-4 Absätzen (2-3 Minuten Lesezeit)',
                'medio': 'eine mittellange Geschichte von 6-8 Absätzen (5-7 Minuten Lesezeit)',
                'largo': 'eine lange Geschichte von 10-12 Absätzen (10-15 Minuten Lesezeit)'
            },
            'fr': {
                'corto': 'une histoire courte de 3-4 paragraphes (2-3 minutes de lecture)',
                'medio': 'une histoire de longueur moyenne de 6-8 paragraphes (5-7 minutes de lecture)',
                'largo': 'une longue histoire de 10-12 paragraphes (10-15 minutes de lecture)'
            }
        }

        tema_elementos = {
            'es': {
                'aventura': 'viajes emocionantes, descubrimientos, valentía, exploración',
                'fantasia': 'magia, criaturas mágicas, mundos encantados, hechizos',
                'amistad': 'compañerismo, lealtad, ayuda mutua, trabajo en equipo',
                'familia': 'amor familiar, tradiciones, apoyo, unión',
                'naturaleza': 'animales, bosques, océanos, cuidado del medio ambiente',
                'ciencia': 'inventos, experimentos, tecnología futurista, descubrimientos',
                'animales': 'mascotas, animales salvajes, comunicación con animales'
            },
            'en': {
                'aventura': 'exciting journeys, discoveries, bravery, exploration',
                'fantasia': 'magic, magical creatures, enchanted worlds, spells',
                'amistad': 'companionship, loyalty, mutual help, teamwork',
                'familia': 'family love, traditions, support, unity',
                'naturaleza': 'animals, forests, oceans, environmental care',
                'ciencia': 'inventions, experiments, futuristic technology, discoveries',
                'animales': 'pets, wild animals, animal communication'
            },
            'de': {
                'aventura': 'aufregende Reisen, Entdeckungen, Mut, Erkundung',
                'fantasia': 'Magie, magische Kreaturen, verzauberte Welten, Zaubersprüche',
                'amistad': 'Kameradschaft, Loyalität, gegenseitige Hilfe, Teamwork',
                'familia': 'Familienliebe, Traditionen, Unterstützung, Einheit',
                'naturaleza': 'Tiere, Wälder, Ozeane, Umweltschutz',
                'ciencia': 'Erfindungen, Experimente, futuristische Technologie, Entdeckungen',
                'animales': 'Haustiere, wilde Tiere, Tierkommunikation'
            },
            'fr': {
                'aventura': 'voyages passionnants, découvertes, bravoure, exploration',
                'fantasia': 'magie, créatures magiques, mondes enchantés, sorts',
                'amistad': 'camaraderie, loyauté, aide mutuelle, travail d\'équipe',
                'familia': 'amour familial, traditions, soutien, unité',
                'naturaleza': 'animaux, forêts, océans, protection de l\'environnement',
                'ciencia': 'inventions, expériences, technologie futuriste, découvertes',
                'animales': 'animaux domestiques, animaux sauvages, communication animale'
            }
        }
        edad_descripcion = edad_descripciones.get(idioma, edad_descripciones['es']).get(datos.get('edad', '6-8'),
                                                                                        edad_descripciones['es']['6-8'])
        longitud_descripcion = longitud_descripciones.get(idioma, longitud_descripciones['es']).get(
            datos.get('longitud', 'medio'), longitud_descripciones['es']['medio'])
        tema_elementos_texto = tema_elementos.get(idioma, tema_elementos['es']).get(datos.get('tema', 'aventura'),
                                                                                    tema_elementos['es']['aventura'])

        titulo_sugerido = datos.get('titulo', '').strip()
        personaje = datos.get('personaje_principal', 'un niño aventurero')

        prompts_por_idioma = {
            'es': f"""
Escribe {longitud_descripcion} para {edad_descripcion} con las siguientes características:

PERSONAJE PRINCIPAL: {personaje}
TEMA: {datos.get('tema', 'aventura')} - incluye elementos de {tema_elementos_texto}
TÍTULO SUGERIDO: {titulo_sugerido if titulo_sugerido else 'Genera un título creativo y mágico'}

INSTRUCCIONES ESPECÍFICAS:
1. El cuento debe ser completamente apropiado para la edad especificada
2. Usa un lenguaje descriptivo pero accesible para la edad
3. Incluye elementos mágicos y fantásticos que capturen la imaginación
4. La historia debe tener un inicio, desarrollo y final satisfactorio
5. Incluye diálogos naturales para hacer la historia más dinámica
6. Describe escenarios de manera vívida para que el niño pueda imaginarlos
7. El protagonista debe enfrentar un desafío y crecer como personaje
8. Incluye emociones positivas y momentos de emoción
9. Al final, incluye una moraleja clara y valiosa para la vida

FORMATO DE RESPUESTA REQUERIDO:
TÍTULO: [Título creativo y atractivo del cuento]

CUENTO:
[Contenido del cuento dividido en párrafos bien estructurados, con descripciones ricas y diálogos naturales]

MORALEJA:
[Una moraleja clara, positiva y educativa que se derive naturalmente de la historia]

IMPORTANTE: Asegúrate de que la historia sea emocionante, educativa, mágica y completamente apropiada para niños.
""",
            'en': f"""
Write {longitud_descripcion} for {edad_descripcion} with the following characteristics:

MAIN CHARACTER: {personaje}
THEME: {datos.get('tema', 'aventura')} - include elements of {tema_elementos_texto}
SUGGESTED TITLE: {titulo_sugerido if titulo_sugerido else 'Generate a creative and magical title'}

SPECIFIC INSTRUCTIONS:
1. The story must be completely appropriate for the specified age
2. Use descriptive but accessible language for the age
3. Include magical and fantastic elements that capture the imagination
4. The story should have a beginning, development and satisfying ending
5. Include natural dialogues to make the story more dynamic
6. Describe scenarios vividly so the child can imagine them
7. The protagonist must face a challenge and grow as a character
8. Include positive emotions and moments of excitement
9. At the end, include a clear and valuable life lesson

REQUIRED RESPONSE FORMAT:
TITLE: [Creative and attractive story title]

STORY:
[Story content divided into well-structured paragraphs, with rich descriptions and natural dialogues]

MORAL:
[A clear, positive and educational moral that naturally derives from the story]

IMPORTANT: Make sure the story is exciting, educational, magical and completely appropriate for children.
""",
            'de': f"""
Schreibe {longitud_descripcion} für {edad_descripcion} mit den folgenden Eigenschaften:

HAUPTCHARAKTER: {personaje}
THEMA: {datos.get('tema', 'aventura')} - schließe Elemente von {tema_elementos_texto} ein
VORGESCHLAGENER TITEL: {titulo_sugerido if titulo_sugerido else 'Generiere einen kreativen und magischen Titel'}

SPEZIFISCHE ANWEISUNGEN:
1. Die Geschichte muss für das angegebene Alter völlig angemessen sein
2. Verwende beschreibende, aber für das Alter zugängliche Sprache
3. Schließe magische und fantastische Elemente ein, die die Vorstellungskraft anregen
4. Die Geschichte sollte einen Anfang, eine Entwicklung und ein befriedigendes Ende haben
5. Schließe natürliche Dialoge ein, um die Geschichte dynamischer zu machen
6. Beschreibe Szenarien lebhaft, damit das Kind sie sich vorstellen kann
7. Der Protagonist muss sich einer Herausforderung stellen und als Charakter wachsen
8. Schließe positive Emotionen und aufregende Momente ein
9. Am Ende schließe eine klare und wertvolle Lebenslehre ein

ERFORDERLICHES ANTWORTFORMAT:
TITEL: [Kreativer und attraktiver Geschichtentitel]

GESCHICHTE:
[Geschichteninhalt aufgeteilt in gut strukturierte Absätze, mit reichen Beschreibungen und natürlichen Dialogen]

MORAL:
[Eine klare, positive und lehrreiche Moral, die natürlich aus der Geschichte hervorgeht]

WICHTIG: Stelle sicher, dass die Geschichte aufregend, lehrreich, magisch und völlig für Kinder geeignet ist.
""",
            'fr': f"""
Écris {longitud_descripcion} pour {edad_descripcion} avec les caractéristiques suivantes:

PERSONNAGE PRINCIPAL: {personaje}
THÈME: {datos.get('tema', 'aventura')} - inclus des éléments de {tema_elementos_texto}
TITRE SUGGÉRÉ: {titulo_sugerido if titulo_sugerido else 'Génère un titre créatif et magique'}

INSTRUCTIONS SPÉCIFIQUES:
1. L'histoire doit être complètement appropriée pour l'âge spécifié
2. Utilise un langage descriptif mais accessible pour l'âge
3. Inclus des éléments magiques et fantastiques qui capturent l'imagination
4. L'histoire doit avoir un début, un développement et une fin satisfaisante
5. Inclus des dialogues naturels pour rendre l'histoire plus dynamique
6. Décris les scénarios de manière vivante pour que l'enfant puisse les imaginer
7. Le protagoniste doit faire face à un défi et grandir en tant que personnage
8. Inclus des émotions positives et des moments d'excitation
9. À la fin, inclus une morale claire et précieuse pour la vie

FORMAT DE RÉPONSE REQUIS:
TITRE: [Titre créatif et attrayant de l'histoire]

HISTOIRE:
[Contenu de l'histoire divisé en paragraphes bien structurés, avec des descriptions riches et des dialogues naturels]

MORALE:
[Une morale claire, positive et éducative qui découle naturellement de l'histoire]

IMPORTANT: Assure-toi que l'histoire soit passionnante, éducative, magique et complètement appropriée pour les enfants.
"""
        }

        prompt_final = prompts_por_idioma.get(idioma, prompts_por_idioma['es'])
        logger.info(f" Prompt construido para idioma {idioma}, longitud: {len(prompt_final)} caracteres")

        return prompt_final

    def _construir_prompt_imagen(self, titulo: str, contenido: str, tema: str, idioma: str = 'es') -> str:

        tema_visual = {
            'aventura': 'adventure scene with maps, treasure, mountains, brave characters',
            'fantasia': 'magical fantasy scene with sparkles, enchanted forest, magical creatures',
            'amistad': 'heartwarming friendship scene with characters helping each other',
            'familia': 'warm family scene with love and togetherness',
            'naturaleza': 'beautiful nature scene with animals, trees, rivers, natural beauty',
            'ciencia': 'futuristic science scene with inventions, space, technology',
            'animales': 'adorable animals in their natural habitat, friendly and cute'
        }.get(tema, 'magical adventure scene')

        prompt_imagen = f"""
Create a beautiful, magical children's book illustration for the story "{titulo}".

Scene description: {tema_visual}

Art style requirements:
- Digital art, vibrant and warm colors
- Whimsical and magical atmosphere
- Child-friendly and enchanting
- Storybook illustration style
- High quality, detailed artwork
- Soft lighting with magical glow
- Suitable for children aged 3-12
- No scary or dark elements
- Include sparkles, soft shadows, and dreamy atmosphere

The image should capture the wonder and magic of childhood stories, with beautiful colors that would appeal to children and create a sense of adventure and imagination.
"""

        return prompt_imagen

    def _procesar_respuesta_cuento(self, respuesta: str, datos_formulario: Dict, idioma: str = 'es') -> Tuple[
        str, str, str]:
        titulos_default = {
            'es': datos_formulario.get('titulo', '').strip() or 'El Cuento Mágico',
            'en': datos_formulario.get('titulo', '').strip() or 'The Magical Tale',
            'de': datos_formulario.get('titulo', '').strip() or 'Das Magische Märchen',
            'fr': datos_formulario.get('titulo', '').strip() or 'Le Conte Magique'
        }

        moralejas_default = {
            'es': "La bondad y la valentía siempre son recompensadas.",
            'en': "Kindness and bravery are always rewarded.",
            'de': "Güte und Mut werden immer belohnt.",
            'fr': "La bonté et le courage sont toujours récompensés."
        }

        titulo_default = titulos_default.get(idioma, titulos_default['es'])
        contenido_default = respuesta
        moraleja_default = moralejas_default.get(idioma, moralejas_default['es'])

        try:
            patrones_titulo = {
                'es': ['TÍTULO:', 'TITULO:'],
                'en': ['TITLE:', 'TÍTULO:', 'TITULO:'],
                'de': ['TITEL:', 'TITLE:', 'TÍTULO:'],
                'fr': ['TITRE:', 'TITLE:', 'TÍTULO:']
            }

            patrones_cuento = {
                'es': ['CUENTO:', 'HISTORIA:'],
                'en': ['STORY:', 'TALE:', 'CUENTO:'],
                'de': ['GESCHICHTE:', 'MÄRCHEN:', 'STORY:'],
                'fr': ['HISTOIRE:', 'CONTE:', 'STORY:']
            }

            patrones_moraleja = {
                'es': ['MORALEJA:', 'ENSEÑANZA:', 'LECCIÓN:'],
                'en': ['MORAL:', 'LESSON:', 'MORALEJA:'],
                'de': ['MORAL:', 'LEHRE:', 'LEKTION:'],
                'fr': ['MORALE:', 'LEÇON:', 'ENSEIGNEMENT:']
            }

            lineas = respuesta.split('\n')
            titulo_extraido = titulo_default
            contenido_extraido = ""
            moraleja_extraida = moraleja_default

            seccion_actual = "contenido"

            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                for patron in patrones_titulo.get(idioma, patrones_titulo['es']):
                    if linea.upper().startswith(patron):
                        titulo_extraido = linea.replace(patron, '').strip()
                        seccion_actual = "titulo"
                        break
                for patron in patrones_cuento.get(idioma, patrones_cuento['es']):
                    if linea.upper().startswith(patron):
                        seccion_actual = "contenido"
                        break
                for patron in patrones_moraleja.get(idioma, patrones_moraleja['es']):
                    if linea.upper().startswith(patron):
                        seccion_actual = "moraleja"
                        moraleja_extraida = linea.replace(patron, '').strip()
                        break
                if seccion_actual == "contenido" and not any(linea.upper().startswith(p) for patrones in
                                                             [patrones_titulo.get(idioma, []),
                                                              patrones_cuento.get(idioma, []),
                                                              patrones_moraleja.get(idioma, [])] for p in patrones):
                    contenido_extraido += linea + "\n\n"
                elif seccion_actual == "moraleja" and not any(linea.upper().startswith(p) for patrones in
                                                              [patrones_titulo.get(idioma, []),
                                                               patrones_cuento.get(idioma, [])] for p in patrones):
                    if not any(linea.upper().startswith(p) for p in patrones_moraleja.get(idioma, [])):
                        moraleja_extraida += " " + linea

            contenido_extraido = contenido_extraido.strip()
            moraleja_extraida = moraleja_extraida.strip()
            if not contenido_extraido:
                contenido_extraido = respuesta

            logger.info(f"Cuento procesado en {idioma} - Titulo: {titulo_extraido[:50]}...")
            return titulo_extraido, contenido_extraido, moraleja_extraida

        except Exception as e:
            logger.error(f"Error procesando respuesta: {str(e)}")
            return titulo_default, contenido_default, moraleja_default

    def _generar_cuento_fallback(self, datos: Dict, idioma: str = 'es') -> Tuple[str, str, str, str, str]:
        personaje = datos.get('personaje_principal', 'un niño aventurero')
        tema = datos.get('tema', 'aventura')
        edad = datos.get('edad', '6-8')

        logger.info(f"🔄 Generando cuento fallback en idioma: {idioma}")
        titulos_por_tema = {
            'es': {
                'aventura': f"La Gran Aventura de {personaje}",
                'fantasia': f"El Mundo Mágico de {personaje}",
                'amistad': f"{personaje} y el Poder de la Amistad",
                'familia': f"La Familia Especial de {personaje}",
                'naturaleza': f"{personaje} y los Secretos del Bosque",
                'ciencia': f"Las Increíbles Invenciones de {personaje}",
                'animales': f"{personaje} y sus Amigos Animales"
            },
            'en': {
                'aventura': f"The Great Adventure of {personaje}",
                'fantasia': f"The Magical World of {personaje}",
                'amistad': f"{personaje} and the Power of Friendship",
                'familia': f"The Special Family of {personaje}",
                'naturaleza': f"{personaje} and the Forest Secrets",
                'ciencia': f"The Incredible Inventions of {personaje}",
                'animales': f"{personaje} and Animal Friends"
            },
            'de': {
                'aventura': f"Das Große Abenteuer von {personaje}",
                'fantasia': f"Die Magische Welt von {personaje}",
                'amistad': f"{personaje} und die Kraft der Freundschaft",
                'familia': f"Die Besondere Familie von {personaje}",
                'naturaleza': f"{personaje} und die Geheimnisse des Waldes",
                'ciencia': f"Die Unglaublichen Erfindungen von {personaje}",
                'animales': f"{personaje} und Tierfreunde"
            },
            'fr': {
                'aventura': f"La Grande Aventure de {personaje}",
                'fantasia': f"Le Monde Magique de {personaje}",
                'amistad': f"{personaje} et le Pouvoir de l'Amitié",
                'familia': f"La Famille Spéciale de {personaje}",
                'naturaleza': f"{personaje} et les Secrets de la Forêt",
                'ciencia': f"Les Incroyables Inventions de {personaje}",
                'animales': f"{personaje} et ses Amis Animaux"
            }
        }

        titulo = titulos_por_tema.get(idioma, titulos_por_tema['es']).get(tema, f"La Aventura Mágica de {personaje}")

        contenidos_por_tema = {
            'es': {
                'aventura': f"""
Había una vez {personaje} que vivía en un pequeño pueblo rodeado de montañas misteriosas. Un día, mientras exploraba el bosque cercano, encontró un mapa antiguo que mostraba el camino hacia un tesoro perdido.

Con valentía en el corazón, {personaje} emprendió una emocionante aventura. Cruzó ríos cristalinos, escaló colinas empinadas y resolvió acertijos antiguos. En cada paso del camino, aprendió algo nuevo sobre sí mismo.

Durante su viaje, {personaje} se encontró con otros aventureros que necesitaban ayuda. Sin dudarlo, compartió su comida y les enseñó el camino seguro. Juntos, enfrentaron los desafíos con coraje y determinación.

Al final, {personaje} descubrió que el verdadero tesoro no era oro ni joyas, sino las amistades que había hecho y las lecciones que había aprendido. Regresó a casa siendo más sabio y valiente que nunca.
""",
                'fantasia': f"""
En un reino mágico muy lejano, vivía {personaje} en una casa encantada donde los libros hablaban y las flores cantaban. Un día, una estrella fugaz cayó en su jardín, trayendo consigo una misión especial.

{personaje} descubrió que tenía poderes mágicos únicos que podía usar para ayudar a otros. Con su varita brillante y su corazón puro, emprendió un viaje por tierras encantadas llenas de criaturas fantásticas.

En su camino, {personaje} conoció a un dragón amigable que había perdido su fuego, a un unicornio triste que no podía volar, y a un hada que había olvidado cómo hacer magia. Con paciencia y bondad, ayudó a cada uno a recuperar sus dones especiales.

Al final de su aventura mágica, {personaje} aprendió que la verdadera magia viene del amor y la generosidad. El reino entero celebró su valentía, y desde entonces, la magia floreció más fuerte que nunca.
""",
                'amistad': f"""
{personaje} era nuevo en la escuela y se sentía muy solo. Durante el recreo, se sentaba bajo un gran árbol y observaba a los otros niños jugar, deseando tener amigos con quienes compartir.

Un día, {personaje} vio a otro niño que también estaba solo, leyendo un libro en un rincón. Con valentía, se acercó y le preguntó sobre su historia. Así comenzó una hermosa amistad que cambiaría sus vidas.

Juntos, {personaje} y su nuevo amigo descubrieron que tenían muchas cosas en común. Les gustaban los mismos juegos, las mismas historias, y ambos soñaban con grandes aventuras. Pronto, otros niños se unieron a su grupo.

{personaje} aprendió que hacer amigos requiere ser amable, compartir y estar dispuesto a escuchar. Su círculo de amigos creció, y la escuela se convirtió en un lugar lleno de risas, juegos y momentos especiales que atesoraría para siempre.
"""
            },
            'en': {
                'aventura': f"""
Once upon a time, {personaje} lived in a small village surrounded by mysterious mountains. One day, while exploring the nearby forest, they found an ancient map showing the path to a lost treasure.

With courage in their heart, {personaje} embarked on an exciting adventure. They crossed crystal-clear rivers, climbed steep hills, and solved ancient riddles. With each step of the journey, they learned something new about themselves.

During their journey, {personaje} met other adventurers who needed help. Without hesitation, they shared their food and showed them the safe path. Together, they faced challenges with courage and determination.

In the end, {personaje} discovered that the real treasure wasn't gold or jewels, but the friendships they had made and the lessons they had learned. They returned home wiser and braver than ever.
""",
                'fantasia': f"""
In a magical kingdom far away, {personaje} lived in an enchanted house where books talked and flowers sang. One day, a shooting star fell in their garden, bringing with it a special mission.

{personaje} discovered they had unique magical powers that could be used to help others. With their shining wand and pure heart, they embarked on a journey through enchanted lands full of fantastic creatures.

On their path, {personaje} met a friendly dragon who had lost his fire, a sad unicorn who couldn't fly, and a fairy who had forgotten how to do magic. With patience and kindness, they helped each one recover their special gifts.

At the end of their magical adventure, {personaje} learned that true magic comes from love and generosity. The entire kingdom celebrated their bravery, and from then on, magic flourished stronger than ever.
""",
                'amistad': f"""
{personaje} was new at school and felt very lonely. During recess, they would sit under a big tree and watch the other children play, wishing they had friends to share with.

One day, {personaje} saw another child who was also alone, reading a book in a corner. With courage, they approached and asked about the story. Thus began a beautiful friendship that would change their lives.

Together, {personaje} and their new friend discovered they had many things in common. They liked the same games, the same stories, and both dreamed of great adventures. Soon, other children joined their group.

{personaje} learned that making friends requires being kind, sharing, and being willing to listen. Their circle of friends grew, and school became a place full of laughter, games, and special moments they would treasure forever.
"""
            },
            'de': {
                'aventura': f"""
Es war einmal {personaje}, der in einem kleinen Dorf lebte, das von geheimnisvollen Bergen umgeben war. Eines Tages, während er den nahen Wald erkundete, fand er eine alte Karte, die den Weg zu einem verlorenen Schatz zeigte.

Mit Mut im Herzen begab sich {personaje} auf ein aufregendes Abenteuer. Er überquerte kristallklare Flüsse, kletterte steile Hügel hinauf und löste alte Rätsel. Mit jedem Schritt der Reise lernte er etwas Neues über sich selbst.

Während seiner Reise traf {personaje} andere Abenteurer, die Hilfe brauchten. Ohne zu zögern teilte er sein Essen und zeigte ihnen den sicheren Weg. Gemeinsam stellten sie sich den Herausforderungen mit Mut und Entschlossenheit.

Am Ende entdeckte {personaje}, dass der wahre Schatz nicht Gold oder Juwelen waren, sondern die Freundschaften, die er geschlossen hatte, und die Lektionen, die er gelernt hatte. Er kehrte weiser und mutiger als je zuvor nach Hause zurück.
""",
                'fantasia': f"""
In einem magischen Königreich weit weg lebte {personaje} in einem verzauberten Haus, wo Bücher sprachen und Blumen sangen. Eines Tages fiel eine Sternschnuppe in seinen Garten und brachte eine besondere Mission mit sich.

{personaje} entdeckte, dass er einzigartige magische Kräfte hatte, die er nutzen konnte, um anderen zu helfen. Mit seinem leuchtenden Zauberstab und reinem Herzen begab er sich auf eine Reise durch verzauberte Länder voller fantastischer Kreaturen.

Auf seinem Weg traf {personaje} einen freundlichen Drachen, der sein Feuer verloren hatte, ein trauriges Einhorn, das nicht fliegen konnte, und eine Fee, die vergessen hatte, wie man Magie macht. Mit Geduld und Güte half er jedem, seine besonderen Gaben wiederzuerlangen.

Am Ende seines magischen Abenteuers lernte {personaje}, dass wahre Magie aus Liebe und Großzügigkeit kommt. Das ganze Königreich feierte seinen Mut, und von da an blühte die Magie stärker als je zuvor.
""",
                'amistad': f"""
{personaje} war neu in der Schule und fühlte sich sehr einsam. In den Pausen saß er unter einem großen Baum und beobachtete die anderen Kinder beim Spielen, wünschte sich Freunde zum Teilen.

Eines Tages sah {personaje} ein anderes Kind, das auch allein war und in einer Ecke ein Buch las. Mit Mut näherte er sich und fragte nach der Geschichte. So begann eine schöne Freundschaft, die ihr Leben verändern würde.

Zusammen entdeckten {personaje} und sein neuer Freund, dass sie viele Gemeinsamkeiten hatten. Sie mochten die gleichen Spiele, die gleichen Geschichten und träumten beide von großen Abenteuern. Bald schlossen sich andere Kinder ihrer Gruppe an.

{personaje} lernte, dass Freunde finden bedeutet, freundlich zu sein, zu teilen und bereit zu sein zuzuhören. Sein Freundeskreis wuchs, und die Schule wurde zu einem Ort voller Lachen, Spiele und besonderer Momente, die er für immer schätzen würde.
"""
            },
            'fr': {
                'aventura': f"""
Il était une fois {personaje} qui vivait dans un petit village entouré de montagnes mystérieuses. Un jour, en explorant la forêt voisine, il trouva une carte ancienne montrant le chemin vers un trésor perdu.

Avec du courage dans le cœur, {personaje} entreprit une aventure passionnante. Il traversa des rivières cristallines, escalada des collines escarpées et résolut d'anciennes énigmes. À chaque étape du voyage, il apprit quelque chose de nouveau sur lui-même.

Pendant son voyage, {personaje} rencontra d'autres aventuriers qui avaient besoin d'aide. Sans hésiter, il partagea sa nourriture et leur montra le chemin sûr. Ensemble, ils affrontèrent les défis avec courage et détermination.

À la fin, {personaje} découvrit que le vrai trésor n'était pas l'or ou les bijoux, mais les amitiés qu'il avait nouées et les leçons qu'il avait apprises. Il rentra chez lui plus sage et plus courageux que jamais.
""",
                'fantasia': f"""
Dans un royaume magique très lointain, {personaje} vivait dans une maison enchantée où les livres parlaient et les fleurs chantaient. Un jour, une étoile filante tomba dans son jardin, apportant avec elle une mission spéciale.

{personaje} découvrit qu'il avait des pouvoirs magiques uniques qu'il pouvait utiliser pour aider les autres. Avec sa baguette brillante et son cœur pur, il entreprit un voyage à travers des terres enchantées pleines de créatures fantastiques.

Sur son chemin, {personaje} rencontra un dragon amical qui avait perdu son feu, une licorne triste qui ne pouvait pas voler, et une fée qui avait oublié comment faire de la magie. Avec patience et bonté, il aida chacun à récupérer ses dons spéciaux.

À la fin de son aventure magique, {personaje} apprit que la vraie magie vient de l'amour et de la générosité. Tout le royaume célébra son courage, et depuis lors, la magie fleurit plus forte que jamais.
""",
                'amistad': f"""
{personaje} était nouveau à l'école et se sentait très seul. Pendant la récréation, il s'asseyait sous un grand arbre et regardait les autres enfants jouer, souhaitant avoir des amis avec qui partager.

Un jour, {personaje} vit un autre enfant qui était aussi seul, lisant un livre dans un coin. Avec courage, il s'approcha et demanda à propos de l'histoire. Ainsi commença une belle amitié qui changerait leurs vies.

Ensemble, {personaje} et son nouvel ami découvrirent qu'ils avaient beaucoup de choses en commun. Ils aimaient les mêmes jeux, les mêmes histoires, et tous deux rêvaient de grandes aventures. Bientôt, d'autres enfants rejoignirent leur groupe.

{personaje} apprit que se faire des amis nécessite d'être gentil, de partager et d'être prêt à écouter. Son cercle d'amis grandit, et l'école devint un lieu plein de rires, de jeux et de moments spéciaux qu'il chérirait pour toujours.
"""
            }
        }

        contenido = contenidos_por_tema.get(idioma, contenidos_por_tema['es']).get(tema, contenidos_por_tema.get(idioma,
                                                                                                                 contenidos_por_tema[
                                                                                                                     'es'])[
            'aventura'])
        moralejas_por_tema = {
            'es': {
                'aventura': "Las aventuras más grandes comienzan cuando tenemos el valor de dar el primer paso y ayudar a otros en el camino.",
                'fantasia': "La verdadera magia está en usar nuestros dones para hacer el bien y ayudar a quienes nos rodean.",
                'amistad': "La amistad verdadera se construye con bondad, comprensión y la disposición de compartir nuestro corazón.",
                'familia': "El amor familiar es el tesoro más grande que podemos tener en la vida.",
                'naturaleza': "Cuidar la naturaleza es cuidar nuestro hogar y el futuro de todos los seres vivos.",
                'ciencia': "La curiosidad y el deseo de aprender nos llevan a descubrir cosas maravillosas.",
                'animales': "Todos los seres vivos merecen amor, respeto y cuidado."
            },
            'en': {
                'aventura': "The greatest adventures begin when we have the courage to take the first step and help others along the way.",
                'fantasia': "True magic lies in using our gifts to do good and help those around us.",
                'amistad': "True friendship is built with kindness, understanding, and the willingness to share our hearts.",
                'familia': "Family love is the greatest treasure we can have in life.",
                'naturaleza': "Taking care of nature is taking care of our home and the future of all living beings.",
                'ciencia': "Curiosity and the desire to learn lead us to discover wonderful things.",
                'animales': "All living beings deserve love, respect, and care."
            },
            'de': {
                'aventura': "Die größten Abenteuer beginnen, wenn wir den Mut haben, den ersten Schritt zu machen und anderen auf dem Weg zu helfen.",
                'fantasia': "Wahre Magie liegt darin, unsere Gaben zu nutzen, um Gutes zu tun und denen um uns herum zu helfen.",
                'amistad': "Wahre Freundschaft wird mit Güte, Verständnis und der Bereitschaft aufgebaut, unser Herz zu teilen.",
                'familia': "Familienliebe ist der größte Schatz, den wir im Leben haben können.",
                'naturaleza': "Die Natur zu pflegen bedeutet, unser Zuhause und die Zukunft aller Lebewesen zu pflegen.",
                'ciencia': "Neugier und der Wunsch zu lernen führen uns dazu, wunderbare Dinge zu entdecken.",
                'animales': "Alle Lebewesen verdienen Liebe, Respekt und Fürsorge."
            },
            'fr': {
                'aventura': "Les plus grandes aventures commencent quand nous avons le courage de faire le premier pas et d'aider les autres en chemin.",
                'fantasia': "La vraie magie réside dans l'utilisation de nos dons pour faire le bien et aider ceux qui nous entourent.",
                'amistad': "La vraie amitié se construit avec la bonté, la compréhension et la volonté de partager notre cœur.",
                'familia': "L'amour familial est le plus grand trésor que nous puissions avoir dans la vie.",
                'naturaleza': "Prendre soin de la nature, c'est prendre soin de notre maison et de l'avenir de tous les êtres vivants.",
                'ciencia': "La curiosité et le désir d'apprendre nous mènent à découvrir des choses merveilleuses.",
                'animales': "Tous les êtres vivants méritent amour, respect et soins."
            }
        }

        moraleja = moralejas_por_tema.get(idioma, moralejas_por_tema['es']).get(tema, moralejas_por_tema.get(idioma,
                                                                                                             moralejas_por_tema[
                                                                                                                 'es'])[
            'aventura'])
        imagen_url = "/static/images/cuento-placeholder.png"
        imagen_prompt = f"Imagen placeholder para cuento de {tema}"

        logger.info(f"Cuento fallback generado en {idioma}: {titulo}")
        return titulo, contenido, moraleja, imagen_url, imagen_prompt

    def _obtener_idioma_usuario(self, user) -> str:
        try:
            if user and user.is_authenticated:
                from user.models import UserSettings

                logger.info(f"Buscando configuraciones para usuario: {user.username}")
                try:
                    settings_obj = UserSettings.objects.get(user=user)
                    idioma = settings_obj.language
                    logger.info(f"Idioma obtenido de UserSettings: '{idioma}' para usuario {user.username}")
                    idiomas_soportados = ['es', 'en', 'de', 'fr']
                    if idioma in idiomas_soportados:
                        return idioma
                    else:
                        logger.warning(f"Idioma '{idioma}' no soportado, usando español por defecto")
                        return 'es'

                except UserSettings.DoesNotExist:
                    logger.warning(
                        f"UserSettings no existe para usuario {user.username}, creando con idioma por defecto")
                    settings_obj = UserSettings.objects.create(user=user, language='es')
                    return 'es'
                except Exception as e:
                    logger.error(f"Error obteniendo UserSettings para {user.username}: {str(e)}")
                    return 'es'
            else:
                logger.info("Usuario no autenticado o None, usando idioma por defecto: es")
                return 'es'
        except Exception as e:
            logger.error(f"Error general obteniendo idioma del usuario: {str(e)}")
            return 'es'  # Idioma por defecto

    def _obtener_system_prompt(self, idioma: str) -> str:
        system_prompts = {
            'es': """Eres un escritor experto en cuentos infantiles mágicos. 
                    Creas historias cautivadoras, educativas y apropiadas para la edad especificada. 
                    Siempre incluyes una moraleja clara y valiosa al final.
                    Tu estilo es descriptivo, imaginativo y lleno de magia.""",
            'en': """You are an expert writer of magical children's stories. 
                    You create captivating, educational stories appropriate for the specified age. 
                    You always include a clear and valuable moral at the end.
                    Your style is descriptive, imaginative and full of magic.""",
            'de': """Du bist ein Experte für magische Kindergeschichten. 
                    Du erschaffst fesselnde, lehrreiche Geschichten, die für das angegebene Alter geeignet sind. 
                    Du schließt immer eine klare und wertvolle Moral am Ende ein.
                    Dein Stil ist beschreibend, fantasievoll und voller Magie.""",
            'fr': """Tu es un expert en contes magiques pour enfants. 
                    Tu crées des histoires captivantes, éducatives et appropriées pour l'âge spécifié. 
                    Tu inclus toujours une morale claire et précieuse à la fin.
                    Ton style est descriptif, imaginatif et plein de magie."""
        }
        return system_prompts.get(idioma, system_prompts['es'])

    def get_language_name(self, language_code: str) -> str:
        languages = {
            'es': 'Español',
            'en': 'English',
            'de': 'Deutsch',
            'fr': 'Français'
        }
        return languages.get(language_code, 'Español')

openai_service = OpenAIService()
