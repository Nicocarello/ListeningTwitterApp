# 🐦 Twitter Sentiment Analysis Dashboard

Una aplicación web interactiva construida con Streamlit para scrapear tweets, analizar su sentimiento con IA y visualizar los resultados en un dashboard dinámico. Esta herramienta está diseñada para el análisis de opiniones y tendencias en redes sociales.

## 📋 Índice

  - [✨ Características Principales](https://www.google.com/search?q=%23-caracter%C3%ADsticas-principales)
  - [🛠️ Stack Tecnológico](https://www.google.com/search?q=%23%EF%B8%8F-stack-tecnol%C3%B3gico)
  - [🚀 Cómo Ejecutar la Aplicación](https://www.google.com/search?q=%23-c%C3%B3mo-ejecutar-la-aplicaci%C3%B3n)
  - [👨‍💻 Cómo Usar la Aplicación](https://www.google.com/search?q=%23-c%C3%B3mo-usar-la-aplicaci%C3%B3n)
  - [📂 Estructura del Código](https://www.google.com/search?q=%23-estructura-del-c%C3%B3digo)

## ✨ Características Principales

  - **🔐 Sistema de Login:** Acceso restringido a usuarios con un correo electrónico de un dominio específico.
  - **📊 Dashboard Interactivo:** Visualiza datos a través de gráficos de torta (distribución de sentimiento) y gráficos de línea (evolución de tweets).
  - **🔎 Scraping Personalizado:** Extrae tweets de X (Twitter) utilizando términos de búsqueda y rangos de fechas específicos a través de la API de Apify.
  - **🧠 Análisis de Sentimiento con IA:** Clasifica automáticamente cada tweet como `POSITIVO`, `NEGATIVO` o `NEUTRO` utilizando la potencia de Google Gemini.
  - **💡 Extracción de Temas Clave:** La IA identifica y resume los principales temas de conversación, tanto a nivel general como por cada categoría de sentimiento.
  - **💬 Chatbot de Datos:** Permite a los usuarios hacer preguntas en lenguaje natural sobre el conjunto de datos recolectado para obtener insights rápidos.
  - **🏆 Rankings y Top 10:** Muestra tablas con los tweets más vistos y los usuarios con más seguidores.
  - **⬇️ Exportación de Datos:** Descarga todos los datos analizados en un archivo `.csv` para análisis externos.

## 🛠️ Stack Tecnológico

  - **Framework:** [Streamlit](https://streamlit.io/)
  - **Análisis de Datos:** [Pandas](https://pandas.pydata.org/)
  - **Visualización de Datos:** [Plotly Express](https://plotly.com/python/plotly-express/)
  - **Scraping de Datos:** [Apify API](https://apify.com/) (`apify-client`)
  - **Inteligencia Artificial:** [Google Gemini API](https://ai.google.dev/) (`google-generativeai`)
  - **Manejo de Concurrencia:** `concurrent.futures.ThreadPoolExecutor`

## 📂 Estructura del Código

El archivo `app.py` está organizado de la siguiente manera:

  - **Configuración Inicial:** `st.set_page_config` y declaración de constantes.
  - **Estado de Sesión y CSS:** Manejo del estado de login y estilos visuales personalizados.
  - **Funciones de Autenticación:** `login_page()` y `logout()`.
  - **Función Principal `main_app()`:** Contiene toda la lógica y la interfaz de la aplicación principal.
      - **`get_twitter_data()`:** Función cacheada que interactúa con la API de Apify para obtener los tweets.
      - **`clasificar_tweet()`:** Envía un tweet a la API de Gemini para su clasificación.
      - **`extraer_temas_..._con_ia()`:** Funciones que usan Gemini para identificar temas.
      - **`chatear_con_dataframe()`:** Lógica del chatbot para interactuar con los datos.
  - **Lógica de Ejecución:** El bloque final que decide si mostrar la página de login o la aplicación principal según el estado de la sesión.
