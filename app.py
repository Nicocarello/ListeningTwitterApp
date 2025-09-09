# scrapper_analysis_app.py

import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import google.generativeai as genai
from datetime import date, timedelta, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.express as px
import re
import json
import random
import seaborn as sns
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
from PIL import Image
import tempfile
import os
import requests




# --- Configuración inicial de la página ---
st.set_page_config(
    page_title="Twitter Scraper + Sentimiento",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Dominio de correo electrónico de la empresa (¡IMPORTANTE: CAMBIA ESTO!) ---
# Reemplaza 'tuempresa.com' con el dominio real de tu empresa.
# Por ejemplo, si los correos son 'usuario@miempresa.com', entonces el dominio es 'miempresa.com'.
COMPANY_EMAIL_DOMAIN = "publicalatam.com" # <--- ¡CAMBIA ESTO!

# --- Inicializar el estado de la sesión ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- CSS personalizado ---
st.markdown(
    """
    <style>
    .big-title {
        font-size: 3em;
        font-weight: bold;
        color: #1DA1F2; /* Twitter Blue */
        text-align: center;
        margin-bottom: 0.5em;
    }
    .subtitle {
        font-size: 1.2em;
        color: #555555;
        text-align: center;
        margin-bottom: 2em;
    }
    .stButton>button {
        background-color: #1DA1F2;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 1.1em;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0E71C3;
    }
    .stTextArea, .stDateInput {
        border-radius: 8px;
    }
    .stInfo, .stSuccess, .stWarning, .stError {
        border-left: 6px solid;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 1em;
    }
    .stInfo { border-color: #2196F3; background-color: #e3f2fd; }
    .stSuccess { border-color: #4CAF50; background-color: #e8f5e9; }
    .stWarning { border-color: #FFC107; background-color: #fff8e1; }
    .stError { border-color: #F44336; background-color: #ffebee; }

    /* Estilos para la página de login */
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh; /* Ajusta la altura para centrar verticalmente */
        padding: 20px;
    }
    .login-box {
        background-color: #f0f2f5;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        width: 100%;
        max-width: 400px;
        text-align: center;
    }
    .login-box h2 {
        color: #1DA1F2;
        margin-bottom: 30px;
        font-size: 2em;
    }
    .login-box .stTextInput > div > div > input {
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #ccc;
    }
    .login-box .stButton > button {
        width: 100%;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Función de Login ---
def login_page():
    st.title("Iniciar Sesión")
    
    # Mostrar la imagen desde la URL
    st.image("https://publicalab.com/assets/imgs/logo-publica-blanco.svg", width=300)  # Ajusta el tamaño según sea necesario
    email = st.text_input("Correo Electrónico")
    if st.button("Ingresar"):
        if email.endswith(COMPANY_EMAIL_DOMAIN):
            st.session_state.logged_in = True
            st.session_state.email = email
            st.success("¡Inicio de sesión exitoso!")
            st.rerun()  # Recargar la página para mostrar la app principal
        else:
            st.error("Por favor, ingresa un correo electrónico válido.")

# --- Función de Logout ---
def logout():
    st.session_state["logged_in"] = False
    st.info("Has cerrado sesión.")
    st.rerun() # Recargar la página para volver a la pantalla de login


# --- Contenido principal de la aplicación ---
def main_app():
    st.image("https://publicalab.com/assets/imgs/logo-publica-blanco.svg", width=200)  # Logo de Publica
    st.markdown("<h1 class='big-title'>🐦 Scraping + Análisis de Sentimiento de Tweets</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Extrae tweets, clasifica su sentimiento y descubre los temas clave.</p>", unsafe_allow_html=True)

    # --- API Keys (se recomienda ocultarlas en producción con secrets) ---
    # En un entorno real, usarías st.secrets["apify_token"] y st.secrets["gemini_api_key"]
    # Asegúrate de haber configurado tu archivo .streamlit/secrets.toml
    apify_token = st.secrets.get("apify_token")
    gemini_api_key = st.secrets.get("gemini_api_key")

    # --- Inicializar Gemini ---
    model = None
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
    else:
        st.error("Por favor, configura tu GEMINI_API_KEY en `.streamlit/secrets.toml` para habilitar el análisis de sentimiento.")

    # --- Función para scraping ---
    @st.cache_data(ttl=3600) # Cachea los datos por 1 hora
    def get_twitter_data(search_terms, start_date, end_date, sort_type):
        try:
            apify_client = ApifyClient(apify_token)
            actor_id = "apidojo/twitter-scraper-lite"
            run_input = {
                "end": end_date,
                "maxItems": 100, # Mantener un límite razonable para evitar usos excesivos de la API
                "searchTerms": search_terms,
                "sort": sort_type,
                "start": start_date
            }
            run = apify_client.actor(actor_id).call(run_input=run_input)
            dataset_items = apify_client.run(run['id']).dataset().list_items().items
            if dataset_items:
                df = pd.DataFrame(dataset_items)
                df['author/profilePicture'] = df['author'].apply(lambda x: x.get('profilePicture') if isinstance(x, dict) else None)
                df['author/followers'] = df['author'].apply(lambda x: x.get('followers') if isinstance(x, dict) else None)
                df['author/userName'] = df['author'].apply(lambda x: x.get('userName') if isinstance(x, dict) else None)

                # Asegurarse de que 'viewCount' y 'author/followers' sean numéricos
                df['viewCount'] = pd.to_numeric(df['viewCount'], errors='coerce').fillna(0)
                df['author/followers'] = pd.to_numeric(df['author/followers'], errors='coerce').fillna(0)

                # Seleccionar todas las columnas originales y las nuevas, incluyendo la foto de perfil
                all_columns = ['author/profilePicture','text', 'createdAt', 'author/userName', 'author/followers', 'url', 'likeCount',
                               'replyCount', 'retweetCount', 'quoteCount', 'bookmarkCount', 'viewCount', 'source']

                # Filtrar solo las columnas que realmente existen en el DataFrame
                df = df[[col for col in all_columns if col in df.columns]]

                df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error al obtener datos de Twitter: {e}. Asegúrate de que tu token de Apify sea válido y los términos de búsqueda sean apropiados.")
            return pd.DataFrame()

    # # --- Funciones IA ---

    def clasificar_tweets_en_lote(tweets, contexto, model):
        import json
        import re

        if not model:
            return ["NEUTRO"] * len(tweets)

        tweets_preparados = [
            tweet.replace('"', "'").replace("\n", " ").strip()[:280]
            for tweet in tweets
        ]

        prompt = f"""
    Eres un modelo de lenguaje experto en análisis de sentimiento de redes sociales.

    CONTEXTO GENERAL: {contexto}

    Clasifica el sentimiento de los siguientes tweets. Para cada tweet responde en una línea con el formato:
    Tweet 1: POSITIVO
    Tweet 2: NEGATIVO
    Tweet 3: NEUTRO

    Sentimientos permitidos: POSITIVO, NEGATIVO, NEUTRO.

    TWEETS:
    """

        for i, tweet in enumerate(tweets_preparados):
            prompt += f'\nTweet {i+1}: "{tweet}"'

        prompt += "\n\nClasificación:\n"

        try:
            response = model.generate_content(prompt, generation_config={"temperature": 0.2})
            respuesta = response.text.strip()

            # Extraer los valores usando regex
            matches = re.findall(r"Tweet\s*\d+:\s*(POSITIVO|NEGATIVO|NEUTRO)", respuesta, re.IGNORECASE)
            sentimientos = [s.upper() for s in matches]

            # Si no coincide la cantidad, asumir NEUTRO
            if len(sentimientos) != len(tweets):
                st.warning(f"❗ Gemini devolvió {len(sentimientos)} sentimientos para {len(tweets)} tweets. Se completará con NEUTRO.")
                while len(sentimientos) < len(tweets):
                    sentimientos.append("NEUTRO")
                if len(sentimientos) > len(tweets):
                    sentimientos = sentimientos[:len(tweets)]

            return sentimientos

        except Exception as e:
            st.error(f"❌ Error en la clasificación con Gemini: {e}")
            return ["NEUTRO"] * len(tweets)

    
    # --- Función actualizada para mostrar los temas ---
    def mostrar_temas_con_contraste(texto_temas):
        """
        Procesa el texto de temas de la IA y lo muestra con el nuevo formato de contraste.
        """
        # Expresión regular para capturar Título, Explicación y Ejemplo
        pattern = r"(\d+)\.\s*([^\n]+)\n(.*?)\nEjemplo:\s*\"([^\"]+)\",\s*\[author/userName:\s*([^\]]+)\]"
        
        if not texto_temas:
            st.info("No se encontraron temas para mostrar.")
            return

        matches = re.findall(pattern, texto_temas, re.MULTILINE | re.DOTALL)

        if not matches:
            # st.warning("No se pudo extraer el formato de temas esperado. Mostrando texto sin formato.")
            st.markdown(texto_temas)
            return

        for numero, tema, explicacion, ejemplo, usuario in matches:
            # Título del tema en bold y tamaño grande
            st.markdown(
                f"**<span style='font-size: 1.5em;'>{numero}. {tema.strip()}</span>**",
                unsafe_allow_html=True
            )
            
            # Descripción con un tamaño de fuente un poco menor
            st.markdown(
                f"<p style='font-size: 1.1em;'>{explicacion.strip()}</p>",
                unsafe_allow_html=True
            )
            
            # Ejemplo entre comillas y en cursiva
            st.markdown(
                f"**Ejemplo:** *\"{ejemplo.strip()}\"* - **@{usuario.strip()}**"
            )
            
            # Un separador visual para cada tema
            st.markdown("---")

    def extraer_temas_con_ia(tweets, sentimiento, contexto, num_temas=3):
        if not model:
            return "El modelo de IA no está disponible para extraer temas."
        
        # Actualización del prompt para que coincida con el formato de la función de visualización
        prompt = f"""CONTEXTO: {contexto}
        Aquí hay tweets clasificados como {sentimiento}. Extrae los {num_temas} temas principales, explicando brevemente cada uno y dando un ejemplo.
        El formato de salida debe ser exactamente:
        1. [Nombre del tema]
        [Breve explicación del tema]
        Ejemplo: "[tweet de ejemplo relevante]", [author/userName: usuario_ejemplo]
        2. [Nombre del tema]
        ...
        ---
        Tweets para analizar:\n"""

        # Limitar la cantidad de tweets enviados a la IA para evitar sobrecargar el prompt
        texto = "\n".join(tweets[:500]) # Se reduce de 1000 a 500 para mayor eficiencia
        if not texto.strip():
            return "No hay tweets suficientes para extraer temas."

        try:
            response = model.generate_content(prompt + texto, generation_config={"temperature": 0.4})
            return response.text.strip()
        except Exception as e:
            st.error(f"Error al extraer temas con IA: {e}")
            return "No se pudieron extraer temas."

    # --- FUNCIÓN PARA TEMAS GENERALES (también con el prompt actualizado) ---
    def extraer_temas_generales_con_ia(tweets, contexto, num_temas=5):
        if not model:
            return "El modelo de IA no está disponible para extraer temas generales."

        # Actualización del prompt para que coincida con el formato de la función de visualización
        prompt = f"""CONTEXTO: {contexto}
        Analiza la siguiente colección de tweets y extrae los {num_temas} temas principales o más mencionados.
        Para cada tema, proporciona un nombre, una breve explicación y un tweet de ejemplo relevante.
        El formato de salida debe ser exactamente:
        1. [Nombre del tema]
        [Breve explicación del tema]
        Ejemplo: "[tweet de ejemplo relevante]", [author/userName: usuario_ejemplo]
        2. [Nombre del tema]
        ...
        ---
        Tweets para analizar:\n"""

        # Tomar una muestra de tweets para no exceder el límite de tokens
        sample_tweets = tweets[:min(len(tweets), 500)]
        texto = "\n".join(sample_tweets)

        if not texto.strip():
            return "No hay tweets suficientes para extraer temas generales."

        try:
            response = model.generate_content(prompt + texto, generation_config={"temperature": 0.4})
            return response.text.strip()
        except Exception as e:
            st.error(f"Error al extraer temas generales con IA: {e}")
            return "No se pudieron extraer temas generales."

    # --- Sidebar: Parámetros ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        search_terms_input = st.text_area(
            "Términos de búsqueda",
            # Usamos el argumento 'placeholder' para el texto de sugerencia
            placeholder="Mercado Libre\nfintech Argentina",
            help="Introduce los términos que deseas buscar en Twitter. Cada término debe ir en una nueva línea o separado por comas."
        )

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Fecha de inicio", date.today() - timedelta(days=7), max_value=date.today())
        with col2:
            end_date = st.date_input("Fecha de fin", date.today(), max_value=date.today())

        if start_date > end_date:
            st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
            st.stop()

        contexto = st.text_area(
            "Contexto para el análisis de sentimiento (opcional)",
            "Opiniones sobre empresas de tecnología y finanzas en América Latina.",
            help="Proporciona un contexto a la IA para mejorar la precisión del análisis de sentimiento y la extracción de temas. Por ejemplo: 'Opiniones de clientes sobre un nuevo producto financiero'."
        )

        st.markdown("---")
        st.info("💡 Consejo: Cuanto más específico sea el contexto, mejor será el análisis de la IA.")

        # Botón de Logout en el sidebar
        st.markdown("---")
        if st.button("Cerrar Sesión", key="logout_sidebar"):
            logout()


    def eliminar_emojis(texto):
        """Quita caracteres que no se pueden codificar en latin-1 (ej. emojis)"""
        if not isinstance(texto, str):
            return texto
        return texto.encode('latin-1', 'ignore').decode('latin-1')



    # --- Contenido principal ---
    st.markdown("---") # Separador visual

    if st.button("🚀 Ejecutar Scraping y Análisis", use_container_width=True):
        if not apify_token:
            st.error("Por favor, ingresa tu token de Apify en `.streamlit/secrets.toml` para continuar.")
        else:
            # Check if the user has provided a Gemini API key
            if not gemini_api_key:
                st.error("Por favor, ingresa tu API Key de Gemini en `.streamlit/secrets.toml` para el análisis de sentimiento y temas.")
                st.stop()

            # Procesamiento de términos
            # split by comma or new line
            terms = [s.strip() for s in re.split(r'[,\n]', search_terms_input) if s.strip()]
            if not terms:
                st.warning("Por favor, introduce al menos un término de búsqueda.")
                st.stop()

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            with st.spinner("Buscando tweets... esto puede tardar un momento."):
                df_top = get_twitter_data(terms, start_str, end_str, "Top")
                # df_latest = get_twitter_data(terms, start_str, end_str, "Latest")

            # df = pd.concat([df_top, df_latest]).drop_duplicates(subset=["url"]).reset_index(drop=True)
            df = df_top.drop_duplicates(subset=["url"]).reset_index(drop=True)

            if df.empty:
                st.warning("😔 No se encontraron tweets con los términos y fechas seleccionados. Intenta con otros parámetros.")
                st.stop()

            st.success(f"✅ Se recolectaron {len(df)} tweets únicos.")
            st.subheader("Primeros tweets encontrados:")
            st.dataframe(df.head(10))

            # --- Métricas de Alcance e Interacciones (con estilo grande) ---
            total_views = df['viewCount'].sum()
            total_interacciones = (
                df[['likeCount', 'replyCount', 'retweetCount', 'quoteCount', 'bookmarkCount']]
                .fillna(0).sum().sum()
            )

            st.markdown(f"""
            <div style="text-align: center; padding: 20px 0;">
                <div style="font-size: 2.2em; font-weight: bold; color: #000000;">
                    📈 Alcance Total: {int(total_views):,} visualizaciones
                </div>
                <div style="font-size: 2.2em; font-weight: bold; color: #000000;">
                    💬 Interacciones Totales: {int(total_interacciones):,}
                </div>
            </div>
            """, unsafe_allow_html=True)

            avg_views = total_views / len(df)
            avg_interacciones = total_interacciones / len(df)

            st.markdown(f"""
            <div style="text-align: center; font-size: 1.5em; color: #000000; margin-top: -10px;">
                Promedio por Tweet: {int(avg_views):,} vistas / {int(avg_interacciones):,} interacciones
            </div>
            """, unsafe_allow_html=True)



            # --- Clasificación de Sentimientos (en lotes) ---
            st.subheader("🧠 Clasificando Sentimientos...")

            # Definir el tamaño del lote
            batch_size = 50  # Puedes ajustar este valor. 
                            # Un lote más grande puede ser más rápido, 
                            # pero también aumenta el riesgo de errores si el prompt es muy largo.
                            
            tweets_to_classify = df['text'].astype(str).tolist()
            total_tweets = len(tweets_to_classify)

            sentimientos = []
            progress_bar = st.progress(0)

            # Iterar sobre los tweets en lotes
            for i in range(0, total_tweets, batch_size):
                batch = tweets_to_classify[i:i + batch_size]
                
                # Llamar a la nueva función de clasificación en lote
                sentimientos_batch = clasificar_tweets_en_lote(batch, contexto, model)
                sentimientos.extend(sentimientos_batch)
                
                # Actualizar la barra de progreso
                progress_bar.progress(min((i + len(batch)) / total_tweets, 1.0))

            df["sentimiento"] = sentimientos
            st.success("✅ Clasificación de sentimientos completada.")
            progress_bar.empty()

            # --- TEMAS CLAVE GENERALES (NUEVA SECCIÓN AQUÍ) ---
            st.markdown("---")
            st.subheader("💡 Temas Clave del Conjunto Total de Tweets")

            all_tweets_text = df['text'].astype(str).tolist()
            if all_tweets_text:
                with st.spinner("Extrayendo temas clave generales..."):
                    temas_generales = extraer_temas_generales_con_ia(all_tweets_text, contexto)
                mostrar_temas_con_contraste(temas_generales)
            else:
                st.warning("No hay tweets para extraer temas clave generales.")
            # --- FIN TEMAS CLAVE GENERALES ---


            # --- TOP 10 Tweets por ViewCount ---
            st.subheader("🔥 Top 10 Tweets Más Vistos")

            # Asegurarse de que 'viewCount' sea numérico y no nulo
            df_sorted_by_views = df.dropna(subset=['viewCount']).sort_values(by='viewCount', ascending=False)

            if not df_sorted_by_views.empty:
                # Seleccionar todas las columnas del DataFrame original para los top 10 tweets
                top_10_views = df_sorted_by_views.head(10)

                # Formatear 'viewCount' para mejor lectura en la tabla si se muestran todas las columnas
                top_10_views_display = top_10_views.copy()
                if 'viewCount' in top_10_views_display.columns:
                    top_10_views_display['viewCount'] = top_10_views_display['viewCount'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")

                st.dataframe(top_10_views_display, use_container_width=True, hide_index=True,
                            column_config={
                                "author/profilePicture": st.column_config.ImageColumn("Foto de Perfil"), # Added profile picture
                                "url": st.column_config.LinkColumn("URL del Tweet"),
                                "viewCount": st.column_config.NumberColumn("Visualizaciones", format="%d"),
                                "createdAt": st.column_config.DateColumn("Fecha de Creación", format="YYYY-MM-DD"),
                                "author/userName": st.column_config.TextColumn("Usuario"),
                                "author/followers": st.column_config.NumberColumn("Seguidores", format="%d"),
                                "likeCount": st.column_config.NumberColumn("Likes", format="%d"),
                                "replyCount": st.column_config.NumberColumn("Respuestas", format="%d"),
                                "retweetCount": st.column_config.NumberColumn("Retweets", format="%d"),
                                "quoteCount": st.column_config.NumberColumn("Citas", format="%d"),
                                "bookmarkCount": st.column_config.NumberColumn("Guardados", format="%d"),
                                "source": st.column_config.TextColumn("Fuente"),
                                "text": st.column_config.TextColumn("Contenido del Tweet"),
                            })
            else:
                st.info("No hay datos de visualizaciones disponibles para mostrar el top 10.")
            # --- FIN TOP 10 Tweets por ViewCount ---

            # --- TOP 10 Usuarios por Seguidores ---
            st.markdown("---")
            st.subheader("👑 Top 10 Usuarios con Más Seguidores")

            # Asegurarse de que 'author/followers' y 'author/userName' no sean nulos
            df_users_sorted = df.dropna(subset=['author/followers', 'author/userName'])

            if not df_users_sorted.empty:
                # Agrupar por usuario y obtener el máximo de seguidores y la primera foto de perfil encontrada
                top_users = df_users_sorted.groupby('author/userName').agg(
                    **{'author/followers': pd.NamedAgg(column='author/followers', aggfunc='max'),
                       'author/profilePicture': pd.NamedAgg(column='author/profilePicture', aggfunc='first')}
                ).reset_index()

                top_users = top_users.sort_values(by='author/followers', ascending=False).head(10)

                # Formatear 'author/followers' para mejor lectura
                top_users_display = top_users.copy()
                top_users_display['author/followers'] = top_users_display['author/followers'].apply(lambda x: f"{int(x):,}")

                st.dataframe(top_users_display, use_container_width=True, hide_index=True,
                            column_config={
                                "author/profilePicture": st.column_config.ImageColumn("Foto de Perfil"), # Added profile picture
                                "author/userName": st.column_config.TextColumn("Usuario"),
                                "author/followers": st.column_config.NumberColumn("Seguidores", format="%d")
                            })
            else:
                st.info("No hay datos de seguidores disponibles para mostrar el top 10 de usuarios.")
            # --- FIN TOP 10 Usuarios por Seguidores ---

            # Gráfico de torta con Plotly
            st.subheader("📊 Distribución de Sentimientos")
            counts = df['sentimiento'].value_counts().reset_index()
            counts.columns = ['Sentimiento', 'Cantidad']

            # Calcular porcentajes
            counts['Porcentaje'] = counts['Cantidad'] / counts['Cantidad'].sum() * 100

            # --- Resumen de Porcentajes ---
            st.markdown("### Resumen Rápido")
            summary_df = counts[['Sentimiento', 'Porcentaje']].copy()
            summary_df['Porcentaje'] = summary_df['Porcentaje'].round(2).astype(str) + '%'
            st.dataframe(summary_df, hide_index=True, use_container_width=True)

            # Crear el gráfico de torta con Matplotlib/Seaborn, ahora más pequeño y con labels reducidos
            colors = ['#F44336',"#797979","#11D54F"]
            plt.figure(figsize=(3, 3)) 
            plt.pie(counts['Cantidad'], labels=counts['Sentimiento'], autopct='%1.1f%%', startangle=140, colors=colors, textprops={'fontsize': 6})
            plt.title('Distribución de Sentimientos de los Tweets', fontsize=6)
            plt.axis('equal')  # Ensures the pie chart is circular
            plt.tight_layout() 
            st.pyplot(plt, use_container_width=False) # <--- AQUI ESTA LA CLAVE


            # --- Temas principales por sentimiento ---
            st.subheader("🔍 Temas Principales por Sentimiento")

            # Usar st.expander para organizar los temas
            for tipo in ["POSITIVO", "NEGATIVO", "NEUTRO"]:
                subset = df[df["sentimiento"] == tipo]["text"].astype(str).tolist()
                if subset:
                    with st.expander(f"Mostrar temas **{tipo}** ({len(subset)} tweets)"):
                        with st.spinner(f"Extrayendo temas {tipo}..."):
                            resumen = extraer_temas_con_ia(subset, tipo, contexto)
                        mostrar_temas_con_contraste(resumen)
                else:
                    st.info(f"No hay tweets clasificados como **{tipo}** para analizar temas.")

            if 'createdAt' in df.columns:
                df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
                df = df.dropna(subset=['createdAt'])

                # Calcular el rango de fechas
                min_date = df['createdAt'].min().date()
                max_date = df['createdAt'].max().date()
                date_range_days = (max_date - min_date).days

                # Determinar frecuencia
                if date_range_days <= 3:
                    df['time_bucket'] = df['createdAt'].dt.strftime('%H:00')  # por hora
                    xaxis_label = 'Hora'
                elif date_range_days <= 150:
                    df['time_bucket'] = df['createdAt'].dt.strftime('%Y-%m-%d')  # por día
                    xaxis_label = 'Fecha'
                else:
                    df['time_bucket'] = df['createdAt'].dt.to_period('M').astype(str)  # por mes
                    xaxis_label = 'Mes'

                # --- MÉTRICA: Evolución temporal de tweets ---
            st.markdown("---")
            st.subheader("📈 Evolución de Tweets en el Tiempo")

            tweet_count_timeline = df.groupby('time_bucket').size().reset_index(name='Cantidad de Tweets')

            # Use Seaborn to create the line plot, now more compact
            plt.figure(figsize=(5, 3)) 
            ax = sns.lineplot(
                data=tweet_count_timeline,
                x='time_bucket',
                y='Cantidad de Tweets',
                linewidth=0.8
            )
            plt.title('Cantidad de Tweets por ' + xaxis_label, fontsize=6)
            plt.xlabel(xaxis_label, fontsize=4)
            plt.ylabel('Número de Tweets', fontsize=4)
            plt.xticks(rotation=45, ha='right', fontsize=4)
            plt.yticks(fontsize=4)
            ax.set_ylim(bottom=0)  # <-- Eje Y empieza en 0
            plt.tight_layout() 
            st.pyplot(plt, use_container_width=False) # <--- AQUI ESTA LA CLAVE

            # Guardar gráficos como imágenes
            grafico_sentimiento_buf = io.BytesIO()
            plt.figure(figsize=(3, 3))
            plt.pie(counts['Cantidad'], labels=counts['Sentimiento'], autopct='%1.1f%%', startangle=140, colors=colors, textprops={'fontsize': 6})
            plt.title('Distribución de Sentimientos de los Tweets', fontsize=6)
            plt.axis('equal')
            plt.tight_layout()
            plt.savefig(grafico_sentimiento_buf, format='png', dpi=300)
            grafico_sentimiento_buf.seek(0)

            # --- Línea temporal
            grafico_timeline_buf = io.BytesIO()
            plt.figure(figsize=(5, 3))
            sns.lineplot(data=tweet_count_timeline, x='time_bucket', y='Cantidad de Tweets', linewidth=0.8)
            plt.title('Cantidad de Tweets por ' + xaxis_label, fontsize=6)
            plt.xlabel(xaxis_label, fontsize=4)
            plt.ylabel('Número de Tweets', fontsize=4)
            plt.xticks(rotation=45, ha='right', fontsize=4)
            plt.yticks(fontsize=4)
            plt.tight_layout()
            plt.savefig(grafico_timeline_buf, format='png')
            grafico_timeline_buf.seek(0)
            temas_por_sentimiento = {}
            for tipo in ["POSITIVO", "NEGATIVO", "NEUTRO"]:
                subset = df[df["sentimiento"] == tipo]["text"].astype(str).tolist()
                if subset:
                    resumen = extraer_temas_con_ia(subset, tipo, contexto)
                    temas_por_sentimiento[tipo] = resumen
                    with st.expander(f"Mostrar temas **{tipo}** ({len(subset)} tweets)"):
                        mostrar_temas_con_contraste(resumen)
                else:
                    temas_por_sentimiento[tipo] = "No hay tweets para este sentimiento."




            def parse_temas_formateados(texto_temas):
                """
                Devuelve una lista de dicts con {tema, descripcion, ejemplo, usuario}.
                Soporta el formato:
                1. [Nombre del tema]
                [Breve explicación]
                Ejemplo: "[tweet de ejemplo]", [author/userName: usuario]
                """
                if not texto_temas:
                    return []

                pattern = r"(\d+)\.\s*([^\n]+)\n(.*?)\nEjemplo:\s*\"([^\"]+)\",\s*\[author/userName:\s*([^\]]+)\]"
                matches = re.findall(pattern, texto_temas, re.MULTILINE | re.DOTALL)

                items = []
                for _, tema, descripcion, ejemplo, usuario in matches:
                    items.append({
                        "tema": (tema or "").strip(),
                        "descripcion": (descripcion or "").strip(),
                        "ejemplo": (ejemplo or "").strip(),
                        "usuario": (usuario or "").strip()
                    })
                return items
                        
            # --- Helper functions for PDF generation ---
            # Global cache for profile pictures to avoid re-downloading
            _profile_pic_cache = {}

            def _fetch_profile_pic(url, username=""):
                """
                Fetches a profile picture from a URL and returns its path.
                Caches the image to a temporary file.
                Returns a default placeholder if the download fails.
                """
                if not url:
                    return None # No URL provided

                if url in _profile_pic_cache:
                    return _profile_pic_cache[url]

                try:
                    response = requests.get(url, stream=True, timeout=5)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                    img_data = io.BytesIO(response.content)
                    img = Image.open(img_data)

                    # Create a unique temporary file name
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    img.save(temp_file.name, format="PNG") # Convert to PNG for FPDF compatibility
                    temp_file_path = temp_file.name
                    temp_file.close()

                    _profile_pic_cache[url] = temp_file_path
                    return temp_file_path
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading profile pic for {username} from {url}: {e}")
                    return None
                except Exception as e:
                    print(f"Error processing profile pic for {username} from {url}: {e}")
                    return None

            def _fmt_int(x):
                try:
                    return f"{int(x):,}"
                except:
                    return "-"
                

            def _fmt_date(dtlike):
                if not dtlike:
                    return "-"
                try:
                    if isinstance(dtlike, str):
                        return datetime.fromisoformat(str(dtlike).replace("Z","")).strftime("%Y-%m-%d")
                    return dtlike.strftime("%Y-%m-%d")
                except:
                    return str(dtlike)[:10]

            def _truncate(text, max_chars=120):
                s = str(text or "").replace("\n"," ").strip()
                return (s[:max_chars] + "…") if len(s) > max_chars else s

            def _table_header(pdf, cols, widths, fill_rgb=(240,242,245), text_rgb=(0,0,0)):
                pdf.set_fill_color(*fill_rgb)
                pdf.set_text_color(*text_rgb)
                pdf.set_font("Arial", 'B', 10)
                for title, w in zip(cols, widths):
                    pdf.cell(w, 8, title, border=1, ln=0, align='C', fill=True)
                pdf.ln(8)
                pdf.set_text_color(0,0,0)
                pdf.set_font("Arial", '', 9)

            def _ensure_page_space(pdf, needed_h=12):
                if pdf.get_y() + needed_h > pdf.page_break_trigger:
                    pdf.add_page()

            
            def _add_top_tweets_table(pdf, df):
                """
                Adds the Top 10 Tweets as a formatted table to the PDF, including profile pictures.
                """
                pdf.ln(5)

                # Define columns and widths
                # Added 'Pic' column, adjusted other widths slightly
                cols = ['Pic', 'Tweet', 'Usuario', 'Seguidores', 'Fecha', 'Vistas']
                # Total width: 5 (pic) + 70 (tweet) + 30 (user) + 25 (followers) + 20 (date) + 20 (views) = 170mm
                widths = [8, 65, 30, 25, 20, 20] # Adjust widths to fit all columns.

                _table_header(pdf, cols, widths)

                pdf.set_font("Arial", '', 8)

                top_10 = df.sort_values(by='viewCount', ascending=False).head(10)

                # Fixed height for each row to accommodate the profile picture
                # This means the tweet text might be truncated more aggressively
                ROW_HEIGHT = 10 # mm, this will be the height of each table row

                for _, row in top_10.iterrows():
                    _ensure_page_space(pdf, needed_h=ROW_HEIGHT + 2) # Add a small buffer

                    current_x = pdf.get_x()
                    current_y = pdf.get_y()

                    # 1. Profile Picture
                    profile_pic_url = row.get('author/profilePicture', '')
                    username = row.get('author/userName', 'unknown')
                    pic_path = _fetch_profile_pic(profile_pic_url, username)
                    
                    pic_x = current_x + (widths[0] - 6) / 2 # Center image
                    pic_y = current_y + (ROW_HEIGHT - 6) / 2 # Center image
                    
                    if pic_path:
                        pdf.image(pic_path, x=pic_x, y=pic_y, w=6, h=6) # 6x6mm image
                    else:
                        # Draw a simple grey square placeholder if image fails to load
                        pdf.set_fill_color(200, 200, 200)
                        pdf.rect(pic_x, pic_y, 6, 6, 'F')
                        pdf.set_fill_color(255, 255, 255) # Reset fill color

                    # Draw cell border for pic
                    pdf.set_xy(current_x, current_y)
                    pdf.cell(widths[0], ROW_HEIGHT, '', border=1, ln=0, align='C')

                    # 2. Tweet Text (truncated to fit)
                    text = _truncate(row.get('text', '-'), max_chars=80) # More aggressive truncation
                    pdf.set_xy(current_x + widths[0], current_y)
                    pdf.multi_cell(widths[1], ROW_HEIGHT/2, eliminar_emojis(text), border=1, align='L')

                    # 3. User Name
                    username_text = _truncate(row.get('author/userName', '-'), max_chars=18)
                    pdf.set_xy(current_x + widths[0] + widths[1], current_y)
                    pdf.cell(widths[2], ROW_HEIGHT, eliminar_emojis(username_text), border=1, ln=0, align='C')

                    # 4. Followers
                    followers = _fmt_int(row.get('author/followers', 0))
                    pdf.set_xy(current_x + widths[0] + widths[1] + widths[2], current_y)
                    pdf.cell(widths[3], ROW_HEIGHT, followers, border=1, ln=0, align='C')

                    # 5. Created At
                    createdAt = _fmt_date(row.get('createdAt', '-'))
                    pdf.set_xy(current_x + widths[0] + widths[1] + widths[2] + widths[3], current_y)
                    pdf.cell(widths[4], ROW_HEIGHT, createdAt, border=1, ln=0, align='C')

                    # 6. View Count
                    viewCount = _fmt_int(row.get('viewCount', 0))
                    pdf.set_xy(current_x + widths[0] + widths[1] + widths[2] + widths[3] + widths[4], current_y)
                    pdf.cell(widths[5], ROW_HEIGHT, viewCount, border=1, ln=1, align='C') # ln=1 to move to next line

                # Important: Clean up temporary files after PDF generation
                for path in _profile_pic_cache.values():
                    try:
                        os.remove(path)
                    except OSError as e:
                        print(f"Error removing temporary file {path}: {e}")
                _profile_pic_cache.clear() # Clear the cache


            def _add_top_users_table(pdf, df):
                """
                Adds the Top 10 Users as a formatted table to the PDF, including profile pictures.
                """
                pdf.ln(5)

                # Define columns and widths for the user table
                cols = ['Pic', 'Usuario', 'Seguidores']
                widths = [10, 80, 40]
                
                _table_header(pdf, cols, widths)
                pdf.set_font("Arial", '', 9)

                # Agrupar por usuario para obtener el máximo de seguidores y la primera foto de perfil
                top_users_df = df.dropna(subset=['author/followers', 'author/userName'])
                top_users_df = top_users_df.groupby('author/userName').agg(
                    **{'author/followers': pd.NamedAgg(column='author/followers', aggfunc='max'),
                    'author/profilePicture': pd.NamedAgg(column='author/profilePicture', aggfunc='first')}
                ).reset_index()
                top_users = top_users_df.sort_values(by='author/followers', ascending=False).head(10)
                
                ROW_HEIGHT = 12 # Fixed height for each row

                for _, row in top_users.iterrows():
                    _ensure_page_space(pdf, needed_h=ROW_HEIGHT + 2)
                    
                    current_x = pdf.get_x()
                    current_y = pdf.get_y()
                    
                    # 1. Profile Picture
                    profile_pic_url = row.get('author/profilePicture', '')
                    username = row.get('author/userName', 'unknown')
                    pic_path = _fetch_profile_pic(profile_pic_url, username)
                    
                    pic_x = current_x + (widths[0] - 8) / 2
                    pic_y = current_y + (ROW_HEIGHT - 8) / 2
                    
                    if pic_path:
                        pdf.image(pic_path, x=pic_x, y=pic_y, w=8, h=8)
                    else:
                        pdf.set_fill_color(200, 200, 200)
                        pdf.rect(pic_x, pic_y, 8, 8, 'F')
                        pdf.set_fill_color(255, 255, 255)

                    pdf.set_xy(current_x, current_y)
                    pdf.cell(widths[0], ROW_HEIGHT, '', border=1, ln=0, align='C')
                    
                    # 2. User Name
                    username_text = _truncate(row.get('author/userName', '-'), max_chars=40)
                    pdf.set_xy(current_x + widths[0], current_y)
                    pdf.cell(widths[1], ROW_HEIGHT, eliminar_emojis(username_text), border=1, ln=0, align='C')
                    
                    # 3. Followers
                    followers = _fmt_int(row.get('author/followers', 0))
                    pdf.set_xy(current_x + widths[0] + widths[1], current_y)
                    pdf.cell(widths[2], ROW_HEIGHT, followers, border=1, ln=1, align='C')

                # Cleanup temporary files
                for path in _profile_pic_cache.values():
                    try:
                        os.remove(path)
                    except OSError as e:
                        print(f"Error removing temporary file {path}: {e}")
                _profile_pic_cache.clear()

            # --- Updated `generar_pdf` function ---
            def generar_pdf(df, resumen_sentimientos, temas_generales, temas_por_sentimiento,
                            grafico_sentimiento, grafico_timeline):
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()

                COLOR_BG_HEADER = (240, 242, 245)
                COLOR_TEXT = (0, 0, 0)
                COLOR_SUBT = (80, 80, 80)

                def section_header(texto):
                    pdf.set_fill_color(*COLOR_BG_HEADER)
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, eliminar_emojis(texto), ln=True, fill=True)
                    pdf.ln(2)

                def write_kpi_line(texto, size=11):
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.set_font("Arial", '', size)
                    # The width 180 is chosen to provide a good margin on both sides of an A4 page.
                    # It ensures the text wraps correctly instead of overflowing.
                    pdf.multi_cell(180, 7, eliminar_emojis(texto), align='L')

                def write_tema_block(tema, descripcion, ejemplo, usuario):
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.set_font("Arial", 'B', 12)
                    # Changed width from 0 to 180
                    pdf.multi_cell(180, 7, eliminar_emojis(tema.upper()), align='L')
                    pdf.set_font("Arial", '', 10)
                    # This line was already fixed in a previous step
                    pdf.multi_cell(180, 6, eliminar_emojis(descripcion), align='L')
                    pdf.set_text_color(*COLOR_SUBT)
                    pdf.set_font("Arial", 'I', 10)
                    ejem = f'Ejemplo: "{ejemplo}" — @{usuario}' if usuario else f'Ejemplo: "{ejemplo}"'
                    # Changed width from 0 to 180
                    pdf.multi_cell(180, 6, eliminar_emojis(ejem), align='L')
                    pdf.ln(2)
                    pdf.set_text_color(*COLOR_TEXT)
                
                # ---------- Portada / Métricas ----------
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, eliminar_emojis("Reporte de Scraping y Análisis de Tweets"), ln=True, align='C')
                pdf.ln(5)

                total_views = df['viewCount'].sum()
                total_interacciones = df[['likeCount', 'replyCount', 'retweetCount', 'quoteCount', 'bookmarkCount']].fillna(0).sum().sum()
                promedio_vistas = total_views / len(df) if len(df) > 0 else 0
                promedio_interacciones = total_interacciones / len(df) if len(df) > 0 else 0


                write_kpi_line(f"Tweets recolectados: {len(df)}")
                write_kpi_line(f"Visualizaciones totales: {int(total_views):,}")
                write_kpi_line(f"Interacciones totales: {int(total_interacciones):,}")
                write_kpi_line(f"Promedio por tweet: {int(promedio_vistas):,} vistas / {int(promedio_interacciones):,} interacciones")

                pdf.ln(2)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img2:
                    tmp_img2.write(grafico_timeline.getvalue())
                    tmp_img2_path = tmp_img2.name
                pdf.image(tmp_img2_path, w=170)
                os.remove(tmp_img2_path)

                # ---------- Temas Generales ----------
                pdf.add_page()
                COLOR_BG_HEADER = (255, 165, 0)
                section_header("Temas Generales")
                COLOR_BG_HEADER = (240, 242, 245)

                items_generales = parse_temas_formateados(temas_generales)
                if items_generales:
                    for it in items_generales:
                        write_tema_block(it["tema"], it["descripcion"], it["ejemplo"], it["usuario"])
                else:
                    write_kpi_line(temas_generales or "Sin información")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                    tmp_img.write(grafico_sentimiento.getvalue())
                    tmp_img_path = tmp_img.name
                pdf.image(tmp_img_path, w=170)
                os.remove(tmp_img_path)
                pdf.ln(2)

                # ---------- Temas por Sentimiento ----------
                pdf.add_page()
                for tipo, resumen in temas_por_sentimiento.items():
                    pdf.ln(1)
                    if tipo == "POSITIVO":
                        COLOR_BG_HEADER = (76, 175, 80)
                    elif tipo == "NEGATIVO":
                        COLOR_BG_HEADER = (244, 67, 54)
                    else:
                        COLOR_BG_HEADER = (158, 158, 158)

                    section_header(f"Temas {tipo}")
                    COLOR_BG_HEADER = (240, 242, 245)

                    items = parse_temas_formateados(resumen)
                    if items:
                        for it in items:
                            write_tema_block(it["tema"], it["descripcion"], it["ejemplo"], it["usuario"])
                    else:
                        write_kpi_line(resumen or "No se encontraron temas.")
                    pdf.add_page()

                # ---------- Top 10 Tweets (TABLE) ----------
                COLOR_BG_HEADER = (255, 165, 0)
                section_header("Top 10 Tweets Más Vistos")
                COLOR_BG_HEADER = (240, 242, 245)
                _add_top_tweets_table(pdf, df)

                # ---------- Top 10 Usuarios (TABLE) ----------
                pdf.add_page()
                COLOR_BG_HEADER = (255, 165, 0)
                section_header("Top 10 Usuarios con Más Seguidores")
                COLOR_BG_HEADER = (240, 242, 245)
                _add_top_users_table(pdf, df)


                pdf_output = pdf.output(dest='S').encode('latin-1')
                buffer = io.BytesIO(pdf_output)
                return buffer


            # # --- Descarga ---
            # st.markdown("---")
            # st.subheader("⬇️ Descargar Resultados")
            # st.download_button(
            #     label="Descargar resultados completos (CSV)",
            #     data=df.to_csv(index=False).encode('utf-8'),
            #     file_name="tweets_analizados.csv",
            #     mime="text/csv",
            #     help="Descarga un archivo CSV con todos los tweets recolectados y su clasificación de sentimiento."
            # )

            st.markdown("---")
            st.subheader("⬇️ Descargar Reporte en PDF")

            pdf_buffer = generar_pdf(
                df=df,
                resumen_sentimientos=summary_df,
                temas_generales=temas_generales,
                temas_por_sentimiento=temas_por_sentimiento,
                grafico_sentimiento=grafico_sentimiento_buf,
                grafico_timeline=grafico_timeline_buf
            )

            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_buffer,
                file_name="reporte_tweets.pdf",
                mime="application/pdf"
            )

            st.markdown("---")
            st.info("✨ Aplicación creada con Streamlit, Apify y Google Gemini.")


# --- Lógica principal para mostrar la página de login o la aplicación ---
if st.session_state["logged_in"]:
    main_app()
else:
    login_page()

