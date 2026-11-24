"""
Herramientas (tools) del Asistente Académico de Entregas.

Cada función es una herramienta que el agente puede invocar. El docstring de
cada una es lo que el modelo lee para decidir cuándo usarla y con qué
argumentos, por eso están escritos con detalle.

Todas las herramientas devuelven un diccionario con la clave "status":
  - "ok":     la operación salió bien.
  - "vacio":  la operación salió bien pero no hay resultados.
  - "error":  hubo un problema (argumento inválido, dato inexistente, falla
              externa). En "mensaje" se explica qué pasó.
Así el agente nunca recibe una excepción sin manejar y siempre puede explicar
al usuario qué ocurrió.
"""

import json
from datetime import date, datetime
from pathlib import Path

# Archivo donde se guardan las entregas (se crea automáticamente)
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "entregas.json"

FORMATO_FECHA = "%Y-%m-%d"
ESTADOS_VALIDOS = ("pendiente", "entregada", "todas")
NOTA_MINIMA, NOTA_MAXIMA = 1.0, 10.0


# ---------------------------------------------------------------------------
# Funciones auxiliares (no son herramientas del agente)
# ---------------------------------------------------------------------------

def _error(mensaje: str) -> dict:
    return {"status": "error", "mensaje": mensaje}


CAMPOS_ENTREGA = ("id", "materia", "titulo", "fecha_entrega", "estado")


def _entrega_valida(e) -> bool:
    """Descarta registros incompletos o con datos inválidos (por ejemplo, editados a mano)."""
    return (
        isinstance(e, dict)
        and all(c in e for c in CAMPOS_ENTREGA)
        and isinstance(e["id"], int) and not isinstance(e["id"], bool)
        and isinstance(e["materia"], str) and isinstance(e["titulo"], str)
        and _parsear_fecha(e["fecha_entrega"]) is not None
        and e["estado"] in ("pendiente", "entregada")
    )


def _cargar_entregas() -> list[dict]:
    """Lee el archivo JSON. Si no existe o está dañado, devuelve una lista vacía.
    Los registros inválidos se ignoran para que ninguna herramienta falle."""
    if not DATA_FILE.exists():
        return []
    try:
        datos = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    if not isinstance(datos, list):
        return []
    return [e for e in datos if _entrega_valida(e)]


def _guardar_entregas(entregas: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(entregas, ensure_ascii=False, indent=2), encoding="utf-8")


def _parsear_fecha(texto: str) -> date | None:
    try:
        return datetime.strptime(texto.strip(), FORMATO_FECHA).date()
    except (ValueError, AttributeError):
        return None


def _urgencia(dias: int) -> str:
    if dias < 0:
        return "vencida"
    if dias == 0:
        return "vence hoy"
    if dias <= 3:
        return "urgente"
    if dias <= 7:
        return "esta semana"
    return "con tiempo"


# ---------------------------------------------------------------------------
# Herramienta 1: fecha actual
# ---------------------------------------------------------------------------

def obtener_fecha_actual() -> dict:
    """
    Devuelve la fecha de hoy y el día de la semana.

    Usar SIEMPRE antes de interpretar fechas relativas que diga el usuario
    (por ejemplo "mañana", "el viernes", "en dos semanas") para convertirlas
    al formato AAAA-MM-DD que piden las otras herramientas.

    Returns:
        dict con "fecha" (AAAA-MM-DD) y "dia_semana".
    """
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    hoy = date.today()
    return {"status": "ok", "fecha": hoy.strftime(FORMATO_FECHA), "dia_semana": dias[hoy.weekday()]}


# ---------------------------------------------------------------------------
# Herramienta 2: registrar una entrega
# ---------------------------------------------------------------------------

def registrar_entrega(materia: str, titulo: str, fecha_entrega: str, descripcion: str = "") -> dict:
    """
    Registra un nuevo trabajo práctico, examen o entrega en la agenda del estudiante.

    Usar cuando el usuario pida anotar, agendar, guardar o recordar una entrega.

    Args:
        materia: Nombre de la materia (por ejemplo "Redes Neuronales").
        titulo: Nombre del trabajo o evaluación (por ejemplo "TP N°1").
        fecha_entrega: Fecha límite en formato AAAA-MM-DD (por ejemplo "2026-12-05").
        descripcion: Detalle opcional de la consigna.

    Returns:
        dict con la entrega creada (incluye su "id") o un mensaje de error.
    """
    materia = (materia or "").strip()
    titulo = (titulo or "").strip()
    if not materia:
        return _error("Falta el nombre de la materia.")
    if not titulo:
        return _error("Falta el título de la entrega.")

    fecha = _parsear_fecha(fecha_entrega)
    if fecha is None:
        return _error(f"La fecha '{fecha_entrega}' no es válida. Debe tener el formato AAAA-MM-DD.")

    entregas = _cargar_entregas()
    duplicada = next(
        (e for e in entregas
         if e["materia"].lower() == materia.lower() and e["titulo"].lower() == titulo.lower()),
        None,
    )
    if duplicada:
        return _error(f"Ya existe '{titulo}' de {materia} (id {duplicada['id']}, "
                      f"fecha {duplicada['fecha_entrega']}).")

    nueva = {
        "id": max((e["id"] for e in entregas), default=0) + 1,
        "materia": materia,
        "titulo": titulo,
        "fecha_entrega": fecha.strftime(FORMATO_FECHA),
        "descripcion": (descripcion or "").strip(),
        "estado": "pendiente",
    }
    entregas.append(nueva)
    _guardar_entregas(entregas)

    resultado = {"status": "ok", "entrega": nueva}
    if fecha < date.today():
        resultado["advertencia"] = "La fecha ingresada ya pasó: la entrega figura como vencida."
    return resultado


# ---------------------------------------------------------------------------
# Herramienta 3: listar entregas
# ---------------------------------------------------------------------------

def listar_entregas(materia: str = "", estado: str = "pendiente") -> dict:
    """
    Lista las entregas registradas, ordenadas por fecha, indicando cuántos días
    faltan y el nivel de urgencia (vencida, vence hoy, urgente, esta semana, con tiempo).

    Usar cuando el usuario pregunte qué tiene pendiente, qué vence pronto,
    qué tiene que entregar de una materia o cómo organizarse.

    Args:
        materia: Filtra por materia (búsqueda parcial, sin distinguir mayúsculas).
                 Dejar vacío para ver todas las materias.
        estado: "pendiente" (por defecto), "entregada" o "todas".

    Returns:
        dict con la lista "entregas" o status "vacio" si no hay resultados.
    """
    estado = (estado or "pendiente").strip().lower()
    if estado not in ESTADOS_VALIDOS:
        return _error(f"Estado '{estado}' inválido. Opciones: {', '.join(ESTADOS_VALIDOS)}.")

    entregas = _cargar_entregas()
    if not entregas:
        return {"status": "vacio", "mensaje": "Todavía no hay ninguna entrega registrada."}

    filtro_materia = (materia or "").strip().lower()
    hoy = date.today()
    resultado = []
    for e in entregas:
        if estado != "todas" and e["estado"] != estado:
            continue
        if filtro_materia and filtro_materia not in e["materia"].lower():
            continue
        dias = (_parsear_fecha(e["fecha_entrega"]) - hoy).days
        item = dict(e, dias_restantes=dias)
        if e["estado"] == "pendiente":
            item["urgencia"] = _urgencia(dias)
        resultado.append(item)

    if not resultado:
        detalle = f" de '{materia}'" if filtro_materia else ""
        return {"status": "vacio", "mensaje": f"No hay entregas en estado '{estado}'{detalle}."}

    resultado.sort(key=lambda e: e["fecha_entrega"])
    return {"status": "ok", "cantidad": len(resultado), "entregas": resultado}


# ---------------------------------------------------------------------------
# Herramienta 4: marcar como entregada
# ---------------------------------------------------------------------------

def marcar_entregada(id_entrega: int) -> dict:
    """
    Marca una entrega como ya entregada (completada).

    Usar cuando el usuario diga que ya entregó o terminó un trabajo. Si no se
    conoce el id, primero usar listar_entregas para encontrarlo.

    Args:
        id_entrega: Número identificador de la entrega (campo "id").

    Returns:
        dict con la entrega actualizada o un mensaje de error.
    """
    # bool es subclase de int en Python: True no debe tomarse como id 1.
    # Se aceptan 3, "3" y 3.0 (los modelos a veces mandan el número como float).
    try:
        if isinstance(id_entrega, bool) or float(id_entrega) != int(float(id_entrega)):
            raise ValueError
        id_entrega = int(float(id_entrega))
    except (TypeError, ValueError, OverflowError):
        return _error(f"El id '{id_entrega}' no es un número válido.")

    entregas = _cargar_entregas()
    entrega = next((e for e in entregas if e["id"] == id_entrega), None)
    if entrega is None:
        return _error(f"No existe ninguna entrega con id {id_entrega}.")
    if entrega["estado"] == "entregada":
        return _error(f"'{entrega['titulo']}' ya estaba marcada como entregada.")

    entrega["estado"] = "entregada"
    _guardar_entregas(entregas)
    return {"status": "ok", "entrega": entrega}


# ---------------------------------------------------------------------------
# Herramienta 5: calcular nota necesaria
# ---------------------------------------------------------------------------

def calcular_nota_necesaria(notas: list[float], evaluaciones_restantes: int = 1,
                            nota_aprobacion: float = 6.0) -> dict:
    """
    Calcula el promedio actual de un estudiante y qué nota necesita sacar en
    las evaluaciones que le faltan para llegar al promedio de aprobación.
    Escala de notas de 1 a 10.

    Usar cuando el usuario pregunte por su promedio, si le alcanza para
    aprobar o cuánto necesita sacarse en el próximo examen.

    Args:
        notas: Lista de notas ya obtenidas (por ejemplo [7, 5.5]).
        evaluaciones_restantes: Cantidad de evaluaciones que faltan rendir (0 o más).
        nota_aprobacion: Promedio mínimo para aprobar (por defecto 6).

    Returns:
        dict con promedio actual, nota necesaria por evaluación y si es posible aprobar.
    """
    if not isinstance(notas, list) or len(notas) == 0:
        return _error("Hay que indicar al menos una nota ya obtenida.")
    try:
        notas = [float(n) for n in notas]
        evaluaciones_restantes = int(evaluaciones_restantes)
        nota_aprobacion = float(nota_aprobacion)
    except (TypeError, ValueError):
        return _error("Las notas, la cantidad de evaluaciones y la nota de aprobación deben ser números.")

    fuera_de_rango = [n for n in notas + [nota_aprobacion] if not NOTA_MINIMA <= n <= NOTA_MAXIMA]
    if fuera_de_rango:
        return _error(f"Valores fuera de la escala 1 a 10: {fuera_de_rango}.")
    if evaluaciones_restantes < 0:
        return _error("La cantidad de evaluaciones restantes no puede ser negativa.")

    promedio = round(sum(notas) / len(notas), 2)
    resultado = {"status": "ok", "promedio_actual": promedio, "nota_aprobacion": nota_aprobacion}

    if evaluaciones_restantes == 0:
        resultado["aprobado"] = promedio >= nota_aprobacion
        return resultado

    total_evaluaciones = len(notas) + evaluaciones_restantes
    necesaria = (nota_aprobacion * total_evaluaciones - sum(notas)) / evaluaciones_restantes
    necesaria = round(max(necesaria, NOTA_MINIMA), 2)

    resultado["evaluaciones_restantes"] = evaluaciones_restantes
    resultado["nota_necesaria_por_evaluacion"] = necesaria
    resultado["es_posible_aprobar"] = necesaria <= NOTA_MAXIMA
    if necesaria > NOTA_MAXIMA:
        resultado["mensaje"] = ("Aun sacando 10 en lo que falta no se llega al promedio; "
                                "conviene consultar por un recuperatorio.")
    return resultado


# ---------------------------------------------------------------------------
# Herramienta 6: búsqueda en internet
# ---------------------------------------------------------------------------

def buscar_en_internet(consulta: str, max_resultados: int = 5) -> dict:
    """
    Busca información en internet con DuckDuckGo.

    Usar cuando el usuario necesite material de estudio, explicaciones,
    documentación o recursos sobre el tema de una entrega.
    No usar para consultar la agenda de entregas.

    Args:
        consulta: Texto a buscar.
        max_resultados: Cantidad de resultados, entre 1 y 10 (por defecto 5).

    Returns:
        dict con la lista "resultados" (título, enlace y resumen) o un error.
    """
    consulta = (consulta or "").strip()
    if len(consulta) < 3:
        return _error("La consulta está vacía o es demasiado corta.")
    try:
        max_resultados = int(max_resultados)
    except (TypeError, ValueError):
        return _error("max_resultados debe ser un número.")
    if not 1 <= max_resultados <= 10:
        return _error("max_resultados debe estar entre 1 y 10.")

    try:
        from ddgs import DDGS
        crudos = DDGS().text(query=consulta, max_results=max_resultados) or []
    except Exception as e:  # sin conexión, límite de consultas, etc.
        return _error(f"No se pudo realizar la búsqueda: {e}")

    resultados = [
        {"titulo": r.get("title", ""), "enlace": r.get("href", ""), "resumen": r.get("body", "")}
        for r in crudos
    ]
    if not resultados:
        return {"status": "vacio", "mensaje": f"No se encontraron resultados para '{consulta}'."}
    return {"status": "ok", "cantidad": len(resultados), "resultados": resultados}
