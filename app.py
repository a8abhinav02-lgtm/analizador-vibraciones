import streamlit as st
import re


def extraer_datos(texto):

    datos = {}

    rpm = re.search(r"RPM=\s*([\d\.]+)", texto)

    if rpm:
        datos["rpm"] = float(rpm.group(1))

    crest = re.search(
        r"Max Peak.*?\n\s*([-\.\d]+)\s+([.\d]+)\s+([.\d]+)\s+([.\d]+)",
        texto,
        re.DOTALL
    )

    if crest:
        datos["max_peak_neg"] = float(crest.group(1))
        datos["max_peak_pos"] = float(crest.group(2))
        datos["crest_neg"] = float(crest.group(3))
        datos["crest_pos"] = float(crest.group(4))

    kurt = re.search(
        r"Kurtosis\s+Skewness.*?\n\s*([-\.\d]+)\s+([-\.\d]+)",
        texto,
        re.DOTALL
    )

    if kurt:
        datos["kurtosis"] = float(kurt.group(1))
        datos["skewness"] = float(kurt.group(2))

    slope = re.search(
        r"Slope \(R=.*?\)\s*([-\.\d]+)",
        texto
    )

    if slope:
        datos["slope"] = float(slope.group(1))

    max_dev = re.search(
        r"Max Deviation\s*([-\.\d]+)",
        texto
    )

    if max_dev:
        datos["max_deviation"] = float(max_dev.group(1))

    rms_dev = re.search(
        r"RMS Deviation\s*([-\.\d]+)",
        texto
    )

    if rms_dev:
        datos["rms_deviation"] = float(rms_dev.group(1))

    return datos


def evaluar_kurtosis(valor):

    if valor < 1:
        return "No se observan impactos ni defectos de rodamiento."

    elif valor < 3:
        return "Condición normal."

    elif valor < 5:
        return "Posibles impactos iniciales."

    elif valor < 10:
        return "Posible daño de rodamiento."

    else:
        return "Falla avanzada con impactos severos."


def evaluar_crest(valor):

    if valor < 3:
        return "Muy estable."

    elif valor < 4:
        return "Normal."

    elif valor < 6:
        return "Impactos tempranos."

    elif valor < 8:
        return "Impactos significativos."

    return "Falla severa."


def generar_informe(datos):

    informe = []

    informe.append("ANÁLISIS ESTADÍSTICO AUTOMÁTICO")
    informe.append("")
    informe.append(f"RPM: {datos.get('rpm','N/A')}")

    if "kurtosis" in datos:
        informe.append("")
        informe.append(f"Kurtosis: {datos['kurtosis']}")
        informe.append(
            evaluar_kurtosis(datos["kurtosis"])
        )

    if "crest_pos" in datos:
        informe.append("")
        informe.append(
            f"Crest Factor: {datos['crest_pos']}"
        )
        informe.append(
            evaluar_crest(datos["crest_pos"])
        )

    if "skewness" in datos:

        informe.append("")
        informe.append(
            f"Skewness: {datos['skewness']}"
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
    informe.append("DIAGNÓSTICO GENERAL")

    if datos.get("kurtosis", 0) < 1 and datos.get("crest_pos", 0) < 4:

        informe.append(
            "Condición BUENA."
        )

    elif datos.get("kurtosis", 0) < 5:

        informe.append(
            "Condición ACEPTABLE."
        )

    else:

        informe.append(
            "Condición DEFICIENTE."
        )

    return "\n".join(informe)


st.set_page_config(
    page_title="Analizador Vibraciones",
    layout="wide"
)

st.title("Analizador Estadístico de Vibraciones")

archivo = st.file_uploader(
    "Seleccione archivo TXT",
    type=["txt"]
)

if archivo:

    texto = archivo.read().decode(
        "utf-8",
        errors="ignore"
    )

    datos = extraer_datos(texto)

    st.subheader("Variables Extraídas")

    st.json(datos)

    informe = generar_informe(datos)

    st.subheader("Informe")

    st.text_area(
        "",
        informe,
        height=400
    )
