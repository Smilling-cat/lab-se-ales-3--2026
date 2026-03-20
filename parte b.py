"""
PARTE B — Medición de Jitter y Shimmer
Procesamiento Digital de Señales — Ingeniería Biomédica, UMNG 2026-1

Procedimiento:
  1. Cargar las 6 grabaciones y seleccionar la ventana de 150 ms con más voz activa
  2. Aplicar filtro pasa-banda (80–400 Hz hombres / 150–500 Hz mujeres)
  3. Calcular Jitter absoluto y relativo (%)
  4. Calcular Shimmer absoluto y relativo (%)
  5. Si shimmer > 10% → calcular HNR como indicador alternativo
  6. Presentar tabla comparativa y boxplots hombres vs. mujeres

Umbrales clínicos de referencia (PRAAT / literatura):
  Jitter relativo  <= 1.040 %   ->  normal
  Shimmer relativo <= 3.08  %   ->  normal   (> 10% sospecha de mal microfono)
  HNR              >= 7 dB      ->  normal
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
from scipy.signal import butter, filtfilt, find_peaks

# ============================================================
#  RUTAS
# ============================================================
CARPETA_AUDIO = r"C:\Users\amaya\Desktop\universidad\2026-1\procesamiento digital de señales\lab 3\auido"
CARPETA_FIGS  = r"C:\Users\amaya\Desktop\universidad\2026-1\procesamiento digital de señales\lab 3\figuras"

NOMBRES = ["hombre1", "hombre2", "hombre3", "mujer1", "mujer2", "mujer3"]
GENEROS = {
    "hombre1": "Hombre", "hombre2": "Hombre", "hombre3": "Hombre",
    "mujer1":  "Mujer",  "mujer2":  "Mujer",  "mujer3":  "Mujer",
}

# Rangos del filtro pasa-banda por genero (Hz)
BANDA = {
    "Hombre": (80,  400),
    "Mujer":  (150, 500),
}

# Umbrales clinicos
UMBRAL_JITTER            = 1.040   # %
UMBRAL_SHIMMER           = 3.08    # %
UMBRAL_SHIMMER_SOSPECHA  = 10.0    # % -> activar HNR
UMBRAL_HNR               = 7.0     # dB

DURACION_VENTANA = 0.150  # 150 milisegundos (~20-30 ciclos vocales)

os.makedirs(os.path.join(CARPETA_FIGS, "jitter_shimmer"), exist_ok=True)

# ============================================================
#  FUNCIONES
# ============================================================

def cargar_wav(nombre):
    ruta = os.path.join(CARPETA_AUDIO, f"{nombre}.wav")
    fs, data = wav.read(ruta)
    if data.ndim == 2:
        data = data.mean(axis=1)
    data = data.astype(np.float64)
    maximo = np.max(np.abs(data))
    if maximo > 0:
        data /= maximo
    return fs, data


def seleccionar_ventana_voz(senal, fs, duracion=15.0):
    """
    Selecciona la ventana de 'duracion' segundos con mayor energia RMS,
    que es donde hay mas voz activa.
    """
    n_muestras = int(duracion * fs)
    if len(senal) <= n_muestras:
        return senal, 0

    paso = int(0.1 * fs)  # deslizar cada 100 ms
    mejor_rms    = -1
    mejor_inicio = 0
    for inicio in range(0, len(senal) - n_muestras, paso):
        segmento = senal[inicio: inicio + n_muestras]
        rms = np.sqrt(np.mean(segmento ** 2))
        if rms > mejor_rms:
            mejor_rms    = rms
            mejor_inicio = inicio

    return senal[mejor_inicio: mejor_inicio + n_muestras], mejor_inicio


def aplicar_filtro_pasabanda(senal, fs, f_low, f_high):
    """Butterworth pasa-banda de orden 4."""
    nyq  = fs / 2
    low  = max(f_low  / nyq, 0.001)
    high = min(f_high / nyq, 0.999)
    b, a = butter(4, [low, high], btype='band')
    return filtfilt(b, a, senal)


def detectar_periodos(senal, fs):
    """
    Detecta periodos Ti entre cruces por cero ascendentes.
    Devuelve array de periodos en segundos.
    """
    indices_cruces = np.where((senal[:-1] < 0) & (senal[1:] >= 0))[0]
    if len(indices_cruces) < 2:
        return np.array([])
    periodos = np.diff(indices_cruces) / fs
    return periodos


def detectar_amplitudes(senal, fs):
    """
    Detecta la amplitud pico en cada ciclo vocal.
    Distancia minima entre picos equivalente a la frecuencia vocal maxima.
    """
    distancia_min = int(fs / 500)
    picos, _ = find_peaks(senal, distance=distancia_min, height=0)
    if len(picos) < 2:
        return np.array([])
    return senal[picos]


def calcular_jitter(periodos):
    """Jitter absoluto y relativo segun formulas de la guia."""
    N = len(periodos)
    if N < 2:
        return None, None
    jitter_abs = (1 / (N - 1)) * np.sum(np.abs(np.diff(periodos)))
    jitter_rel = (jitter_abs / np.mean(periodos)) * 100
    return jitter_abs, jitter_rel


def calcular_shimmer(amplitudes):
    """Shimmer absoluto y relativo segun formulas de la guia."""
    N = len(amplitudes)
    if N < 2:
        return None, None
    shimmer_abs = (1 / (N - 1)) * np.sum(np.abs(np.diff(amplitudes)))
    shimmer_rel = (shimmer_abs / np.mean(amplitudes)) * 100
    return shimmer_abs, shimmer_rel


def calcular_hnr(senal, fs):
    """
    Harmonic-to-Noise Ratio estimado por autocorrelacion.
    HNR = 10 * log10( r_max / (1 - r_max) )
    """
    N = len(senal)
    autocorr = np.correlate(senal, senal, mode='full')
    autocorr = autocorr[N - 1:]
    r0 = autocorr[0]
    if r0 == 0:
        return None
    autocorr_norm = autocorr / r0

    lag_min = max(1, int(fs / 600))
    lag_max = min(int(fs / 50), len(autocorr_norm) - 1)
    if lag_min >= lag_max:
        return None

    r_max = np.max(autocorr_norm[lag_min:lag_max])
    r_max = np.clip(r_max, 0.001, 0.999)
    hnr   = 10 * np.log10(r_max / (1 - r_max))
    return round(hnr, 2)


# ============================================================
#  PROCESAMIENTO PRINCIPAL
# ============================================================
print("\n" + "="*65)
print("  PARTE B - Jitter, Shimmer y HNR")
print("="*65)

resultados = {}

for nombre in NOMBRES:
    genero = GENEROS[nombre]
    ruta   = os.path.join(CARPETA_AUDIO, f"{nombre}.wav")
    if not os.path.exists(ruta):
        print(f"\n  [!] No se encontro {nombre}.wav - se omite.")
        continue

    fs, senal = cargar_wav(nombre)
    print(f"\n  Procesando {nombre} ({genero}) | fs = {fs} Hz | "
          f"duracion total = {len(senal)/fs:.1f} s")

    # 1. Ventana de 15 s con mayor energia
    ventana, inicio_ventana = seleccionar_ventana_voz(senal, fs, DURACION_VENTANA)
    t_inicio = inicio_ventana / fs
    print(f"    Ventana: {t_inicio*1000:.1f} ms -> {(t_inicio + len(ventana)/fs)*1000:.1f} ms  "
          f"({len(ventana)/fs*1000:.1f} ms, {len(ventana)} muestras)")

    # 2. Filtro pasa-banda
    f_low, f_high = BANDA[genero]
    senal_filt = aplicar_filtro_pasabanda(ventana, fs, f_low, f_high)
    print(f"    Filtro pasa-banda: {f_low}-{f_high} Hz")

    # 3-4. Periodos y amplitudes
    periodos   = detectar_periodos(senal_filt, fs)
    amplitudes = detectar_amplitudes(senal_filt, fs)
    print(f"    Ciclos detectados: {len(periodos)}  |  Picos de amplitud: {len(amplitudes)}")

    # 5. Jitter y Shimmer
    jitter_abs,  jitter_rel  = calcular_jitter(periodos)
    shimmer_abs, shimmer_rel = calcular_shimmer(amplitudes)

    # 6. HNR si shimmer es sospechoso
    hnr      = None
    usar_hnr = False
    if shimmer_rel is None or (shimmer_rel is not None and shimmer_rel > UMBRAL_SHIMMER_SOSPECHA):
        usar_hnr = True
        hnr = calcular_hnr(senal_filt, fs)
        if shimmer_rel is not None:
            print(f"    AVISO: Shimmer = {shimmer_rel:.2f}% > {UMBRAL_SHIMMER_SOSPECHA}% "
                  f"-> HNR calculado como indicador alternativo")
        else:
            print(f"    AVISO: Shimmer no calculable -> HNR como alternativo")

    resultados[nombre] = {
        "genero"      : genero,
        "fs"          : fs,
        "n_periodos"  : len(periodos),
        "n_picos"     : len(amplitudes),
        "jitter_abs"  : jitter_abs,
        "jitter_rel"  : jitter_rel,
        "shimmer_abs" : shimmer_abs,
        "shimmer_rel" : shimmer_rel,
        "hnr"         : hnr,
        "usar_hnr"    : usar_hnr,
        "senal_filt"  : senal_filt,
    }


# ============================================================
#  TABLA DE RESULTADOS EN CONSOLA
# ============================================================
print("\n\n" + "="*100)
print("  RESULTADOS - Jitter y Shimmer por grabacion")
print("="*100)
print(f"\n{'Señal':<10} {'Genero':<8} {'J_abs(s)':<13} {'J_rel(%)':<12} "
      f"{'Sh_abs':<13} {'Sh_rel(%)':<12} {'Estado J':<10} {'Estado Sh':<10} {'HNR(dB)'}")
print("-" * 100)

for nombre, r in resultados.items():
    j_rel  = r["jitter_rel"]
    sh_rel = r["shimmer_rel"]
    hnr    = r["hnr"]

    estado_j  = "NORMAL" if j_rel  is not None and j_rel  <= UMBRAL_JITTER  else ("PATOL." if j_rel  is not None else "N/D")
    estado_sh = "NORMAL" if sh_rel is not None and sh_rel <= UMBRAL_SHIMMER else ("PATOL." if sh_rel is not None else "N/D")

    ja  = f"{r['jitter_abs']:.6f}"  if r["jitter_abs"]  is not None else "N/D"
    jr  = f"{j_rel:.4f}"            if j_rel            is not None else "N/D"
    sha = f"{r['shimmer_abs']:.6f}" if r["shimmer_abs"] is not None else "N/D"
    shr = f"{sh_rel:.4f}"           if sh_rel           is not None else "N/D"
    hnr_s = f"{hnr:.2f}"            if hnr              is not None else "-"

    print(f"{nombre:<10} {r['genero']:<8} {ja:<13} {jr:<12} "
          f"{sha:<13} {shr:<12} {estado_j:<10} {estado_sh:<10} {hnr_s}")

print(f"\n  Umbrales de referencia (literatura clinica / PRAAT):")
print(f"    Jitter relativo  <= {UMBRAL_JITTER}%  -> normal")
print(f"    Shimmer relativo <= {UMBRAL_SHIMMER}%  -> normal")
print(f"    Shimmer > {UMBRAL_SHIMMER_SOSPECHA}%          -> posible mal microfono o ventana ruidosa")
print(f"    HNR              >= {UMBRAL_HNR} dB   -> voz sana")


# ============================================================
#  GRAFICA 1 — Señales filtradas con parametros en titulo
# ============================================================
COLORES = {"Hombre": "#2196F3", "Mujer": "#E91E63"}

fig, axes = plt.subplots(3, 2, figsize=(14, 10))
fig.suptitle("Señales filtradas — ventana 150 ms (Parte B)", fontsize=13, fontweight='bold')

for idx, (nombre, r) in enumerate(resultados.items()):
    fila  = idx // 2
    col   = idx % 2
    sf    = r["senal_filt"]
    fs_s  = r["fs"]
    t     = np.arange(len(sf)) / fs_s
    color = COLORES[r["genero"]]

    axes[fila, col].plot(t, sf, color=color, linewidth=0.6)
    jr  = f"J={r['jitter_rel']:.2f}%"  if r["jitter_rel"]  is not None else "J=N/D"
    shr = f"Sh={r['shimmer_rel']:.2f}%" if r["shimmer_rel"] is not None else "Sh=N/D"
    hnr_t = f"  HNR={r['hnr']:.1f}dB" if r["hnr"] is not None else ""
    axes[fila, col].set_title(f"{nombre}  |  {jr}  |  {shr}{hnr_t}", fontsize=8)
    axes[fila, col].set_xlabel("Tiempo (s)")
    axes[fila, col].set_ylabel("Amplitud")
    axes[fila, col].grid(True, alpha=0.3)

for idx in range(len(resultados), 6):
    axes[idx // 2, idx % 2].set_visible(False)

plt.tight_layout()
ruta_fig1 = os.path.join(CARPETA_FIGS, "jitter_shimmer", "señales_filtradas_parteB.png")
plt.savefig(ruta_fig1, dpi=150)
print(f"\n  Grafica guardada: {ruta_fig1}")
plt.show()


# ============================================================
#  GRAFICA 2 — Boxplots comparativos hombres vs. mujeres
# ============================================================
h_j  = [r["jitter_rel"]  for r in resultados.values() if r["genero"] == "Hombre" and r["jitter_rel"]  is not None]
m_j  = [r["jitter_rel"]  for r in resultados.values() if r["genero"] == "Mujer"  and r["jitter_rel"]  is not None]
h_sh = [r["shimmer_rel"] for r in resultados.values() if r["genero"] == "Hombre" and r["shimmer_rel"] is not None]
m_sh = [r["shimmer_rel"] for r in resultados.values() if r["genero"] == "Mujer"  and r["shimmer_rel"] is not None]

fig2, axes2 = plt.subplots(1, 2, figsize=(10, 5))
fig2.suptitle("Hombres vs. Mujeres — Jitter y Shimmer", fontsize=12, fontweight='bold')

for ax, datos_h, datos_m, etiqueta, umbral in zip(
        axes2,
        [h_j,  h_sh],
        [m_j,  m_sh],
        ["Jitter relativo (%)", "Shimmer relativo (%)"],
        [UMBRAL_JITTER, UMBRAL_SHIMMER]):

    bp = ax.boxplot([datos_h, datos_m], tick_labels=["Hombres", "Mujeres"],
                    patch_artist=True, widths=0.5)
    bp["boxes"][0].set_facecolor("#2196F3")
    bp["boxes"][1].set_facecolor("#E91E63")
    ax.axhline(umbral, color="red", linestyle="--", linewidth=1.2,
               label=f"Umbral = {umbral}%")
    ax.set_title(etiqueta)
    ax.set_ylabel("%")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
ruta_fig2 = os.path.join(CARPETA_FIGS, "jitter_shimmer", "boxplot_jitter_shimmer.png")
plt.savefig(ruta_fig2, dpi=150)
print(f"  Grafica guardada: {ruta_fig2}")
plt.show()

print("\n  Parte B completada.\n")