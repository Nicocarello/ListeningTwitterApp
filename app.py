# scrapper_analysis_app.py

import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import google.generativeai as genai
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.express as px
import re

# --- Configuración inicial de la página ---
st.set_page_config(
    page_title="Twitter Scraper + Sentimiento",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Dominio de correo electrónico de la empresa (¡IMPORTANTE: CAMBIA ESTO!) ---
# Reemplaza 'tuempresa.com' con el dominio real de tu empresa.
# Por ejemplo, si los correos son 'usuario@miempresa.com', entonces el dominio es 'miempresa.com'.
COMPANY_EMAIL_DOMAIN = st.secrets.get("COMPANY_EMAIL_DOMAIN")

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
    st.experimental_rerun() # Recargar la página para volver a la pantalla de login

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
                "maxItems": 10000, # Mantener un límite razonable para evitar usos excesivos de la API
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

    # --- Funciones IA ---
    def clasificar_tweet(tweet, contexto):
        if not model:
            return "NEUTRO" # Retorna neutro si el modelo no está inicializado
        prompt = f"""CONTEXTO: {contexto}
        Clasifica el sentimiento del siguiente tweet en POSITIVO, NEGATIVO o NEUTRO.
        Responde únicamente con POSITIVO, NEGATIVO o NEUTRO. Ninguna palabra más.
        Tweet: "{tweet}"\nSentimiento:"""
        try:
            response = model.generate_content(prompt, generation_config={"temperature": 0.2})
            return response.text.strip().upper()
        except Exception as e:
            # st.warning(f"Error al clasificar tweet: {e}. Asignando 'NEUTRO'.") # Descomentar para depurar
            return "NEUTRO"

    def extraer_temas_con_ia(tweets, sentimiento, contexto, num_temas=3):
        if not model:
            return "El modelo de IA no está disponible para extraer temas."
        prompt = f"""CONTEXTO: {contexto}
        Aquí hay tweets clasificados como {sentimiento}. Extrae los {num_temas} temas principales, explicando brevemente cada uno y dando un ejemplo.
        Formato de salida:
        Tema: [nombre del tema 1]
        Explicación: [breve explicación]
        Ejemplo: "[tweet de ejemplo relevante]"\n
        Tema: [nombre del tema 2]
        Explicación: [breve explicación]
        Ejemplo: "[tweet de ejemplo relevante]"\n
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

    # --- NUEVA FUNCIÓN PARA TEMAS GENERALES ---
    def extraer_temas_generales_con_ia(tweets, contexto, num_temas=5):
        if not model:
            return "El modelo de IA no está disponible para extraer temas generales."

        prompt = f"""CONTEXTO: {contexto}
        Analiza la siguiente colección de tweets y extrae los {num_temas} temas principales o más mencionados.
        Para cada tema, proporciona un nombre, una breve explicación y un tweet de ejemplo relevante que lo ilustre.
        Formato de salida:
        [nombre del tema 1]:[breve explicación]\n
        Ejemplo: "*tweet de ejemplo relevante*", [usuario autor del tweet (author/userName)]\n
        [nombre del tema 2]:[breve explicación]\n
        Ejemplo: "*tweet de ejemplo relevante*", [usuario autor del tweet (author/userName)]\n
        ---
        Tweets para analizar:\n"""

        # Tomar una muestra de tweets si hay muchos, para no exceder el límite de tokens de la API
        # y para mantener la respuesta rápida. Ajusta el número según sea necesario.
        sample_tweets = tweets[:min(len(tweets), 500)] # Limita a 1000 tweets para el análisis general
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

            # --- Clasificación de Sentimientos ---
            st.subheader("🧠 Clasificando Sentimientos...")

            # Progreso de la clasificación
            progress_bar = st.progress(0)
            status_text = st.empty()

            resultados = ["NEUTRO"] * len(df)
            tweets_validos = [(i, t) for i, t in enumerate(df['text']) if pd.notna(t) and str(t).strip()]

            total_tweets_to_classify = len(tweets_validos)
            classified_count = 0

            with ThreadPoolExecutor(max_workers=5) as executor: # Reducir workers para evitar rate limits o sobrecarga
                futures = {executor.submit(clasificar_tweet, t, contexto): i for i, t in tweets_validos}
                for f in as_completed(futures):
                    idx = futures[f]
                    try:
                        resultados[idx] = f.result()
                    except:
                        resultados[idx] = "NEUTRO"

                    classified_count += 1
                    progress = min(classified_count / total_tweets_to_classify, 1.0)
                    progress_bar.progress(progress)
                    status_text.text(f"Clasificando: {classified_count}/{total_tweets_to_classify} tweets procesados.")

            df["sentimiento"] = resultados
            st.success("✅ Clasificación de sentimientos completada.")
            progress_bar.empty() # Ocultar barra de progreso
            status_text.empty() # Ocultar texto de estado

            # --- TEMAS CLAVE GENERALES (NUEVA SECCIÓN AQUÍ) ---
            st.markdown("---")
            st.subheader("💡 Temas Clave del Conjunto Total de Tweets")

            all_tweets_text = df['text'].astype(str).tolist()
            if all_tweets_text:
                with st.spinner("Extrayendo temas clave generales..."):
                    temas_generales = extraer_temas_generales_con_ia(all_tweets_text, contexto)
                st.markdown(temas_generales)
            else:
                st.warning("No hay tweets para extraer temas clave generales.")
            # --- FIN TEMAS CLAVE GENERALES ---


            # --- TOP 10 Tweets por ViewCount ---
            st.markdown("---")
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
                                "sentimiento": st.column_config.TextColumn("Sentimiento")
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

            # Gráfico de torta con Plotly
            fig = px.pie(
                counts,
                values='Cantidad',
                names='Sentimiento',
                title='Distribución de Sentimientos de los Tweets',
                hover_data=['Porcentaje'],
                labels={'Porcentaje': 'Porcentaje (%)'},
                color='Sentimiento',
                color_discrete_map={
                    'POSITIVO': '#4CAF50', # Green
                    'NEGATIVO': '#F44336', # Red
                    'NEUTRO': '#9E9E9E'     # Grey
                }
            )

            fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
            fig.update_layout(
                margin=dict(t=40, b=0, l=0, r=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)


            # --- Temas principales por sentimiento ---
            st.subheader("🔍 Temas Principales por Sentimiento")

            # Usar st.expander para organizar los temas
            for tipo in ["POSITIVO", "NEGATIVO", "NEUTRO"]:
                subset = df[df["sentimiento"] == tipo]["text"].astype(str).tolist()
                if subset:
                    with st.expander(f"Mostrar temas **{tipo}** ({len(subset)} tweets)"):
                        with st.spinner(f"Extrayendo temas {tipo}..."):
                            resumen = extraer_temas_con_ia(subset, tipo, contexto)
                        st.markdown(resumen.replace("---", "---\n"))
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
                    df['time_bucket'] = df['createdAt'].dt.strftime('%Y-%m-%d %H:00')  # por hora
                    xaxis_label = 'Hora'
                elif date_range_days <= 150:
                    df['time_bucket'] = df['createdAt'].dt.date  # por día
                    xaxis_label = 'Fecha'
                else:
                    df['time_bucket'] = df['createdAt'].dt.to_period('M').astype(str)  # por mes
                    xaxis_label = 'Mes'

                # --- MÉTRICA: Evolución temporal de tweets ---
                st.markdown("---")
                st.subheader("📈 Evolución de Tweets en el Tiempo")

                tweet_count_timeline = df.groupby('time_bucket').size().reset_index(name='Cantidad de Tweets')

                fig_timeline = px.line(
                    tweet_count_timeline,
                    x='time_bucket',
                    y='Cantidad de Tweets',
                    title='Cantidad de Tweets por ' + xaxis_label,
                    markers=True,
                    line_shape='spline'
                )
                fig_timeline.update_layout(
                    xaxis_title=xaxis_label,
                    yaxis_title='Número de Tweets',
                    margin=dict(t=40, b=0, l=0, r=0),
                    yaxis_range=[0, None]
                )
                st.plotly_chart(fig_timeline, use_container_width=True)


            # --- Descarga ---
            st.markdown("---")
            st.subheader("⬇️ Descargar Resultados")
            st.download_button(
                label="Descargar resultados completos (CSV)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="tweets_analizados.csv",
                mime="text/csv",
                help="Descarga un archivo CSV con todos los tweets recolectados y su clasificación de sentimiento."
            )

            st.markdown("---")
            st.info("✨ Aplicación creada con Streamlit, Apify y Google Gemini.")


# --- Lógica principal para mostrar la página de login o la aplicación ---
if st.session_state["logged_in"]:
    main_app()
else:
    login_page()

