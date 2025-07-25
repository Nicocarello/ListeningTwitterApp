# 🐦 Aplicación de Scraping y Análisis de Sentimiento de Tweets

## Descripción General

Esta aplicación web interactiva, construida con **Streamlit**, permite a los usuarios extraer tweets basados en términos de búsqueda y rangos de fechas específicos, y luego realizar un análisis de sentimiento sobre el contenido recolectado utilizando la inteligencia artificial de **Google Gemini**. Además, identifica temas clave dentro de los tweets y muestra métricas importantes como los tweets más vistos y los usuarios con más seguidores.

Es una herramienta ideal para el monitoreo de marca, análisis de campañas, investigación de mercado o simplemente para entender la percepción pública sobre temas específicos en Twitter (X).

---

## 🧩 Características Principales

- **Scraping de Tweets**: Extrae tweets utilizando la API de **Apify**, permitiendo búsquedas por términos y rangos de fechas.
- **Análisis de Sentimiento**: Clasifica cada tweet como **POSITIVO**, **NEGATIVO** o **NEUTRO** utilizando el modelo `gemini-2.0-flash` de Google Gemini.
- **Extracción de Temas Clave**: Identifica los temas más relevantes en el conjunto total de tweets, así como temas específicos para tweets positivos, negativos y neutros.

### Visualización de Datos:
- Distribución de sentimientos en un **gráfico de torta interactivo**.
- Evolución temporal de la **cantidad de tweets**.
- **Tabla** de los 10 tweets más vistos.
- **Tabla** de los 10 usuarios con más seguidores.

- **Descarga de Resultados**: Permite descargar un archivo CSV con todos los tweets recolectados y su clasificación de sentimiento.
- **Interfaz Intuitiva**: Desarrollada con Streamlit para una experiencia de usuario sencilla y amigable.

---

## 🚀 Cómo Usar la Aplicación

1. **Acceder a la Aplicación**  
   Abre la URL de la aplicación desplegada en tu navegador web.

2. **Configuración en la Barra Lateral (Sidebar)**:
   - **Términos de búsqueda**: Introduce las palabras clave o frases que deseas buscar en Twitter. Puedes introducir múltiples términos, uno por línea o separados por comas.
   - **Fecha de inicio y Fecha de fin**: Selecciona el rango de fechas para la recolección de tweets.
   - **Contexto para el análisis de sentimiento (opcional)**: Proporciona un contexto adicional a la IA para mejorar la precisión del análisis de sentimiento y la extracción de temas.  
     Ejemplo: `"Opiniones de clientes sobre un nuevo producto financiero."`

3. **Ejecutar el Análisis**  
   Haz clic en el botón **"🚀 Ejecutar Scraping y Análisis"**.

4. **Visualizar Resultados**  
   La aplicación mostrará progresivamente los resultados:
   - Un resumen de los tweets recolectados.
   - La distribución de sentimientos.
   - Los temas clave generales y por sentimiento.
   - Los tweets más vistos y los usuarios con más seguidores.
   - La evolución temporal de los tweets.

---

## 🛠 Tecnologías Utilizadas

- **Python**: Lenguaje de programación principal.
- **Streamlit**: Framework para la creación de aplicaciones web interactivas de ciencia de datos.
- **Apify Client**: Para interactuar con la API de Apify y realizar el scraping de tweets.
- **Google Generative AI (Gemini)**: Para el análisis de sentimiento y la extracción de temas clave.
- **Pandas**: Para la manipulación y análisis de datos.
- **Plotly Express**: Para la creación de gráficos interactivos.

---

## ⚠️ Notas Importantes

- **Límites de API**: La recolección de tweets y el análisis de IA están sujetos a los límites de uso de las APIs de Apify y Google Gemini. Un uso muy intensivo podría requerir una cuenta de pago en esas plataformas.
- **Precisión del Sentimiento**: La clasificación de sentimiento es realizada por un modelo de IA y, aunque es potente, puede no ser 100% precisa en todos los contextos. Proporcionar un buen **"Contexto para el análisis de sentimiento"** puede mejorar la precisión.

---

📬 ¿Tienes sugerencias o encontraste algún error? ¡No dudes en abrir un issue o un pull request!
