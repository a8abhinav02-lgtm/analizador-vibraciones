import streamlit as st
import re


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def convertir_numero(valor):
    """
    Convierte formatos como:
    .319 -> 0.319
    -.015 -> -0.015
    """

    valor = valor.strip()

    if valor.startswith("-."):
        valor = valor.replace("-.", "-0.")

    elif valor.startswith("."):
        valor = "0" + valor

    return float(valor)


# ==========================================
# EXTRACCION DE DATOS
# ==========================================

def extraer_datos(texto):

    datos = {}

    # RPM

    rpm = re.search(r"RPM=\s*([\d\.]+)", texto)

    if rpm:
        try:
            datos["rpm"] = float(rpm.group(1))
        except:
            pass

    # MAX PEAK Y CREST FACTOR

    patron_peak = re.search(
        r"Max Peak.*?\n\s*([-\.\d]+)\s+([-\.\d]+)\s+([-\.\d]+)\s+([-\.\d]+)",
        texto,
        re.DOTALL
    )

    if patron_peak:

        try:

            datos["max_peak_neg"] = convertir_numero(
                patron_peak.group(1)
            )

            datos["max_peak_pos"] = convertir_numero(
                patron_peak.group(2)
            )

            datos["crest_neg"] = convertir_numero(
                patron_peak.group(3)
            )

            datos["crest_pos"] = convertir_numero(
                patron_peak.group(4)
            )

        except:
            pass

    # BUSCAR KURTOSIS Y SKEWNESS
    # MÁS ROBUSTO QUE REGEX

    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):

        if "Kurtosis" in linea and "Skewness" in linea:

            try:

                valores_linea = lineas[i + 2]

                valores = valores_linea.split()

                if len(valores) >= 2:

                    datos["kurtosis"] = convertir_numero(
                        valores[0]
                    )

                    datos["skewness"] = convertir_numero(
                        valores[1]
                    )

            except:
                pass

    # SLOPE

    slope = re.search(
        r"Slope \(R=.*?\)\s*([-\.\d]+)",
        texto
    )

    if slope:

        try:
            datos["slope"] = convertir_numero(
                slope.group(1)
            )
        except:
            pass

    # MAX DEVIATION

    max_dev = re.search(
        r"Max Deviation\s*([-\.\d]+)",
        texto
    )

    if max_dev:

        try:
            datos["max_deviation"] = convertir_numero(
                max_dev.group(1)
            )
        except:
            pass

    # RMS DEVIATION

    rms_dev = re.search(
        r"RMS Deviation\s*([-\.\d]+)",
        texto
    )

    if rms_dev:

        try:
            datos["rms_deviation"] = convertir_numero(
                rms_dev.group(1)
            )
        except:
            pass

    return datos


# ==========================================
# REGLAS DE DIAGNOSTICO
# ==========================================

def evaluar_kurtosis(valor):

    if valor < 1:
        return (
            "Kurtosis muy baja. Distribución normal y "
            "sin evidencia estadística de impactos."
        )

    elif valor < 3:
        return (
            "Condición normal."
        )

    elif valor < 5:
        return (
            "Posibles impactos iniciales. "
            "Revisar tendencia."
        )

    elif valor < 10:
        return (
            "Posible daño de rodamiento o lubricación."
        )

    else:
        return (
            "Impactos severos. Revisar inmediatamente."
        )


def evaluar_crest(valor):

    if valor < 3:
        return "Señal muy estable."

    elif valor < 4:
        return "Factor de cresta normal."

    elif valor < 6:
        return "Posibles impactos tempranos."

    elif valor < 8:
        return "Impactos importantes."

    else:
        return "Impactos severos o falla avanzada."


# ==========================================
# INFORME AUTOMATICO
# ==========================================

def generar_informe(datos):

    informe = []

    informe.append("ANALISIS ESTADISTICO AUTOMATICO")
    informe.append("=" * 60)

    informe.append("")

    if "rpm" in datos:
        informe.append(
            f"Velocidad de operación: {datos['rpm']} RPM"
        )

    # KURTOSIS

    if "kurtosis" in datos:

        informe.append("")
        informe.append(
            f"Kurtosis: {datos['kurtosis']:.3f}"
        )

        informe.append(
            evaluar_kurtosis(
                datos["kurtosis"]
            )
        )

    # CREST FACTOR

    if "crest_pos" in datos:

        informe.append("")
        informe.append(
            f"Crest Factor: {datos['crest_pos']:.2f}"
        )

        informe.append(
            evaluar_crest(
                datos["crest_pos"]
            )
        )

    # SKEWNESS

    if "skewness" in datos:

        informe.append("")
        informe.append(
            f"Skewness: {datos['skewness']:.3f}"
        )

        if abs(datos["skewness"]) < 0.2:

            informe.append(
                "Distribución simétrica."
            )

        else:

            informe.append(
                "Distribución asimétrica."
            )

    # DIAGNOSTICO GENERAL

    informe.append("")
    informe.append("DIAGNOSTICO GENERAL")
    informe.append("-" * 40)

    kurt = datos.get("kurtosis", 0)
    crest = datos.get("crest_pos", 0)

    if kurt < 1 and crest < 4:

        informe.append(
            "CONDICION BUENA."
        )

        informe.append(
            "La forma de onda es estable y no presenta "
            "evidencia estadística de defectos mecánicos."
        )

    elif kurt < 5:

        informe.append(
            "CONDICION ACEPTABLE."
        )

        informe.append(
            "Realizar seguimiento de tendencia."
        )

    else:

        informe.append(
            "CONDICION DEFICIENTE."
        )

        informe.append(
            "Investigar origen de impactos."
        )

    return "\n".join(informe)


# ==========================================
# INTERFAZ STREAMLIT
# ==========================================

st.set_page_config(
    page_title="Analizador Vibraciones",
    layout="wide"
)

st.title("🔧 Analizador Estadístico de Vibraciones")

st.write(
    "Cargue un archivo TXT exportado desde AMS, CSI 2140 "
    "u otro software de vibraciones."
)

archivo = st.file_uploader(
    "Seleccione archivo TXT",
    type=["txt"]
)

if archivo:

    try:

        texto = archivo.read().decode(
            "utf-8",
            errors="ignore"
        )

        with st.expander(
            "Ver contenido del archivo"
        ):
            st.text(texto[:5000])

        datos = extraer_datos(texto)

        st.subheader("Variables Extraídas")

        st.json(datos)

        informe = generar_informe(datos)

        st.subheader("Informe Automático")

        st.text_area(
            "",
            informe,
            height=400
        )

    except Exception as e:

        st.error(
            f"Error procesando archivo: {str(e)}"
        )
