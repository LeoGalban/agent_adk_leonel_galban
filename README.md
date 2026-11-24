# Agendita: Asistente Académico de Entregas con Google ADK

Agente de inteligencia artificial desarrollado en Python con **Google Agent Development Kit (ADK)** que ayuda a estudiantes a organizar sus trabajos prácticos y exámenes.

> Trabajo práctico de **S.A.C. Modelos y Aplicaciones de la Inteligencia Artificial**
> Tecnicatura Superior en Desarrollo de Software Multiplataforma, Instituto Politécnico Formosa
> Alumno: **Leonel Galban Rojas**

---

## ¿Qué problema resuelve?

Durante la cursada es común tener varios trabajos prácticos de distintas materias, cada uno con su fecha de entrega, y perder de vista qué vence primero o cuánto hace falta sacarse en un parcial para aprobar.

**Agendita** es un agente que, a partir de mensajes en lenguaje natural:

- **anota** las entregas con su materia y fecha límite,
- **avisa** qué está vencido, qué vence hoy y qué es urgente,
- **marca** como entregados los trabajos terminados,
- **calcula** el promedio y la nota necesaria para aprobar,
- **busca** material de estudio en internet.

No es un chatbot que solo genera texto: el modelo **interpreta la solicitud, decide qué herramientas usar (y en qué orden), las ejecuta y arma la respuesta con los resultados reales**. Por ejemplo, ante *"anotame el TP de Redes para el viernes"*, primero consulta la fecha actual para saber qué día es "el viernes" y después registra la entrega.

---

## Herramientas

| Herramienta | Responsabilidad | Validaciones |
|---|---|---|
| `obtener_fecha_actual` | Devuelve la fecha y el día de la semana, para interpretar fechas relativas ("mañana", "el viernes"). | — |
| `registrar_entrega` | Guarda una nueva entrega (materia, título, fecha, descripción). | Campos vacíos, fecha con formato inválido, entregas duplicadas y aviso si la fecha ya pasó. |
| `listar_entregas` | Lista entregas ordenadas por fecha con días restantes y nivel de urgencia. Filtra por materia y estado. | Estado inválido; resultado vacío si no hay entregas o el filtro no encuentra nada. |
| `marcar_entregada` | Marca una entrega como completada. | Id no numérico, id inexistente, entrega ya marcada. |
| `calcular_nota_necesaria` | Calcula el promedio actual y la nota necesaria en las evaluaciones que faltan. | Lista vacía, valores no numéricos, notas fuera de la escala 1 a 10, cantidad negativa y caso en el que no se puede aprobar. |
| `buscar_en_internet` | Busca material de estudio con DuckDuckGo. | Consulta vacía, cantidad de resultados fuera de rango, falla de conexión y búsqueda sin resultados. |

Todas las herramientas devuelven un diccionario con un campo `status`:

- `"ok"`: la operación salió bien.
- `"vacio"`: no hubo resultados (por ejemplo, ninguna entrega pendiente).
- `"error"`: argumento inválido o falla externa, con un `"mensaje"` que explica el problema.

Así el agente **nunca recibe una excepción sin manejar** y en sus instrucciones se le indica cómo responder en cada caso (pedir el dato corregido, sugerir alternativas, no inventar información).

Las entregas se guardan en `asistente_academico/data/entregas.json`, que se crea automáticamente.

---

## Instrucciones del agente

Las instrucciones (en [`agent.py`](asistente_academico/agent.py)) están divididas en:

- **Rol:** asistente académico para estudiantes de nivel superior, en español rioplatense.
- **Objetivo:** organizar entregas, avisar vencimientos, calcular notas y buscar material.
- **Herramientas y cuándo usarlas:** una guía de qué herramienta corresponde a cada tipo de pedido.
- **Restricciones:** no inventar datos, no calcular notas "de cabeza", pedir los datos que falten, no resolver los TPs por el estudiante y no salirse del tema académico.
- **Comportamiento ante resultados:** qué hacer con `ok`, `vacio`, `error` y advertencias.

---

## Modelo

Se usa **LiteLLM** para conectar ADK con modelos de **Ollama**, como se trabajó en clase. Por defecto usa `ollama_chat/qwen3:8b`, un modelo local, gratuito y con soporte de *tool calling*. Se puede cambiar desde el archivo `.env` (ver más abajo) sin tocar el código, por ejemplo para usar un modelo de la nube de Ollama.

---

## Estructura del proyecto

```
agent_adk_leonel_galban/
├── asistente_academico/
│   ├── __init__.py
│   ├── agent.py          # Definición del agente (modelo, instrucciones, herramientas)
│   ├── tools.py          # Las seis herramientas con sus validaciones
│   └── .env.example      # Configuración de ejemplo (modelo y Ollama)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Instalación y uso

### Requisitos

- Python 3.10 o superior
- [uv](https://docs.astral.sh/uv/) (o `pip`)
- [Ollama](https://ollama.com/) instalado y corriendo

### 1. Clonar el repositorio

```bash
git clone https://github.com/LeoGalban/agent_adk_leonel_galban.git
cd agent_adk_leonel_galban
```

### 2. Crear el entorno virtual e instalar dependencias

```bash
# Windows
uv venv env && env\Scripts\activate
# Linux / macOS
uv venv env && source env/bin/activate

uv pip install -r requirements.txt
```

### 3. Configurar el modelo

Copiar el archivo de ejemplo:

```bash
# Windows
copy asistente_academico\.env.example asistente_academico\.env
# Linux / macOS
cp asistente_academico/.env.example asistente_academico/.env
```

Descargar el modelo (unos 5 GB) y verificar que esté disponible:

```bash
ollama pull qwen3:8b
ollama ls
```

- Para usar otro modelo se cambia `MODELO_AGENTE` en el `.env`. Conviene uno que soporte *tool calling*.
- Los modelos de la nube de Ollama (por ejemplo `gemma4:31b-cloud`) requieren iniciar sesión con `ollama signin` y pueden requerir créditos en la cuenta.

### 4. Ejecutar la interfaz web de ADK

Desde la carpeta raíz del proyecto:

```bash
adk web
```

Abrir http://localhost:8000 en el navegador y elegir **asistente_academico** en el menú desplegable.

También se puede probar desde la terminal con:

```bash
adk run asistente_academico
```

---

## Ejemplos de uso

Estos mensajes muestran cómo el agente elige distintas herramientas según el pedido. En la interfaz web de ADK se puede ver cada llamada a herramienta con sus argumentos y su resultado.

| Mensaje del usuario | Herramientas que usa el agente |
|---|---|
| "Anotame el TP de Agentes de Modelos de IA para el viernes" | `obtener_fecha_actual` → `registrar_entrega` |
| "Agendá el parcial de Estadística para el 2026-12-10" | `registrar_entrega` |
| "¿Qué tengo pendiente?" | `listar_entregas` |
| "¿Qué me queda de Estadística?" | `listar_entregas` (con filtro de materia) |
| "Ya entregué el TP de Agentes" | `listar_entregas` → `marcar_entregada` |
| "Me saqué 7 y 4,5 en los parciales, ¿cuánto necesito en el final para tener 6?" | `calcular_nota_necesaria` |
| "Buscame material sobre redes neuronales convolucionales" | `buscar_en_internet` |
| "Anotame el TP para el 31/02" | `registrar_entrega` devuelve error y el agente pide una fecha válida |
| "Marcá como entregada la 99" | `marcar_entregada` devuelve error: no existe |
| "¿Qué tengo de Física?" (sin entregas cargadas) | `listar_entregas` devuelve resultado vacío y el agente lo informa |
| "Me saqué 2 y 3, ¿llego al 6 con un examen más?" | `calcular_nota_necesaria` devuelve que no es posible aprobar |
