import streamlit as st
import re


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def convertir_numero(valor):

    valor = valor.strip()

    if valor.startswith("-."):
        valor = valor.replace("-.", "-0.")

    elif valor.startswith("."):
        valor = "0" + valor

    return float(valor)


# =====================================================
# EXTRAER DATOS
# =====================================================

def extraer_datos(texto):

    datos = {}

    # RPM

    rpm = re.search(
        r"RPM=\s*([\d\.]+)",
        texto
    )

    if rpm:

        try:
            datos["rpm"] = float(rpm.group(1))
        except:
            pass

    # =====================================================
    # CREST FACTOR Y MAX PEAK
    # =====================================================

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

    # =====================================================
    # KURTOSIS Y SKEWNESS
    # =====================================================

    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):

        if "Kurtosis" in linea and "Skewness" in linea:

            for j in range(i + 1, min(i + 10, len(lineas))):

                candidato = lineas[j].strip()

                # Ignorar líneas de guiones

                if "-" * 5 in candidato:
                    continue

                # Buscar números decimales

                numeros = re.findall(
                    r'-?\.\d+|-?\d+\.\d+',
                    candidato
                )

                if len(numeros) >= 2:

                    try:

                        datos["kurtosis"] = convertir_numero(
                            numeros[0]
                        )

                        datos["skewness"] = convertir_numero(
                            numeros[1]
                        )

                        break

                    except:
                        pass

            break

    # =====================================================
    # SLOPE
    # =====================================================

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

    # =====================================================
    # MAX DEVIATION
    # =====================================================

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

    # =====================================================
    # RMS DEVIATION
    # =====================================================

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


# =====================================================
# REGLAS DE DIAGNOSTICO
# =====================================================

def evaluar_kurtosis(valor):

    if valor < 1:

        return (
            "Kurtosis muy baja. Distribución normal "
            "sin evidencia de impactos."
        )

    elif valor < 3:

        return (
            "Condición normal."
        )

    elif valor < 5:

        return (
            "Posibles impactos iniciales."
        )

    elif valor < 10:

        return (
            "Posible daño de rodamiento o lubricación."
        )

    else:

        return (
            "Impactos severos."
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
        return "Impactos severos."


# =====================================================
# INFORME
# =====================================================

def generar_informe(datos):

    informe = []

    informe.append("ANALISIS ESTADISTICO AUTOMATICO")
    informe.append("=" * 60)

    informe.append("")

    if "rpm" in datos:

        informe.append(
            f"Velocidad de operación: {datos['rpm']} RPM"
        )

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

    informe.append("")
    informe.append("DIAGNOSTICO GENERAL")
    informe.append("-" * 40)

    kurt = datos.get("kurtosis", 0)
    crest = datos.get("crest_pos", 0)

    if kurt < 1 and crest < 4:

        informe.append("")
        informe.append("CONDICION BUENA")

        informe.append(
            "La señal presenta comportamiento estable. "
            "No se observan evidencias estadísticas de "
            "impactos, falla de rodamientos, holgura "
            "o problemas severos."
        )

    elif kurt < 5:

        informe.append("")
        informe.append("CONDICION ACEPTABLE")

        informe.append(
            "Mantener monitoreo y análisis de tendencia."
        )

    else:

        informe.append("")
        informe.append("CONDICION DEFICIENTE")

        informe.append(
            "Investigar origen de impactos y revisar "
            "estado de los rodamientos."
        )

    return "\n".join(informe)


# =====================================================
# STREAMLIT
# =====================================================

st.set_page_config(
    page_title="Analizador Estadístico",
    layout="wide"
)

st.title("🔧 Analizador Estadístico de Vibraciones")

st.write(
    "Cargue un archivo TXT exportado desde AMS Machinery Manager, CSI 2140 o software equivalente."
)

archivo = st.file_uploader(
    "Seleccione un archivo TXT",
    type=["txt"]
)

if archivo:

    try:

        texto = archivo.read().decode(
            "utf-8",
            errors="ignore"
        )

        datos = extraer_datos(texto)

        st.subheader("Variables extraídas")

        st.json(datos)

        informe = generar_informe(datos)

        st.subheader("Informe automático")

        st.text_area(
            "",
            informe,
            height=450
        )

    except Exception as e:

        st.error(
            f"Error procesando archivo: {str(e)}"
        )
