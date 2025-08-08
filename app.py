# scrapper_analysis_app.py

import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import google.generativeai as genai
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.express as px
import re
import io
import json
import random
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
COMPANY_EMAIL_DOMAIN = "publicalatam.com"

# --- Inicializar el estado de la sesión ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "results" not in st.session_state:
    st.session_state["results"] = None

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
    st.image("https://publicalab.com/assets/imgs/logo-publica-blanco.svg", width=300)
    email = st.text_input("Correo Electrónico")
    if st.button("Ingresar"):
        if email.endswith(COMPANY_EMAIL_DOMAIN):
            st.session_state.logged_in = True
            st.session_state.email = email
            st.success("¡Inicio de sesión exitoso!")
            st.rerun()
        else:
            st.error("Por favor, ingresa un correo electrónico válido.")

# --- Función de Logout ---
def logout():
    st.session_state["logged_in"] = False
    st.info("Has cerrado sesión.")
    st.experimental_rerun()

# --- Contenido principal de la aplicación ---
def main_app():
    st.image("https://publicalab.com/assets/imgs/logo-publica-blanco.svg", width=200)
    st.markdown("<h1 class='big-title'>🐦 Scraping + Análisis de Sentimiento de Tweets</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Extrae tweets, clasifica su sentimiento y descubre los temas clave.</p>", unsafe_allow_html=True)

    apify_token = st.secrets.get("apify_token")
    gemini_api_key = st.secrets.get("gemini_api_key")

    model = None
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
    else:
        st.error("Por favor, configura tu GEMINI_API_KEY en `.streamlit/secrets.toml` para habilitar el análisis de sentimiento.")

    @st.cache_data(ttl=3600)
    def get_twitter_data(search_terms, start_date, end_date, sort_type):
        try:
            apify_client = ApifyClient(apify_token)
            actor_id = "apidojo/twitter-scraper-lite"
            run_input = {
                "end": end_date,
                "maxItems": 1000,
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

                df['viewCount'] = pd.to_numeric(df['viewCount'], errors='coerce').fillna(0)
                df['author/followers'] = pd.to_numeric(df['author/followers'], errors='coerce').fillna(0)

                all_columns = ['author/profilePicture','text', 'createdAt', 'author/userName', 'author/followers', 'url', 'likeCount',
                               'replyCount', 'retweetCount', 'quoteCount', 'bookmarkCount', 'viewCount', 'source']
                df = df[[col for col in all_columns if col in df.columns]]

                df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error al obtener datos de Twitter: {e}. Asegúrate de que tu token de Apify sea válido y los términos de búsqueda sean apropiados.")
            return pd.DataFrame()

    def clasificar_tweets_en_lote(tweets, contexto, model):
        if not model:
            return ["NEUTRO"] * len(tweets)

        prompt = f"""CONTEXTO: {contexto}
        Clasifica el sentimiento de cada uno de los siguientes tweets en POSITIVO, NEGATIVO o NEUTRO.
        Responde con una lista de sentimientos, un sentimiento por cada tweet.
        El formato de salida debe ser estrictamente una lista JSON de strings, por ejemplo: `["POSITIVO", "NEGATIVO", "NEUTRO"]`.
        
        TWEETS:
        """
        for i, tweet in enumerate(tweets):
            prompt += f"Tweet {i+1}: '{tweet}'\n"
        
        prompt += "SENTIMIENTOS (en formato de lista JSON):"

        try:
            response = model.generate_content(prompt, generation_config={"temperature": 0.2})
            response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            sentimientos_ia = json.loads(response_text)
            
            if isinstance(sentimientos_ia, list) and len(sentimientos_ia) == len(tweets):
                return [s.upper() for s in sentimientos_ia]
            else:
                return ["NEUTRO"] * len(tweets)
        except Exception as e:
            st.error(f"Error en la clasificación de tweets en lote: {e}")
            return ["NEUTRO"] * len(tweets)
    
    def mostrar_temas_con_contraste(texto_temas):
        pattern = r"(\d+)\.\s*([^\n]+)\n(.*?)\nEjemplo:\s*\"([^\"]+)\",\s*\[author/userName:\s*([^\]]+)\]"
        
        if not texto_temas:
            st.info("No se encontraron temas para mostrar.")
            return

        matches = re.findall(pattern, texto_temas, re.MULTILINE | re.DOTALL)

        if not matches:
            st.warning("No se pudo extraer el formato de temas esperado. Mostrando texto sin formato.")
            st.markdown(texto_temas)
            return

        for numero, tema, explicacion, ejemplo, usuario in matches:
            st.markdown(f"**<span style='font-size: 1.5em;'>{numero}. {tema.strip()}</span>**", unsafe_allow_html=True)
            st.markdown(f"**Descripción:** {explicacion.strip()}")
            st.markdown(f"**Ejemplo:** *\"{ejemplo.strip()}\"* - **@{usuario.strip()}**")
            st.markdown("---")

    def extraer_temas_con_ia(tweets, sentimiento, contexto, num_temas=3):
        if not model:
            return "El modelo de IA no está disponible para extraer temas."
        prompt = f"""CONTEXTO: {contexto}
        Aquí hay tweets clasificados como {sentimiento}. Extrae los {num_temas} temas principales, explicando brevemente cada uno y dando un ejemplo.
        Formato de salida:
        Tema: [nombre del tema 1]:  [breve explicación]
        Ejemplo: "[tweet de ejemplo relevante]"\n
        Tema: [nombre del tema 2]:  [breve explicación]
        Ejemplo: "[tweet de ejemplo relevante]"\n
        ---
        Tweets para analizar:\n"""
        texto = "\n".join(tweets[:500])
        if not texto.strip():
            return "No hay tweets suficientes para extraer temas."

        try:
            response = model.generate_content(prompt + texto, generation_config={"temperature": 0.4})
            return response.text.strip()
        except Exception as e:
            st.error(f"Error al extraer temas con IA: {e}")
            return "No se pudieron extraer temas."

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
        
            
    # --- Función para generar PDF (MEJORADA) ---
    def generar_pdf(df, counts, fig_pie, fig_timeline, top_10_views, top_10_users,
                    temas_generales, temas_por_sentimiento_dict, search_terms):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
            ListFlowable, ListItem
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        import re
        import io
        from datetime import date

        buffer = BytesIO()

        # ---------- Estilos ----------
        styles = getSampleStyleSheet()

        # Títulos existentes, retocados
        styles['Title'].fontSize = 24
        styles['Title'].alignment = TA_CENTER
        styles['Title'].spaceAfter = 20
        styles['Title'].textColor = colors.HexColor('#1DA1F2')

        # Nuevos estilos
        if 'Body' not in styles:
            styles.add(ParagraphStyle(name='Body', fontSize=10, leading=14, spaceAfter=8))
        if 'H1' not in styles:
            styles.add(ParagraphStyle(name='H1', fontSize=18, leading=22, spaceAfter=10,
                                    textColor=colors.HexColor("#FF9100")))
        if 'H2' not in styles:
            styles.add(ParagraphStyle(name='H2', fontSize=14, leading=18, spaceAfter=8,
                                    textColor=colors.HexColor("#1DA1F2")))
        if 'Small' not in styles:
            styles.add(ParagraphStyle(name='Small', fontSize=9, leading=12,
                                    textColor=colors.HexColor("#555555")))

        # Helper: convierte Markdown ligero a mini-HTML para ReportLab
        def md_to_html(s: str) -> str:
            s = s or ""
            s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)  # **bold**
            s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)      # *italic*
            s = s.replace("\n", "<br/>")                   # saltos de línea
            return s

        def P(text, style_name='Body'):
            return Paragraph(md_to_html(text), styles[style_name])

        # ---------- Cabecera / pie ----------
        title_text = "Informe de Análisis de Sentimiento de Tweets"
        subtitle_text = "Análisis para los términos: " + ', '.join(search_terms)

        def my_page(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#F2D21D"))
            canvas.rect(0, A4[1] - 30, A4[0], 20, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(30, A4[1] - 25, title_text)
            canvas.setFillColor(colors.black)
            canvas.setFont('Helvetica', 9)
            canvas.drawCentredString(A4[0] / 2.0, 30, f'Página {doc.page}')
            canvas.drawRightString(A4[0] - 30, 30, f'Generado el: {date.today().strftime("%Y-%m-%d")}')
            canvas.restoreState()

        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
        doc.title = title_text
        elements = []

        # ---------- Portada / resumen ----------
        elements.append(Paragraph(title_text, styles['Title']))
        elements.append(Paragraph(subtitle_text, styles['H2']))
        elements.append(Spacer(1, 0.5 * inch))

        total_tweets = len(df)
        total_views = int(df['viewCount'].sum()) if 'viewCount' in df.columns else 0
        elements.append(P(f"<b>Términos de búsqueda:</b> {', '.join(search_terms)}"))
        elements.append(P(f"<b>Total de tweets encontrados:</b> {total_tweets:,}"))
        elements.append(P(f"<b>Total de visualizaciones:</b> {total_views:,}"))
        elements.append(Spacer(1, 0.5 * inch)) 

        
    # ---------- Evolución temporal ----------
        elements.append(Paragraph("Evolución de Tweets en el Tiempo", styles['H1']))
        
        # Recrea el gráfico de línea de tiempo con la configuración correcta
        if 'createdAt' in df.columns and not df.empty:
            try:
                # Recrea la lógica para el eje X
                df_copy = df.copy()
                df_copy['createdAt'] = pd.to_datetime(df_copy['createdAt'], errors='coerce')
                df_copy = df_copy.dropna(subset=['createdAt'])
                
                min_date = df_copy['createdAt'].min().date()
                max_date = df_copy['createdAt'].max().date()
                date_range_days = (max_date - min_date).days
                
                if date_range_days <= 3:
                    df_copy['time_bucket'] = df_copy['createdAt'].dt.strftime('%Y-%m-%d %H:00')
                    xaxis_label = 'Hora'
                elif date_range_days <= 150:
                    df_copy['time_bucket'] = df_copy['createdAt'].dt.date
                    xaxis_label = 'Fecha'
                else:
                    df_copy['time_bucket'] = df_copy['createdAt'].dt.to_period('M').astype(str)
                    xaxis_label = 'Mes'
                    
                tweet_count_timeline = df_copy.groupby('time_bucket').size().reset_index(name='Cantidad de Tweets')
                
                # Crea la figura de Plotly con la configuración completa de una sola vez
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

                fig_timeline_bytes = fig_timeline.to_image(format="png", scale=2)
                img_timeline = Image(io.BytesIO(fig_timeline_bytes), width=600, height=350)
                img_timeline.hAlign = 'CENTER'
                elements.append(img_timeline)
                
            except Exception as e:
                st.error(f"Error al generar el gráfico para el PDF: {e}")
                elements.append(P("No se pudo renderizar el gráfico de evolución temporal."))
        else:
            elements.append(P("No hay datos suficientes para mostrar la evolución temporal."))
        elements.append(PageBreak())

        # ---------- Temas generales (regex unificado + fallback formateado) ----------
        elements.append(Paragraph("Temas Clave del Conjunto Total de Tweets", styles['H1']))

        # MISMO patrón que en la UI (mostrar_temas_con_contraste)
        pattern_temas = r"(\d+)\.\s*([^\n]+)\n(.*?)\nEjemplo:\s*\"([^\"]+)\",\s*\[author/userName:\s*([^\]]+)\]"
        matches = []
        if isinstance(temas_generales, str):
            matches = re.findall(pattern_temas, temas_generales, re.DOTALL | re.MULTILINE)

        if matches:
            items = []
            for _, tema, explicacion, ejemplo, usuario in matches:
                titulo = Paragraph(f"<b>{md_to_html(tema.strip())}</b>", styles['Body'])
                desc = P(explicacion.strip(), 'Body')
                eje = Paragraph(f"<i>Ejemplo:</i> “{md_to_html(ejemplo.strip())}”, "
                                f"<font color='#555555'>@{md_to_html(usuario.strip())}</font>", styles['Small'])
                items.append(ListItem([titulo, desc, eje], leftIndent=10))
            elements.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=10))
        else:
            elements.append(P("No se pudo extraer el formato de temas esperado. Mostrando texto formateado automáticamente.", 'Small'))
            elements.append(P(temas_generales or "No se pudieron extraer temas generales.", 'Body'))
        elements.append(PageBreak())

        # ---------- Distribución de sentimientos ----------
        elements.append(Paragraph("Distribución de Sentimientos", styles['H1']))

        # Gráfico de torta
        try:
            fig_pie_bytes = fig_pie.to_image(format="png")
            img_pie = Image(io.BytesIO(fig_pie_bytes), width=450, height=300)
            img_pie.hAlign = 'CENTER'
            elements.append(img_pie)
        except Exception:
            elements.append(P("No se pudo renderizar el gráfico de distribución de sentimientos."))

        elements.append(Spacer(1, 0.25 * inch))
        elements.append(Paragraph("Resumen de Sentimientos", styles['H2']))

        data_summary = [["Sentimiento", "Porcentaje"]]
        total_tweets_counts = int(counts['Cantidad'].sum()) if not counts.empty else 0
        if total_tweets_counts > 0:
            for _, row in counts.iterrows():
                porcentaje = f"{row['Cantidad'] / total_tweets_counts * 100:.2f}%"
                data_summary.append([str(row['Sentimiento']), porcentaje])
        else:
            data_summary.append(["-", "0.00%"])

        table_summary = Table(data_summary, colWidths=[2*inch, 2*inch])
        table_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1DA1F2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table_summary)
        elements.append(PageBreak())

        # ---------- Temas por sentimiento ----------
        elements.append(Paragraph("Temas Principales por Sentimiento", styles['H1']))
        for sentimiento, texto_temas in (temas_por_sentimiento_dict or {}).items():
            elements.append(Paragraph(f"Temas {sentimiento}", styles['H2']))
            if texto_temas:
                matches_s = re.findall(pattern_temas, texto_temas, re.DOTALL | re.MULTILINE)
                if matches_s:
                    items = []
                    for _, tema, explicacion, ejemplo, usuario in matches_s:
                        titulo = Paragraph(f"<b>{md_to_html(tema.strip())}</b>", styles['Body'])
                        desc = P(explicacion.strip(), 'Body')
                        eje = Paragraph(f"<i>Ejemplo:</i> “{md_to_html(ejemplo.strip())}”, "
                                        f"<font color='#555555'>@{md_to_html(usuario.strip())}</font>", styles['Small'])
                        items.append(ListItem([titulo, desc, eje], leftIndent=10))
                    elements.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=10))
                else:
                    # Fallback formateado si no matchea
                    elements.append(P(texto_temas, 'Body'))
            else:
                elements.append(P(f"No hay tweets clasificados como {sentimiento} para analizar temas.", 'Body'))
            elements.append(Spacer(1, 8))
        elements.append(PageBreak())

        # ---------- Top 10 tweets ----------
        elements.append(Paragraph("Top 10 Tweets Más Vistos", styles['H1']))
        if top_10_views is not None and not top_10_views.empty:
            data_top_tweets = [['Foto', 'Usuario', 'Vistas', 'Tweet']]
            for _, row in top_10_views.head(10).iterrows():
                user = f"@{row.get('author/userName','')}"
                views = f"{int(row.get('viewCount', 0)):,}"
                
                # Convierte el texto del tweet en un objeto Paragraph para que se ajuste automáticamente
                text = Paragraph(str(row.get('text', '')), styles['Body'])
                
                image_url = row.get('author/profilePicture', '')
                if image_url:
                    try:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            img_buffer = BytesIO(response.content)
                            img = Image(img_buffer, width=0.5*inch, height=0.5*inch)
                        else:
                            img = Paragraph("❌", styles['Body'])
                    except Exception:
                        img = Paragraph("❌", styles['Body'])
                else:
                    img = Paragraph("❌", styles['Body'])
                    
                data_top_tweets.append([img, user, views, text])

            # Se ajusta el ancho de las columnas (la columna de Tweet es la más grande)
            table_top_tweets = Table(data_top_tweets, colWidths=[0.6*inch, 1.2*inch, 1.2*inch, 2.8*inch])
            table_top_tweets.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1DA1F2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'), # Alinea el contenido de la celda en la parte superior
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            elements.append(table_top_tweets)
        else:
            elements.append(P("No hay datos de visualizaciones disponibles para mostrar el top 10.", 'Body'))
        elements.append(PageBreak())

        # ---------- Top 10 usuarios ----------
        elements.append(Paragraph("Top 10 Usuarios con Más Seguidores", styles['H1']))
        if top_10_users is not None and not top_10_users.empty:
            # 1. Añade 'Foto' a los encabezados de la tabla
            data_top_users = [['Foto', 'Usuario', 'Seguidores']]
            for _, row in top_10_users.iterrows():
                user = f"@{row.get('author/userName','')}"
                followers = f"{int(row.get('author/followers', 0)):,}"
                
                # 2. Prepara la imagen
                image_url = row.get('author/profilePicture', '')
                if image_url:
                    try:
                        # Descarga la imagen y la almacena en un buffer
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            img_buffer = BytesIO(response.content)
                            img = Image(img_buffer, width=0.5*inch, height=0.5*inch)
                        else:
                            img = Paragraph("❌", styles['Body'])
                    except Exception:
                        img = Paragraph("❌", styles['Body'])
                else:
                    img = Paragraph("❌", styles['Body'])
                    
                # 3. Agrega la imagen como el primer elemento de la fila
                data_top_users.append([img, user, followers])

            # 4. Ajusta el ancho de las columnas para la nueva columna 'Foto'
            table_top_users = Table(data_top_users, colWidths=[0.6*inch, 2.5*inch, 2.5*inch])
            table_top_users.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1DA1F2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # Alinea el contenido de la celda al centro
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            elements.append(table_top_users)
        else:
            elements.append(P("No hay datos de seguidores disponibles para mostrar el top 10 de usuarios.", 'Body'))
        elements.append(PageBreak())
        # ---------- Build ----------
        doc.build(elements, onFirstPage=my_page, onLaterPages=my_page)
        buffer.seek(0)
        return buffer    

    # --- Sidebar: Parámetros ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        search_terms_input = st.text_area(
            "Términos de búsqueda",
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

        st.markdown("---")
        if st.button("Cerrar Sesión", key="logout_sidebar"):
            logout()

    st.markdown("---")

    if st.button("🚀 Ejecutar Scraping y Análisis", use_container_width=True):
        if not apify_token:
            st.error("Por favor, ingresa tu token de Apify en `.streamlit/secrets.toml` para continuar.")
        else:
            if not gemini_api_key:
                st.error("Por favor, ingresa tu API Key de Gemini en `.streamlit/secrets.toml` para el análisis de sentimiento y temas.")
                st.stop()
            
            st.session_state["results"] = None

            terms = [s.strip() for s in re.split(r'[,\n]', search_terms_input) if s.strip()]
            if not terms:
                st.warning("Por favor, introduce al menos un término de búsqueda.")
                st.stop()

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            with st.spinner("Buscando tweets... esto puede tardar un momento."):
                df_top = get_twitter_data(terms, start_str, end_str, "Top")

            df = df_top.drop_duplicates(subset=["url"]).reset_index(drop=True)

            if df.empty:
                st.warning("😔 No se encontraron tweets con los términos y fechas seleccionados. Intenta con otros parámetros.")
                st.stop()

            st.success(f"✅ Se recolectaron {len(df)} tweets únicos.")
            st.subheader("Primeros tweets encontrados:")
            st.dataframe(df.head(10))

            st.subheader("🧠 Clasificando Sentimientos...")

            batch_size = 50
            tweets_to_classify = df['text'].astype(str).tolist()
            total_tweets = len(tweets_to_classify)

            sentimientos = []
            progress_bar = st.progress(0)

            for i in range(0, total_tweets, batch_size):
                batch = tweets_to_classify[i:i + batch_size]
                sentimientos_batch = clasificar_tweets_en_lote(batch, contexto, model)
                sentimientos.extend(sentimientos_batch)
                progress_bar.progress(min((i + len(batch)) / total_tweets, 1.0))

            df["sentimiento"] = sentimientos
            st.success("✅ Clasificación de sentimientos completada.")
            progress_bar.empty()

            st.markdown("---")
            st.subheader("💡 Temas Clave del Conjunto Total de Tweets")
            all_tweets_text = df['text'].astype(str).tolist()
            temas_generales = "No hay tweets suficientes para extraer temas clave generales."
            if all_tweets_text:
                with st.spinner("Extrayendo temas clave generales..."):
                    temas_generales = extraer_temas_generales_con_ia(all_tweets_text, contexto)
                mostrar_temas_con_contraste(temas_generales)
            else:
                st.warning("No hay tweets para extraer temas clave generales.")

            st.markdown("---")
            st.subheader("🔥 Top 10 Tweets Más Vistos")
            df_sorted_by_views = df.dropna(subset=['viewCount']).sort_values(by='viewCount', ascending=False)
            top_10_views = pd.DataFrame()
            if not df_sorted_by_views.empty:
                top_10_views = df_sorted_by_views.head(10)
                top_10_views_display = top_10_views.copy()
                if 'viewCount' in top_10_views_display.columns:
                    top_10_views_display['viewCount'] = top_10_views_display['viewCount'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                st.dataframe(top_10_views_display, use_container_width=True, hide_index=True,
                            column_config={
                                "author/profilePicture": st.column_config.ImageColumn("Foto de Perfil"),
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

            st.markdown("---")
            st.subheader("👑 Top 10 Usuarios con Más Seguidores")
            df_users_sorted = df.dropna(subset=['author/followers', 'author/userName'])
            top_10_users = pd.DataFrame()
            if not df_users_sorted.empty:
                top_users = df_users_sorted.groupby('author/userName').agg(
                    **{'author/followers': pd.NamedAgg(column='author/followers', aggfunc='max'),
                       'author/profilePicture': pd.NamedAgg(column='author/profilePicture', aggfunc='first')}
                ).reset_index()
                top_10_users = top_users.sort_values(by='author/followers', ascending=False).head(10)
                top_users_display = top_10_users.copy()
                top_users_display['author/followers'] = top_users_display['author/followers'].apply(lambda x: f"{int(x):,}")
                st.dataframe(top_users_display, use_container_width=True, hide_index=True,
                            column_config={
                                "author/profilePicture": st.column_config.ImageColumn("Foto de Perfil"),
                                "author/userName": st.column_config.TextColumn("Usuario"),
                                "author/followers": st.column_config.NumberColumn("Seguidores", format="%d")
                            })
            else:
                st.info("No hay datos de seguidores disponibles para mostrar el top 10 de usuarios.")

            st.subheader("📊 Distribución de Sentimientos")
            counts = df['sentimiento'].value_counts().reset_index()
            counts.columns = ['Sentimiento', 'Cantidad']
            counts['Porcentaje'] = counts['Cantidad'] / counts['Cantidad'].sum() * 100
            
            st.markdown("### Resumen Rápido")
            summary_df = counts[['Sentimiento', 'Porcentaje']].copy()
            summary_df['Porcentaje'] = summary_df['Porcentaje'].round(2).astype(str) + '%'
            st.dataframe(summary_df, hide_index=True, use_container_width=True)

            fig_pie = px.pie(
                counts,
                values='Cantidad',
                names='Sentimiento',
                title='Distribución de Sentimientos de los Tweets',
                hover_data=['Porcentaje'],
                labels={'Porcentaje': 'Porcentaje (%)'},
                color='Sentimiento',
                color_discrete_map={
                    'POSITIVO': '#4CAF50',
                    'NEGATIVO': '#F44336',
                    'NEUTRO': '#9E9E9E'
                }
            )

            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
            fig_pie.update_layout(
                margin=dict(t=40, b=0, l=0, r=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="right", x=1)
            )
            st.plotly_chart(fig_pie, use_container_width=True)


            st.subheader("🔍 Temas Principales por Sentimiento")
            temas_por_sentimiento_dict = {}

            for tipo in ["POSITIVO", "NEGATIVO", "NEUTRO"]:
                subset = df[df["sentimiento"] == tipo]["text"].astype(str).tolist()
                if subset:
                    with st.expander(f"Mostrar temas **{tipo}** ({len(subset)} tweets)"):
                        with st.spinner(f"Extrayendo temas {tipo}..."):
                            resumen = extraer_temas_con_ia(subset, tipo, contexto)
                            temas_por_sentimiento_dict[tipo] = resumen
                        st.markdown(resumen.replace("---", "---\n"))
                else:
                    st.info(f"No hay tweets clasificados como **{tipo}** para analizar temas.")

            fig_timeline = None
            if 'createdAt' in df.columns:
                df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
                df = df.dropna(subset=['createdAt'])

                min_date = df['createdAt'].min().date()
                max_date = df['createdAt'].max().date()
                date_range_days = (max_date - min_date).days

                if date_range_days <= 3:
                    df['time_bucket'] = df['createdAt'].dt.strftime('%Y-%m-%d %H:00')
                    xaxis_label = 'Hora'
                elif date_range_days <= 150:
                    df['time_bucket'] = df['createdAt'].dt.date
                    xaxis_label = 'Fecha'
                else:
                    df['time_bucket'] = df['createdAt'].dt.to_period('M').astype(str)
                    xaxis_label = 'Mes'

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
                # Agrega explícitamente la configuración de los ejes X e Y
                fig_timeline.update_layout(
                    xaxis_title=xaxis_label,
                    yaxis_title='Número de Tweets',
                    margin=dict(t=40, b=0, l=0, r=0),
                    yaxis_range=[0, None]
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

                # Guarda el gráfico en el estado de la sesión
                st.session_state["results"] = {
                    "df": df,
                    "counts": counts,
                    "fig_pie": fig_pie,
                    "fig_timeline": fig_timeline, # Este es el objeto que se usa para generar el PDF
                    "top_10_views": top_10_views,
                    "top_10_users": top_10_users,
                    "temas_generales": temas_generales,
                    "temas_por_sentimiento_dict": temas_por_sentimiento_dict,
                    "search_terms": terms
                }

            
            st.success("✅ Análisis completado. Puedes ver los resultados y descargarlos a continuación.")

    if st.session_state["results"] is not None:
        st.markdown("---")
        st.subheader("⬇️ Descargar Resultados")
        
        results = st.session_state["results"]

        st.download_button(
            label="Descargar resultados completos (CSV)",
            data=results["df"].to_csv(index=False).encode('utf-8'),
            file_name="tweets_analizados.csv",
            mime="text/csv",
            help="Descarga un archivo CSV con todos los tweets recolectados y su clasificación de sentimiento."
        )
        
        pdf_buffer = generar_pdf(
            results["df"],
            results["counts"],
            results["fig_pie"],
            results["fig_timeline"],
            results["top_10_views"],
            results["top_10_users"],
            results["temas_generales"],
            results["temas_por_sentimiento_dict"],
            results["search_terms"]
        )

        st.download_button(
            label="Descargar Informe (PDF)",
            data=pdf_buffer,
            file_name="informe_analisis_tweets.pdf",
            mime="application/pdf",
            help="Descarga un informe completo en formato PDF con todos los gráficos y análisis."
        )

    st.markdown("---")
    st.info("✨ Aplicación creada con Streamlit, Apify y Google Gemini.")


if st.session_state["logged_in"]:
    main_app()
else:

    login_page()
