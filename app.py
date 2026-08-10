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

    # Evaluación de Kurtosis
    if 2.3 <= kurtosis <= 3.5:
        hallazgos.append(f"Kurtosis Normal ({kurtosis}): Distribución gaussiana continua típica de máquina saludable.")
    elif kurtosis < 2.3:
        hallazgos.append(f"Kurtosis Baja ({kurtosis}): Predominio de componente senoidal pura o modulación suave.")
    elif 3.5 < kurtosis <= 4.5:
        hallazgos.append(f"Kurtosis Moderadamente Alta ({kurtosis}): Presencia de impactos levemente transitorios.")
    else:
        hallazgos.append(f"Kurtosis Severa ({kurtosis}): Presencia marcada de impactos impulsivos repetitivos (rodamientos/engranajes).")

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
        return f"Armónico (2X - {pos_xrpm:.2f}x): Desalineación, ho
