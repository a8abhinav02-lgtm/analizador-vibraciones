import streamlit as st
import re
import pandas as pd

# =====================================================
# CONFIGURACIÓN DE LA PÁGINA
# =====================================================
st.set_page_config(
    page_title="Analizador de Vibraciones - Cat II",
    page_icon="⚡",
    layout="wide"
)

# =====================================================
# FUNCIONES AUXILIARES Y PARSER
# =====================================================
def convertir_numero(valor):
    valor = str(valor).strip()
    if valor.startswith("-."):
        valor = valor.replace("-.", "-0.")
    elif valor.startswith("."):
        valor = "0" + valor
    return float(valor)

def extraer_datos(texto):
    datos = {}
    lines = texto.splitlines()

    # 1. Información General
    m = re.search(r"Equipment:\s*(.*)", texto)
    if m: datos["equipo"] = m.group(1).strip()

    m = re.search(r"Meas\. Point:\s*(.*)", texto)
    if m: datos["punto"] = m.group(1).strip()

    m = re.search(r"Date/Time:\s*(.*?)\s+RPM=", texto)
    if m: datos["fecha"] = m.group(1).strip()

    m = re.search(r"RPM=\s*([\d\.]+)", texto)
    if m: datos["rpm"] = float(m.group(1))

    # Helper para buscar la primera línea de datos debajo de un encabezado
    def obtener_numeros_despues_de(keyword):
        for i, line in enumerate(lines):
            if keyword in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    nums = re.findall(r'-?\d*\.?\d+', lines[j])
                    nums = [n for n in nums if n and n != '-']
                    if len(nums) >= 2:
                        return nums
        return []

    # 2. Max Peak & Crest Factor
    nums_max = obtener_numeros_despues_de("Max Peak")
    if len(nums_max) >= 4:
        datos["max_peak_neg"] = convertir_numero(nums_max[0])
        datos["max_peak_pos"] = convertir_numero(nums_max[1])
        datos["crest_neg"] = convertir_numero(nums_max[2])
        datos["crest_pos"] = convertir_numero(nums_max[3])

    # 3. Avg Peak & RMS Amplitude
    nums_avg = obtener_numeros_despues_de("Avg Peak")
    if len(nums_avg) >= 4:
        datos["avg_peak_neg"] = convertir_numero(nums_avg[0])
        datos["avg_peak_pos"] = convertir_numero(nums_avg[1])
        datos["rms_neg"] = convertir_numero(nums_avg[2])
        datos["rms_pos"] = convertir_numero(nums_avg[3])

    # 4. Kurtosis & Skewness
    nums_kurt = obtener_numeros_despues_de("Kurtosis")
    if len(nums_kurt) >= 2:
        datos["kurtosis"] = convertir_numero(nums_kurt[-2])
        datos["skewness"] = convertir_numero(nums_kurt[-1])

    # 5. Drift
    m_slope = re.search(r"Slope \(R=.*?\)\s*([-\.\d]+)", texto)
    if m_slope: datos["slope"] = convertir_numero(m_slope.group(1))

    m_max_dev = re.search(r"Max Deviation\s*([-\.\d]+)", texto)
    if m_max_dev: datos["max_deviation"] = convertir_numero(m_max_dev.group(1))

    m_rms_dev = re.search(r"RMS Deviation\s*([-\.\d]+)", texto)
    if m_rms_dev: datos["rms_deviation"] = convertir_numero(m_rms_dev.group(1))

    # 6. Eventos
    p_neg = re.search(r'\(-\)\s+Peaks\s+([\d\.]+)\s+\((\d+)\)\s+([\d\.]+)', texto)
    if p_neg:
        datos["neg_peak_xrpm"] = float(p_neg.group(1))
        datos["neg_peak_count"] = int(p_neg.group(2))
        datos["neg_peak_hz"] = float(p_neg.group(3))

    p_pos = re.search(r'\(\+\)\s+Peaks\s+([\d\.]+)\s+\((\d+)\)\s+([\d\.]+)', texto)
    if p_pos:
        datos["pos_peak_xrpm"] = float(p_pos.group(1))
        datos["pos_peak_count"] = int(p_pos.group(2))
        datos["pos_peak_hz"] = float(p_pos.group(3))

    p_zero = re.search(r'Zero Xs\/2\s+([\d\.]+)\s+\((\d+)\)\s+([\d\.]+)', texto)
    if p_zero:
        datos["zero_cross_xrpm"] = float(p_zero.group(1))
        datos["zero_cross_count"] = int(p_zero.group(2))
        datos["zero_cross_hz"] = float(p_zero.group(3))

    # 7. Distribución de Onda (Waveform Distribution %)
    match_dist = re.search(r"([\d\s]+)\(%\)", texto)
    if match_dist:
        dist_vals = [int(x) for x in match_dist.group(1).split()]
        if len(dist_vals) == 15:
            datos["distribucion_pct"] = dist_vals

    return datos

# =====================================================
# DIAGNÓSTICO EXPERTO (CATEGORÍA II)
# =====================================================
def diagnostico_experto(datos):
    kurtosis = datos.get("kurtosis", 3.0)
    crest = max(datos.get("crest_pos", 0), datos.get("crest_neg", 0))
    skew = datos.get("skewness", 0.0)

    hallazgos = []
    recomendaciones = []

    # Evaluación de Kurtosis (Basado en teoría ISO)
    if 2.3 <= kurtosis <= 3.5:
        hallazgos.append(f"Kurtosis Normal ({kurtosis}): Distribución gaussiana continua típica de máquina en condición saludable.")
    elif kurtosis < 2.3:
        hallazgos.append(f"Kurtosis Baja ({kurtosis}): Predominio de componente senoidal pura o señal suave.")
    elif 3.5 < kurtosis <= 4.5:
        hallazgos.append(f"Kurtosis Moderadamente Alta ({kurtosis}): Presencia de impactos levemente transitorios.")
    else:
        hallazgos.append(f"Kurtosis Severa ({kurtosis}): Presencia marcada de impactos impulsivos repetitivos (falla de rodamientos/engranajes).")

    # Evaluación Factor de Cresta
    if crest < 3.5:
        hallazgos.append(f"Factor de Cresta Normal ({crest:.2f}).")
    elif 3.5 <= crest < 5.0:
        hallazgos.append(f"Factor de Cresta Moderado ({crest:.2f}): Picos de alta frecuencia por encima del valor continuo RMS.")
    else:
        hallazgos.append(f"Factor de Cresta Elevado ({crest:.2f}): Picos de aceleración transitorios de alta energía.")

    # Evaluación Asimetría
    if abs(skew) < 0.2:
        hallazgos.append("Distribución simétrica de la forma de onda.")
    else:
        hallazgos.append(f"Distribución asimétrica (Skewness: {skew}): Carga/impacto unidireccional o fricción direccional.")

    # Condición Global y Ponderación
    if (2.0 <= kurtosis <= 3.5) and crest < 4.0:
        condicion = "🟢 BUENA"
        confianza = 95
        recomendaciones.append("Mantener la rutina de monitoreo periódica habitual.")
    elif (kurtosis <= 4.2) and crest < 5.2:
        condicion = "🟡 ACEPTABLE / ADVERTENCIA"
        confianza = 85
        recomendaciones.append("Verificar la tendencia en la envolvente de aceleración (gSE/PeakVue).")
        recomendaciones.append("Inspeccionar lubricación y estado de la transmisión por correas/poleas.")
    else:
        condicion = "🔴 ALERTA CRÍTICA"
        confianza = 90
        recomendaciones.append("Efectuar análisis de espectro FFT de alta frecuencia y Demodulación/PeakVue.")
        recomendaciones.append("Inspeccionar mecánicamente rodamientos, holguras y elementos de transmisión.")

    return condicion, confianza, hallazgos, recomendaciones

# =====================================================
# EVALUACIÓN CINEMÁTICA (xRPM)
# =====================================================
def evaluar_cinematica(pos_xrpm):
    if pos_xrpm is None or pos_xrpm == 0:
        return "Sin datos cinemáticos."
    
    if pos_xrpm < 0.95:
        return f"Sub-síncrono ({pos_xrpm:.2f}x): Jaula de rodamiento (FTF), desprendimiento de flujo o remolino de aceite."
    elif 0.95 <= pos_xrpm <= 1.05:
        return f"Síncrono (1X - {pos_xrpm:.2f}x): Desbalance dinámico o componente fundamental."
    elif 1.9 <= pos_xrpm <= 2.1:
        return f"Armónico (2X - {pos_xrpm:.2f}x): Desalineación, holgura mecánica o eje agrietado."
    elif 2.1 < pos_xrpm < 12.0:
        return f"Banda Media ({pos_xrpm:.2f}x): Frecuencias de falla de rodamientos (BPFO/BPFI) o paso de paletas."
    else:
        return f"Alta Frecuencia ({pos_xrpm:.2f}x): Paso de álabes/dientes, engrane, armónico VFD o modulación de correa."

# =====================================================
# INTERFAZ Y FLUJO DE USUARIO EN STREAMLIT
# =====================================================
st.title("⚡ Analizador Estadístico de Vibraciones (Categoría II)")

archivo = st.file_uploader("Cargar reporte TXT (CSI / AMS Manager)", type=["txt"])

if archivo:
    try:
        texto = archivo.read().decode("utf-8", errors="ignore")
        datos = extraer_datos(texto)

        # -------------------------------------------------------------
        # AJUSTE / CONFIRMACIÓN DE VELOCIDAD DE OPERACIÓN (RPM)
        # -------------------------------------------------------------
        rpm_detectada = datos.get("rpm", 1780.0)

        with st.sidebar:
            st.header("⚙️ Configuración Cinemática")
            st.info(f"RPM detectada en TXT: **{rpm_detectada:.1f} RPM**")
            
            rpm_real = st.number_input(
                "Confirmar/Ajustar RPM Real de Operación:",
                min_value=1.0,
                max_value=100000.0,
                value=float(rpm_detectada),
                step=1.0,
                help="Si midió con estroboscopio o sabe la velocidad real del proceso, ajústela aquí para recalcular las frecuencias xRPM."
            )

        # Recalcular órdenes cinemáticos si la RPM fue modificada por el usuario
        datos["rpm"] = rpm_real
        frecuencia_1x_hz = rpm_real / 60.0

        if "pos_peak_hz" in datos and frecuencia_1x_hz > 0:
            datos["pos_peak_xrpm"] = datos["pos_peak_hz"] / frecuencia_1x_hz
        if "neg_peak_hz" in datos and frecuencia_1x_hz > 0:
            datos["neg_peak_xrpm"] = datos["neg_peak_hz"] / frecuencia_1x_hz
        if "zero_cross_hz" in datos and frecuencia_1x_hz > 0:
            datos["zero_cross_xrpm"] = datos["zero_cross_hz"] / frecuencia_1x_hz

        # -------------------------------------------------------------
        # DESPLIEGUE DE ENCABEZADO GENERAL
        # -------------------------------------------------------------
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Equipo", datos.get("equipo", "N/A"))
        col_m2.metric("Punto", datos.get("punto", "N/A"))
        col_m3.metric("Fecha", datos.get("fecha", "N/A"))
        col_m4.metric("Velocidad Validada", f"{rpm_real:.1f} RPM")

        st.markdown("---")

        # -------------------------------------------------------------
        # PESTAÑAS DE TRABAJO
        # -------------------------------------------------------------
        tab_diag, tab_stats, tab_events, tab_raw, tab_help = st.tabs([
            "📋 Diagnóstico Experto", 
            "📊 Indicadores Estadísticos", 
            "🎯 Cinemática y Eventos", 
            "📄 Raw Data",
            "ℹ️ Guía & Ayuda"
        ])

        # TAB 1: DIAGNÓSTICO EXPERTO
        with tab_diag:
            condicion, confianza, hallazgos, recomendaciones = diagnostico_experto(datos)
            
            c_left, c_right = st.columns([1, 2])
            with c_left:
                st.subheader("Estado General")
                st.markdown(f"## {condicion}")
                st.progress(confianza / 100)
                st.caption(f"Nivel de Confianza: {confianza}%")

            with c_right:
                st.subheader("Hallazgos Clave")
                for h in hallazgos:
                    st.markdown(f"• {h}")

                st.subheader("Recomendaciones Tácticas")
                for r in recomendaciones:
                    st.markdown(f"👉 **{r}**")

        # TAB 2: INDICADORES ESTADÍSTICOS
        with tab_stats:
            st.subheader("Parámetros Estadísticos de Forma de Onda")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kurtosis", f"{datos.get('kurtosis', 0):.3f}")
            c2.metric("Skewness", f"{datos.get('skewness', 0):.3f}")
            c3.metric("Crest Factor (+)", f"{datos.get('crest_pos', 0):.2f}")
            c4.metric("Crest Factor (-)", f"{datos.get('crest_neg', 0):.2f}")

            # Gráfico Nativo de Histograma de Distribución
            if "distribucion_pct" in datos:
                st.subheader("Distribución de la Onda (Histograma Std Dev)")
                std_labels = ["-5.0", "-4.3", "-3.6", "-2.9", "-2.1", "-1.4", "-0.7", "0.0", "0.7", "1.4", "2.1", "2.9", "3.6", "4.3", "5.0"]
                df_dist = pd.DataFrame({
                    "Desviación Estándar (σ)": std_labels,
                    "Porcentaje (%)": datos["distribucion_pct"]
                }).set_index("Desviación Estándar (σ)")
                
                st.bar_chart(df_dist)

        # TAB 3: CINEMÁTICA Y EVENTOS
        with tab_events:
            st.subheader("Análisis de Picos y Frecuencias (xRPM)")
            
            xrpm_pos = datos.get("pos_peak_xrpm", 0)
            interpretacion = evaluar_cinematica(xrpm_pos)
            
            st.info(f"**Interpretación Cinemática:** {interpretacion}")

            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                st.markdown("##### Picos Positivos (+)")
                st.write(f"• **Frecuencia:** {xrpm_pos:.2f} xRPM ({datos.get('pos_peak_hz',0):.1f} Hz)")
                st.write(f"• **Conteo Eventos:** {datos.get('pos_peak_count',0)}")
            
            with col_e2:
                st.markdown("##### Picos Negativos (-)")
                st.write(f"• **Frecuencia:** {datos.get('neg_peak_xrpm',0):.2f} xRPM ({datos.get('neg_peak_hz',0):.1f} Hz)")
                st.write(f"• **Conteo Eventos:** {datos.get('neg_peak_count',0)}")

            with col_e3:
                st.markdown("##### Cruces por Cero")
                st.write(f"• **Frecuencia:** {datos.get('zero_cross_xrpm',0):.2f} xRPM ({datos.get('zero_cross_hz',0):.1f} Hz)")
                st.write(f"• **Conteo Cruces:** {datos.get('zero_cross_count',0)}")

        # TAB 4: RAW DATA
        with tab_raw:
            st.json(datos)

        # TAB 5: GUÍA Y AYUDA METODOLÓGICA
        with tab_help:
            st.header("📖 Guía de Interpretación Metodológica (ISO 18436-2)")
            st.markdown("""
            Esta herramienta evalúa los parámetros estadísticos de la **forma de onda en el tiempo (Time Waveform)** extraídos de colectores de datos (CSI / Emerson AMS Machinery Manager). 
            A continuación se detalla el significado físico e industrial de cada sección:
            """)

            with st.expander("📋 1. Diagnóstico Experto y Semáforo de Condición"):
                st.markdown("""
                * **🟢 BUENA:** La señal presenta una distribución gaussiana continua, Kurtosis cercana a 3.0 y Factor de Cresta bajo (< 4.0). Indica un funcionamiento suave sin transitorios ni impactos.
                * **🟡 ACEPTABLE / ADVERTENCIA:** Se observan ligeras desviaciones o aumentos en el Factor de Cresta o Kurtosis. Es un indicador de **fase inicial de falla** (frecuencia de alta energía en rodamientos, inicio de degradación de lubricante o tensión de correas).
                * **🔴 ALERTA CRÍTICA:** Elevada energía en picos o Kurtosis muy alta (> 4.5). Indica presencia severa de impactos repetitivos por picaduras en rodamientos, dientes de engranajes agrietados o soltura mecánica grave.
                """)

            with st.expander("📊 2. Indicadores Estadísticos de la Forma de Onda"):
                st.markdown("""
                * **Kurtosis (Curtosis):** Mide el grado de "picudez" o presencia de transitorios e impactos en la forma de onda.
                  * **$K \approx 3.0$**: Distribución Gaussiana (Máquina operando en condición normal).
                  * **$K < 2.3$**: Predominio de componente armónica/senoidal pura o señal plana.
                  * **$K > 3.5$**: Indica impactos repetitivos intermitentes (Etapa 2/3 de falla en rodamientos).
                * **Factor de Cresta (Crest Factor = $\\frac{\\text{Peak}}{\\text{RMS}}$):** Compara el pico máximo instantáneo con el nivel de energía continua $RMS$. Un Factor de Cresta $> 4.0 - 5.0$ alerta sobre piquetes transitorios de alta aceleración ($G$-s).
                * **Skewness (Asimetría):** Mide la simetría de la onda respecto al eje cero. 
                  * **$\text{Skew} \approx 0$**: Fuerzas simétricas en ambas direcciones.
                  * **$\text{Skew} \neq 0$ ($> |0.2|$)**: Fricción unidireccional, rozamiento de rotor o impactos direccionales.
                * **Histograma de Distribución ($\sigma$):** Representa qué porcentaje de las muestras de tiempo caen en cada banda de Desviación Estándar. Una campana de Gauss simétrica confirma operabilidad normal.
                """)

            with st.expander("🎯 3. Cinemática y Eventos (xRPM & Hz)"):
                st.markdown("""
                Muestra la frecuencia donde ocurren los eventos pico o de cruce por cero en relación con la velocidad de giro ($1\text{X}$):
                * **$< 0.95\text{x}$ (Sub-síncrono):** Asociado a jaula de rodamiento (FTF), remolino de aceite (*oil whirl*) o turbulencia de flujo.
                * **$1.0\text{x}$ (Síncrono):** Desbalance dinámico, excentricidad o problema fundamental del rotor.
                * **$2.0\text{x}$:** Desalineación angular/paralela, eje curvado o soltura mecánica.
                * **$2.1\text{x} - 12.0\text{x}$ (Banda Media):** Frecuencias de falla en pistas de rodamientos (BPFO, BPFI, BSF) o paso de paletas principales.
                * **$> 12.0\text{x}$ (Alta Frecuencia):** Frecuencia de paso de álabes (bombas Kamyr), engrane de dientes, modulación por correa o armónicos de variadores de velocidad (VFD / PWM).
                """)

            with st.expander("📄 4. Raw Data"):
                st.markdown("""
                Contiene la estructura de datos cruda extraída del archivo `.txt` codificada en formato JSON. Permite verificar los valores exactos capturados por el motor de expresiones regulares para fines de auditoría técnica.
                """)

    except Exception as e:
        st.error(f"Error procesando el archivo de vibraciones: {str(e)}")
