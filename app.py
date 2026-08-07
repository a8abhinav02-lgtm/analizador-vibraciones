import streamlit as st
import re

# =====================================================
# CONFIGURACION PAGINA
# =====================================================

st.set_page_config(
    page_title="Analizador Vibraciones V3",
    layout="wide"
)

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


def extraer_numeros(linea):

    numeros = re.findall(
        r'-?\d+\.\d+|-?\.\d+|-?\d+',
        linea
    )

    return numeros


# =====================================================
# EXTRACCION DE DATOS
# =====================================================

def extraer_datos(texto):

    datos = {}

    lineas = texto.splitlines()

    # =====================================
    # INFORMACION GENERAL
    # =====================================

    m = re.search(r"Equipment:\s*(.*)", texto)

    if m:
        datos["equipo"] = m.group(1).strip()

    m = re.search(r"Meas\. Point:\s*(.*)", texto)

    if m:
        datos["punto"] = m.group(1).strip()

    m = re.search(
        r"Date/Time:\s*(.*?)\s+RPM=",
        texto
    )

    if m:
        datos["fecha"] = m.group(1).strip()

    m = re.search(
        r"RPM=\s*([\d\.]+)",
        texto
    )

    if m:
        datos["rpm"] = float(m.group(1))

    # =====================================
    # MAX PEAK / CREST FACTOR
    # =====================================

    for i, linea in enumerate(lineas):

        if "Max Peak" in linea and "Crest Factor" in linea:

            try:

                valores = extraer_numeros(
                    lineas[i + 2]
                )

                if len(valores) >= 4:

                    datos["max_peak_neg"] = convertir_numero(valores[0])
                    datos["max_peak_pos"] = convertir_numero(valores[1])

                    datos["crest_neg"] = convertir_numero(valores[2])
                    datos["crest_pos"] = convertir_numero(valores[3])

            except:
                pass

    # =====================================
    # AVG PEAK / RMS
    # =====================================

    for i, linea in enumerate(lineas):

        if "Avg Peak" in linea and "RMS Amplitude" in linea:

            try:

                valores = extraer_numeros(
                    lineas[i + 2]
                )

                if len(valores) >= 4:

                    datos["avg_peak_neg"] = convertir_numero(valores[0])
                    datos["avg_peak_pos"] = convertir_numero(valores[1])

                    datos["rms_neg"] = convertir_numero(valores[2])
                    datos["rms_pos"] = convertir_numero(valores[3])

            except:
                pass

    # =====================================
    # KURTOSIS / SKEWNESS
    # =====================================

    for i, linea in enumerate(lineas):

        if "Kurtosis" in linea and "Skewness" in linea:

            try:

                valores = extraer_numeros(
                    lineas[i + 2]
                )

                if len(valores) >= 2:

                    datos["kurtosis"] = convertir_numero(
                        valores[-2]
                    )

                    datos["skewness"] = convertir_numero(
                        valores[-1]
                    )

            except:
                pass

    # =====================================
    # DRIFT
    # =====================================

    m = re.search(
        r"Slope \(R=.*?\)\s*([-\.\d]+)",
        texto
    )

    if m:

        try:
            datos["slope"] = convertir_numero(
                m.group(1)
            )
        except:
            pass

    m = re.search(
        r"Max Deviation\s*([-\.\d]+)",
        texto
    )

    if m:

        try:
            datos["max_deviation"] = convertir_numero(
                m.group(1)
            )
        except:
            pass

    m = re.search(
        r"RMS Deviation\s*([-\.\d]+)",
        texto
    )

    if m:

        try:
            datos["rms_deviation"] = convertir_numero(
                m.group(1)
            )
        except:
            pass

    # =====================================
    # EVENTOS
    # =====================================

    for linea in lineas:

        if "(-) Peaks" in linea:

            valores = extraer_numeros(linea)

            if len(valores) >= 3:

                datos["neg_peak_xrpm"] = float(valores[0])
                datos["neg_peak_count"] = int(float(valores[1]))
                datos["neg_peak_hz"] = float(valores[2])

        if "(+) Peaks" in linea:

            valores = extraer_numeros(linea)

            if len(valores) >= 3:

                datos["pos_peak_xrpm"] = float(valores[0])
                datos["pos_peak_count"] = int(float(valores[1]))
                datos["pos_peak_hz"] = float(valores[2])

        if "Zero Xs/2" in linea:

            valores = extraer_numeros(linea)

            if len(valores) >= 3:

                datos["zero_cross_xrpm"] = float(valores[0])
                datos["zero_cross_count"] = int(float(valores[1]))
                datos["zero_cross_hz"] = float(valores[2])

    return datos


# =====================================================
# DIAGNOSTICO EXPERTO
# =====================================================

def diagnostico_experto(datos):

    kurtosis = datos.get("kurtosis", 0)

    crest = max(
        datos.get("crest_pos", 0),
        datos.get("crest_neg", 0)
    )

    skew = datos.get("skewness", 0)

    hallazgos = []
    recomendaciones = []

    # Kurtosis

    if kurtosis < 1:

        hallazgos.append(
            "Kurtosis baja. No se observan impactos repetitivos."
        )

    elif kurtosis < 3:

        hallazgos.append(
            "Kurtosis dentro de rango normal."
        )

    elif kurtosis < 5:

        hallazgos.append(
            "Posibles impactos iniciales."
        )

    else:

        hallazgos.append(
            "Impactos significativos detectados."
        )

    # Crest Factor

    if crest < 4:

        hallazgos.append(
            "Crest Factor normal."
        )

    elif crest < 6:

        hallazgos.append(
            "Crest Factor moderadamente elevado."
        )

    else:

        hallazgos.append(
            "Crest Factor elevado."
        )

    # Skewness

    if abs(skew) < 0.2:

        hallazgos.append(
            "Distribución simétrica."
        )

    else:

        hallazgos.append(
            "Distribución asimétrica."
        )

    # Condición

    if kurtosis < 1 and crest < 4:

        condicion = "🟢 BUENA"
        confianza = 95

        recomendaciones.append(
            "Continuar el monitoreo periódico."
        )

    elif kurtosis < 3 and crest < 5:

        condicion = "🟡 ACEPTABLE"
        confianza = 85

        recomendaciones.append(
            "Verificar la tendencia en próxima inspección."
        )

    else:

        condicion = "🔴 ALERTA"
        confianza = 70

        recomendaciones.append(
            "Revisar FFT, envolvente y condición mecánica."
        )

    return (
        condicion,
        confianza,
        hallazgos,
        recomendaciones
    )


# =====================================================
# INTERFAZ
# =====================================================

st.title("🔧 Analizador Estadístico de Vibraciones V3")

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

        datos = extraer_datos(texto)

        st.header("Información General")

        c1, c2 = st.columns(2)

        with c1:

            st.write(
                "**Equipo:**",
                datos.get("equipo", "")
            )

            st.write(
                "**Punto:**",
                datos.get("punto", "")
            )

        with c2:

            st.write(
                "**Fecha:**",
                datos.get("fecha", "")
            )

            st.write(
                "**RPM:**",
                datos.get("rpm", "")
            )

        st.header("Indicadores Principales")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Kurtosis",
            datos.get("kurtosis", "N/A")
        )

        c2.metric(
            "Skewness",
            datos.get("skewness", "N/A")
        )

        c3.metric(
            "Crest (+)",
            datos.get("crest_pos", "N/A")
        )

        c4.metric(
            "Crest (-)",
            datos.get("crest_neg", "N/A")
        )

        condicion, confianza, hallazgos, recomendaciones = (
            diagnostico_experto(datos)
        )

        st.header("Semáforo de Condición")

        st.subheader(condicion)

        st.progress(confianza / 100)

        st.write(
            f"Confianza estimada: {confianza}%"
        )

        st.header("Hallazgos")

        for item in hallazgos:
            st.write("✅", item)

        st.header("Recomendaciones")

        for item in recomendaciones:
            st.write("🔹", item)

        st.header("Eventos")

        st.write(
            f"(-) Peaks: {datos.get('neg_peak_xrpm','N/A')} xRPM"
        )

        st.write(
            f"(+) Peaks: {datos.get('pos_peak_xrpm','N/A')} xRPM"
        )

        st.write(
            f"Zero Crossings: {datos.get('zero_cross_xrpm','N/A')} xRPM"
        )

        st.header("Datos Extraídos")

        st.json(datos)

    except Exception as e:

        st.error(
            f"Error procesando archivo: {str(e)}"
        )
