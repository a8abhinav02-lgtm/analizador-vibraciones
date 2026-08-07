import streamlit as st
import re

# ====================================================
# FUNCIONES AUXILIARES
# ====================================================

def convertir_numero(valor):

    valor = valor.strip()

    if valor.startswith("-."):
        valor = valor.replace("-.", "-0.")

    elif valor.startswith("."):
        valor = "0" + valor

    return float(valor)


# ====================================================
# EXTRACCION DE DATOS
# ====================================================

def extraer_datos(texto):

    datos = {}

    # ------------------------------------------------
    # EQUIPO
    # ------------------------------------------------

    eq = re.search(
        r'Equipment:\s*(.*)',
        texto
    )

    if eq:
        datos["equipo"] = eq.group(1).strip()

    # ------------------------------------------------
    # PUNTO
    # ------------------------------------------------

    punto = re.search(
        r'Meas\. Point:\s*(.*)',
        texto
    )

    if punto:
        datos["punto"] = punto.group(1).strip()

    # ------------------------------------------------
    # FECHA
    # ------------------------------------------------

    fecha = re.search(
        r'Date/Time:\s*(.*?)\s+RPM=',
        texto
    )

    if fecha:
        datos["fecha"] = fecha.group(1).strip()

    # ------------------------------------------------
    # RPM
    # ------------------------------------------------

    rpm = re.search(
        r'RPM=\s*([\d\.]+)',
        texto
    )

    if rpm:

        try:
            datos["rpm"] = float(rpm.group(1))
        except:
            pass

    # ------------------------------------------------
    # MAX PEAK Y CREST FACTOR
    # ------------------------------------------------

    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):

        if "Max Peak" in linea and "Crest Factor" in linea:

            try:

                valores = lineas[i + 2].split()

                if len(valores) >= 4:

                    datos["max_peak_neg"] = convertir_numero(
                        valores[0]
                    )

                    datos["max_peak_pos"] = convertir_numero(
                        valores[1]
                    )

                    datos["crest_neg"] = convertir_numero(
                        valores[2]
                    )

                    datos["crest_pos"] = convertir_numero(
                        valores[3]
                    )

            except:
                pass

    # ------------------------------------------------
    # AVG PEAK Y RMS
    # ------------------------------------------------

    for i, linea in enumerate(lineas):

        if "Avg Peak" in linea and "RMS Amplitude" in linea:

            try:

                valores = lineas[i + 2].split()

                if len(valores) >= 4:

                    datos["avg_peak_neg"] = convertir_numero(
                        valores[0]
                    )

                    datos["avg_peak_pos"] = convertir_numero(
                        valores[1]
                    )

                    datos["rms_neg"] = convertir_numero(
                        valores[2]
                    )

                    datos["rms_pos"] = convertir_numero(
                        valores[3]
                    )

            except:
                pass

    # ------------------------------------------------
    # KURTOSIS Y SKEWNESS
    # ------------------------------------------------

    for i, linea in enumerate(lineas):

        if "Kurtosis" in linea and "Skewness" in linea:

            for j in range(i + 1, min(i + 10, len(lineas))):

                candidato = lineas[j].strip()

                if "----" in candidato:
                    continue

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

    # ------------------------------------------------
    # SLOPE
    # ------------------------------------------------

    slope = re.search(
        r'Slope \(R=.*?\)\s*([-\.\d]+)',
        texto
    )

    if slope:

        try:
            datos["slope"] = convertir_numero(
                slope.group(1)
            )
        except:
            pass

    # ------------------------------------------------
    # DESVIACIONES
    # ------------------------------------------------

    max_dev = re.search(
        r'Max Deviation\s*([-\.\d]+)',
        texto
    )

    if max_dev:

        try:
            datos["max_deviation"] = convertir_numero(
                max_dev.group(1)
            )

        except:
            pass

    rms_dev = re.search(
        r'RMS Deviation\s*([-\.\d]+)',
        texto
    )

    if rms_dev:

        try:
            datos["rms_deviation"] = convertir_numero(
                rms_dev.group(1)
            )

        except:
            pass

    # ------------------------------------------------
    # EVENTOS
    # ------------------------------------------------

    for linea in lineas:

        if "(-) Peaks" in linea:

            numeros = re.findall(
                r'([\d\.]+)',
                linea
            )

            if len(numeros) >= 3:

                datos["neg_peak_xrpm"] = float(numeros[0])
                datos["neg_peak_hz"] = float(numeros[2])

        if "(+) Peaks" in linea:

            numeros = re.findall(
                r'([\d\.]+)',
                linea
            )

            if len(numeros) >= 3:

                datos["pos_peak_xrpm"] = float(numeros[0])
                datos["pos_peak_hz"] = float(numeros[2])

        if "Zero Xs/2" in linea:

            numeros = re.findall(
                r'([\d\.]+)',
                linea
            )

            if len(numeros) >= 3:

                datos["zero_cross_xrpm"] = float(numeros[0])
                datos["zero_cross_hz"] = float(numeros[2])

    return datos


# ====================================================
# DIAGNOSTICO
# ====================================================

def generar_diagnostico(datos):

    observaciones = []

    kurt = datos.get("kurtosis", 0)

    if kurt < 1:

        observaciones.append(
            "✅ Kurtosis baja: no se evidencian impactos."
        )

    elif kurt < 5:

        observaciones.append(
            "⚠ Posibles impactos iniciales."
        )

    else:

        observaciones.append(
            "🔴 Probables impactos severos."
        )

    crest = datos.get("crest_pos")

    if crest:

        if crest < 4:

            observaciones.append(
                "✅ Crest Factor normal."
            )

        elif crest < 6:

            observaciones.append(
                "⚠ Posibles impactos tempranos."
            )

        else:

            observaciones.append(
                "🔴 Crest Factor elevado."
            )

    skew = datos.get("skewness")

    if skew is not None:

        if abs(skew) < 0.2:

            observaciones.append(
                "✅ Distribución simétrica."
            )

        else:

            observaciones.append(
                "⚠ Distribución asimétrica."
            )

    if kurt < 1 and crest and crest < 4:

        condicion = "🟢 BUENA"

    elif kurt < 5:

        condicion = "🟡 ACEPTABLE"

    else:

        condicion = "🔴 DEFICIENTE"

    return condicion, observaciones


# ====================================================
# STREAMLIT
# ====================================================

st.set_page_config(
    page_title="Analizador de Vibraciones",
    layout="wide"
)

st.title("🔧 Analizador Estadístico de Vibraciones")

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

    st.header("Información General")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Equipo:**", datos.get("equipo", ""))
        st.write("**Punto:**", datos.get("punto", ""))

    with col2:
        st.write("**Fecha:**", datos.get("fecha", ""))
        st.write("**RPM:**", datos.get("rpm", ""))

    st.header("Variables Extraídas")

    st.json(datos)

    st.header("Indicadores Principales")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Kurtosis",
            datos.get("kurtosis", "N/A")
        )

    with c2:
        st.metric(
            "Skewness",
            datos.get("skewness", "N/A")
        )

    with c3:
        st.metric(
            "Crest Factor",
            datos.get("crest_pos", "N/A")
        )

    condicion, observaciones = generar_diagnostico(datos)

    st.header("Diagnóstico Automático")

    st.subheader(f"Condición: {condicion}")

    for obs in observaciones:
        st.write(obs)

    st.header("Eventos Detectados")

    st.write(
        f"(-) Peaks: {datos.get('neg_peak_xrpm','N/A')} xRPM"
    )

    st.write(
        f"(+) Peaks: {datos.get('pos_peak_xrpm','N/A')} xRPM"
    )

    st.write(
        f"Zero Crossings: {datos.get('zero_cross_xrpm','N/A')} xRPM"
    )
