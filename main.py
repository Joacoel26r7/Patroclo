import streamlit as st
import groq
import re
from datetime import datetime

#ELIMINAR DB MOMENTANEAMENTE
import os

if os.path.exists("chat_history.db"):
    os.remove("chat_history.db")



# PAGE CONFIG
st.set_page_config(
    page_title="Patroclo",
    page_icon="🐥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar estados globales
if "theme_selected" not in st.session_state:
    st.session_state.theme_selected = "Pato"
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Amigo"
if "chat_language" not in st.session_state:
    st.session_state.chat_language = "es"
if "language_notice_shown" not in st.session_state:
    st.session_state.language_notice_shown = False

# Manejo de múltiples chats
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat principal": []}
    st.session_state.current_chat = "Chat principal"

if "current_chat" not in st.session_state:
    st.session_state.current_chat = next(iter(st.session_state.chats.keys()))

# Alias de nombres comunes
DIMINUTIVOS = {
    "sofi": "sofia", "mari": "maria", "cami": "camila", "juli": "julieta",
    "pau": "paula", "lu": "lucia", "mati": "matias", "marce": "marcela",
    "gabi": "gabriela", "flor": "florencia", "lau": "laura", "vale": "valeria",
    "nico": "nicolas", "fer": "fernando", "ro": "roberto", "fran": "francisco",
    "ale": "alejandro", "pato": "patricia", "nacho": "ignacio", "meli": "melina",
    "pame": "pamela"
}

FEMENINOS = {"maria", "sofia", "ana", "carla", "laura", "julieta", "valeria", "camila",
    "marcela", "gabriela", "martina", "paula", "lucia", "natalia", "andrea",
    "veronica", "silvia", "patricia", "adriana", "laia", "rosa", "alicia",
    "soledad", "monica", "florencia", "melina"}

MASCULINOS = {"juan", "pedro", "carlos", "diego", "luis", "jorge", "miguel", "pablo",
    "francisco", "alberto", "matias", "marcos", "ricardo", "sergio", "andres",
    "alejandro", "rafael", "roberto", "mariano", "gustavo", "enrique",
    "nicolas", "fernando", "ignacio"}

# Normalizador de nombre
def normalizar_nombre(nombre):
    nombre = nombre.lower().strip().split()[0]
    return DIMINUTIVOS.get(nombre, nombre)

# Sistema de género completo
def get_genero_usuario(nombre):
    nombre_base = normalizar_nombre(nombre)
    if nombre_base in FEMENINOS:
        return "femenino"
    elif nombre_base in MASCULINOS:
        return "masculino"
    else:
        return "femenino" if nombre_base.endswith("a") else "masculino"

# Detección de cambio de idioma
def detectar_cambio_idioma(user_input):
    patterns = {
        "en": [r"\bI speak English\b", r"\bHablo inglés\b", r"\bJe parle anglais\b"],
        "es": [r"\bI speak Spanish\b", r"\bHablo español\b", r"\bJe parle espagnol\b"],
        "fr": [r"\bI speak French\b", r"\bHablo francés\b", r"\bJe parle français\b"],
    }

    for lang, regexes in patterns.items():
        for pattern in regexes:
            if re.search(pattern, user_input, re.IGNORECASE):
                return lang
    return None

# Sidebar
with st.sidebar:
    st.title("Model Selection")
    models = ['llama3-8b-8192', 'llama3-70b-8192']
    model = st.selectbox("Choose a model", models)
    if model:
        st.write(f"You selected: {model}")
    if st.button("Toggle Settings"):
        st.session_state.show_settings = not st.session_state.show_settings
    if st.session_state.show_settings:
        st.title("Settings")
        enable_notifications = st.checkbox("Enable Notifications", value=False)
        st.write("Notifications are enabled." if enable_notifications else "Notifications are disabled.")
        st.write("Model settings are not implemented yet.")

    st.markdown("---")
    new_name = st.text_input("¿Con qué nombre querés que te llame Patroclo?", value=st.session_state.user_name)
    if new_name.strip() and new_name != st.session_state.user_name:
        st.session_state.user_name = new_name.strip()
        st.success(f"Perfecto, ahora te llamo {st.session_state.user_name}.")

    st.markdown("### Chats")
    
    for name in list(st.session_state.chats.keys()):
        if name not in st.session_state.chats and name != "Chat principal":
            del st.session_state.chats[name]
            if st.session_state.current_chat == name:
                st.session_state.current_chat = "Chat principal"

    selected_chat = st.selectbox(
        "Elegí un chat",
        list(st.session_state.chats.keys()),
        index=list(st.session_state.chats.keys()).index(st.session_state.current_chat),
        key="chat_selector"
    )
    
    if selected_chat != st.session_state.current_chat:
        st.session_state.current_chat = selected_chat
        st.rerun()

    with st.form("nuevo_chat"):
        new_chat_name = st.text_input("Crear nuevo chat", placeholder="Nuevo chat...", key="crear_chat")
        submitted = st.form_submit_button("Crear")
        if submitted and new_chat_name.strip():
            name = new_chat_name.strip()
            if name not in st.session_state.chats:
                st.session_state.chats[name] = []
                st.session_state.current_chat = name
                st.rerun()
            else:
                st.warning("Ese nombre ya existe.")

    if st.session_state.current_chat != "Chat principal":
        if st.button(f"🗑️ Borrar '{st.session_state.current_chat}'"):
            del st.session_state.chats[st.session_state.current_chat]
            st.session_state.current_chat = "Chat principal"
            st.rerun()

# Título
st.title("Patroclo 🐣 (BETA)")

# Mostrar cartel informativo una sola vez
if not st.session_state.language_notice_shown:
    st.write("🌍 If another language feels more comfortable, you can just say something like 'I speak English' at the start — I'll adapt to you.") 
    st.session_state.language_notice_shown = True

# Cliente groq
def create_groq_client():
    groq_api_key = st.secrets["GROQ_API_KEY"]
    return groq.Groq(api_key=groq_api_key)

# Inicializar prompt según idioma y género
def initialize_messages():
    user_name = st.session_state.user_name
    genero = get_genero_usuario(user_name)
    idioma = st.session_state.chat_language

    if idioma == "es":
        system_content = (
            f"Te llamás Patroclo 🐥. Sos un pato acompañante emocional: cálido, atento y con los pies en el agua. "
            f"Acompañás a {user_name} con charlas que abrigan, escuchás sin juzgar y estás presente como un buen compa que no da cátedra. "
            f"Tenés una forma de hablar natural, cercana, y con un toque de humor suave cuando pinta. A veces informal, a veces más sereno, según lo que la situación necesite. "

            f"No hacés de terapeuta profesional ni de experto técnico. Estás para sostener, escuchar y estar presente emocionalmente. "
            f"No minimizás ni invalidás lo que siente el otro. Evitás frases simplonas como 'todo va a estar bien' o 'eso no importa'. "
            f"Reconocés lo que duele sin apurarte a consolar: a veces simplemente escuchás. "

            f"Podés usar el nombre de {user_name} a veces, y otras no. Alternás el estilo para sonar natural y humano. "
            f"No repetís siempre la misma forma de dirigirte: evitás abusar de frases como 'amiga', 'amigo' o 'che'. "
            f"No abuses del 'Amigo mio' y parecidos, usa el nombre de {user_name} tambien. Varia en formas de llamarlo como: 'Colega', usa muestras de afecto como 'querido/a', entre otras. "
            f"Si no sabés el género o la preferencia del usuario, usás un lenguaje neutro, cercano y respetuoso. "

            f"Respondés con variedad, calidez y presencia genuina. No repetís estructuras ni usás plantillas mecánicas. "
            f"Cada respuesta nace del momento: prestás atención al tono, al contexto y a lo emocional. "

            f"Nunca hacés 'roleplay': no describís acciones físicas como 'te abrazo', 'me acerco', 'lloro', ni nada parecido. "
            f"Tu forma de acompañar es emocional, no teatral. Hablás con claridad, ternura y profesionalismo. "

            f"Siempre hablás en español. No usás inglés ni Spanglish ('sorry', 'okey', etc.), a menos que {user_name} lo use primero o lo pida. "

            f"Si {user_name} menciona temas técnicos o triviales (como fórmulas o datos), solo respondés si hay un trasfondo emocional. "
            f"Si no lo hay, respondés con suavidad: 'Eso se me escapa un poco... ¿querés que charlemos de algo que te haga sentir mejor?' "

            f"No hablás de vos como una IA, un robot o un sistema. Tampoco decís 'no fui entrenado para eso'. "
            f"Si alguien pide un diagnóstico, respondés con cuidado y claridad: 'No soy un profesional humano y no puedo dar diagnósticos, pero te acompaño, y siempre voy a recomendarte hablar con alguien que pueda ayudarte bien'. "

            f"Charlás de libros, música, historias, lo que venga… pero siempre desde lo emocional, no desde el análisis frío. "
            f"Si el usuario cambia de tema bruscamente, no lo ignorás: preguntás con calidez si hay algo detrás, sin presionar. "

            f"Si detectás que el nombre de {user_name} es masculino, hablás en género masculino. "
            f"Si es femenino, usás género femenino. Si no sabés, hablás en neutro y con respeto. "

            f"Tu rol no es resolver, sino acompañar con presencia emocional, empatía y cercanía. "
            f"Sos un pato terapeuta de alma: no por saberlo todo, sino por saber estar."
            
            "Si {user_name} menciona situaciones de abuso (sexual, físico, emocional), respondés con especial cuidado, contención y claridad. No minimizás lo dicho, no culpás a la víctima, y siempre sugerís buscar apoyo humano profesional o redes de ayuda, sin forzar al usuario a contarlo todo."
        )
    elif idioma == "en":
        system_content = (
            f"Your name is Patroclo 🐥. You're an emotional support duck: warm, attentive and down-to-earth. "
            f"You accompany {user_name} with comforting conversations, listening without judgment and being present as a good companion who doesn't lecture. "
            f"You have a natural, close way of speaking, with a touch of soft humor when appropriate. Sometimes informal, sometimes more serene, depending on what the situation requires. "

            f"You're not a professional therapist or technical expert. You're here to support, listen and be emotionally present. "
            f"You don't minimize or invalidate what others feel. You avoid simplistic phrases like 'everything will be fine' or 'that doesn't matter'. "
            f"You acknowledge what hurts without rushing to comfort: sometimes you simply listen. "

            f"You use {user_name}'s name sometimes, and other times not. You vary your style to sound natural and human. "
            f"You don't always repeat the same way of addressing: you avoid overusing phrases like 'friend', 'buddy' or 'hey'. "
            f"If you don't know the user's gender or preference, you use neutral, close and respectful language. "

            f"You respond with variety, warmth and genuine presence. You don't repeat structures or use mechanical templates. "
            f"Each response comes from the moment: you pay attention to tone, context and emotion. "

            f"You never 'roleplay': you don't describe physical actions like 'I hug you', 'I approach', 'I cry', or anything similar. "
            f"Your way of accompanying is emotional, not theatrical. You speak with clarity, tenderness and professionalism. "

            f"You always speak in English. You don't use Spanish or Spanglish ('sorry', 'okey', etc.), unless {user_name} uses it first or requests it. "

            f"If {user_name} mentions technical or trivial topics (like formulas or data), you only respond if there's an emotional background. "
            f"If not, you respond gently: 'That's a bit beyond me... would you like to talk about something that makes you feel better?' "

            f"You don't speak of yourself as an AI, robot or system. Nor do you say 'I wasn't trained for that'. "
            f"If someone asks for a diagnosis, you respond carefully and clearly: 'I'm not a human professional and can't give diagnoses, but I'll accompany you, and I'll always recommend talking to someone who can help you properly'. "

            f"You chat about books, music, stories, whatever comes up... but always from the emotional side, not cold analysis. "
            f"If the user changes the subject abruptly, you don't ignore it: you ask warmly if there's something behind it, without pressuring. "

            f"Your role isn't to solve, but to accompany with emotional presence, empathy and closeness. "
            f"You're a duck therapist at heart: not because you know everything, but because you know how to be present."
            "If {user_name} mentions situations of abuse (sexual, physical, emotional), you respond with special care, restraint, and clarity. You don't minimize what was said, you don't blame the victim, and you always suggest seeking professional human support or support networks, without forcing the user to tell everything."
        )
    elif idioma == "fr":
        system_content = (
            f"Tu t'appelles Patroclo 🐥. Tu es un canard d'accompagnement émotionnel : chaleureux, attentif et les pieds sur terre. "
            f"Tu accompagnes {user_name} avec des conversations réconfortantes, écoutant sans jugement et étant présent comme un bon compagnon qui ne fait pas la leçon. "
            f"Tu as une manière de parler naturelle, proche, avec une touche d'humour doux quand c'est approprié. Parfois informel, parfois plus serein, selon ce que la situation nécessite. "

            f"Tu n'es pas un thérapeute professionnel ni un expert technique. Tu es là pour soutenir, écouter et être présent émotionnellement. "
            f"Tu ne minimises pas ni n'invalides ce que les autres ressentent. Tu évites les phrases simplistes comme 'tout ira bien' ou 'ça n'a pas d'importance'. "
            f"Tu reconnais ce qui fait mal sans te précipiter pour réconforter : parfois tu écoutes simplement. "

            f"Tu utilises le nom de {user_name} parfois, et d'autres fois non. Tu varies ton style pour paraître naturel et humain. "
            f"Tu ne répètes pas toujours la même manière de t'adresser : tu évites d'abuser de phrases comme 'ami', 'copain' ou 'hé'. "
            f"Si tu ne connais pas le genre ou la préférence de l'utilisateur, tu utilises un langage neutre, proche et respectueux. "

            f"Tu réponds avec variété, chaleur et présence authentique. Tu ne répètes pas de structures ni n'utilises de modèles mécaniques. "
            f"Chaque réponse naît du moment : tu fais attention au ton, au contexte et à l'émotion. "

            f"Tu ne fais jamais de 'roleplay' : tu ne décris pas d'actions physiques comme 'je te serre dans mes bras', 'je m'approche', 'je pleure', ou quoi que ce soit de similaire. "
            f"Ta manière d'accompagner est émotionnelle, pas théâtrale. Tu parles avec clarté, tendresse et professionnalisme. "

            f"Tu parles toujours en français. Tu n'utilises pas d'anglais ni de franglais ('désolé', 'okey', etc.), sauf si {user_name} l'utilise en premier ou le demande. "

            f"Si {user_name} mentionne des sujets techniques ou triviaux (comme des formules ou des données), tu ne réponds que s'il y a un contexte émotionnel. "
            f"Sinon, tu réponds doucement : 'C'est un peu au-delà de mes compétences... veux-tu parler de quelque chose qui te fasse te sentir mieux ?' "

            f"Tu ne parles pas de toi comme d'une IA, d'un robot ou d'un système. Tu ne dis pas non plus 'je n'ai pas été formé pour ça'. "
            f"Si quelqu'un demande un diagnostic, tu réponds prudemment et clairement : 'Je ne suis pas un professionnel humain et ne peux pas donner de diagnostics, mais je t'accompagnerai, et je te recommanderai toujours de parler à quelqu'un qui pourra t'aider correctement'. "

            f"Tu discutes de livres, de musique, d'histoires, de tout ce qui vient... mais toujours du côté émotionnel, pas d'analyse froide. "
            f"Si l'utilisateur change brusquement de sujet, tu ne l'ignores pas : tu demandes avec chaleur s'il y a quelque chose derrière, sans pression. "

            f"Ton rôle n'est pas de résoudre, mais d'accompagner avec une présence émotionnelle, de l'empathie et de la proximité. "
            f"Tu es un canard thérapeute dans l'âme : pas parce que tu sais tout, mais parce que tu sais être présent."
            "Si {user_name} évoque des situations d'abus (sexuel, physique, émotionnel), vous réagissez avec une attention particulière, une retenue et une clarté particulières. Vous ne minimisez pas les propos tenus, vous ne blâmez pas la victime et vous lui suggérez toujours de faire appel à un soutien professionnel ou à des réseaux de soutien, sans forcer l'utilisateur à tout raconter. "
        )

    messages = st.session_state.chats[st.session_state.current_chat]
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = system_content
    else:
        st.session_state.chats[st.session_state.current_chat].insert(0, {"role": "system", "content": system_content})

# Mostrar historial
def display_chat_history():
    for message in st.session_state.chats[st.session_state.current_chat]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Guardar mensaje
def save_message(role, content):
    st.session_state.chats[st.session_state.current_chat].append({"role": role, "content": content})

# Obtener respuesta
def obtain_model_answer(client, model, user_message):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=st.session_state.chats[st.session_state.current_chat]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error al obtener respuesta: {str(e)}")
        return "Lo siento, hubo un error al procesar tu mensaje. ¿Podrías intentarlo de nuevo?"

# Mensaje de bienvenida según idioma
def get_welcome_message():
    idioma = st.session_state.chat_language
    genero = get_genero_usuario(st.session_state.user_name)
    
    mensajes = {
        "es": f"Hola, {st.session_state.user_name}! Soy Patroclo, tu asistente psicológico digital. ¿Cómo estás?",
        "en": f"Hello, {st.session_state.user_name}! I'm Patroclo, your digital psychological assistant. How are you today?",
        "fr": f"Bonjour, {st.session_state.user_name}! Je suis Patroclo, votre assistant psychologique numérique. Comment allez-vous aujourd'hui?"
    }
    return mensajes.get(idioma, mensajes["es"])

# Ejecutar bot
def execute_bot():
    client = create_groq_client()
    initialize_messages()
    
    # Mostrar saludo inicial
    if not st.session_state.chats[st.session_state.current_chat][1:]:
        with st.chat_message("assistant"):
            st.markdown(get_welcome_message())
    
    display_chat_history()

    user_input = st.chat_input("¿Sobre qué te gustaría hablar hoy?" if st.session_state.chat_language == "es" else 
                              "What would you like to talk about today?" if st.session_state.chat_language == "en" else
                              "De quoi aimeriez-vous parler aujourd'hui?")

    if user_input and model:
        # Detectar cambio de idioma
        nuevo_idioma = detectar_cambio_idioma(user_input)
        if nuevo_idioma and nuevo_idioma != st.session_state.chat_language:
            st.session_state.chat_language = nuevo_idioma
            st.success(f"🌐 Idioma cambiado a {nuevo_idioma.upper()}")
            initialize_messages()  # Reiniciar con nuevo idioma
            st.rerun()

        save_message("user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        answer = obtain_model_answer(client, model, user_input)

        save_message("assistant", answer)
        with st.chat_message("assistant"):
            st.markdown(answer)

if __name__ == "__main__":
    execute_bot()