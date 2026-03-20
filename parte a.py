"""
PARTE A — Adquisición y análisis espectral de señales de voz
Procesamiento Digital de Señales — Ingeniería Biomédica, UMNG 2026-1

Pasos que cubre este script:
  3. Importar señales y graficarlas en el dominio del tiempo
  4. Calcular la FFT y graficar el espectro de magnitudes
  5. Extraer: F0, frecuencia media, brillo, intensidad (RMS)

Uso:
  Coloca los archivos .wav en la carpeta  audio/
  Luego ejecuta:  python parteA_adquisicion.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav

# ============================================================
#  CONFIGURACIÓN — ajusta aquí si cambias nombres o carpetas
# ============================================================
CARPETA_AUDIO  = r"C:\Users\amaya\Desktop\universidad\2026-1\procesamiento digital de señales\lab 3\auido"
CARPETA_FIGS   = r"C:\Users\amaya\Desktop\universidad\2026-1\procesamiento digital de señales\lab 3\figuras"
NOMBRES = [
    "hombre1", "hombre2", "hombre3",
    "mujer1",  "mujer2",  "mujer3",
]
GENEROS = {
    "hombre1": "Hombre", "hombre2": "Hombre", "hombre3": "Hombre",
    "mujer1":  "Mujer",  "mujer2":  "Mujer",  "mujer3":  "Mujer",
}
COLORES = {"Hombre": "#2196F3", "Mujer": "#E91E63"}

os.makedirs(CARPETA_AUDIO, exist_ok=True)
os.makedirs(os.path.join(CARPETA_FIGS, "dominio_tiempo"), exist_ok=True)
os.makedirs(os.path.join(CARPETA_FIGS, "espectros_fft"),  exist_ok=True)

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================

def cargar_wav(nombre):
    """Lee el .wav y devuelve (fs, señal normalizada float64)."""
    ruta = os.path.join(CARPETA_AUDIO, f"{nombre}.wav")
    fs, data = wav.read(ruta)
    # Convertir a mono si es estéreo
    if data.ndim == 2:
        data = data.mean(axis=1)
    # Normalizar a float en [-1, 1]
    data = data.astype(np.float64)
    data /= np.max(np.abs(data)) if np.max(np.abs(data)) > 0 else 1
    return fs, data


def calcular_f0(señal, fs, fmin=50, fmax=600):
    """
    Estima la frecuencia fundamental F0 por autocorrelación.
    fmin/fmax definen el rango de búsqueda (Hz).
    """
    N = len(señal)
    lag_min = int(fs / fmax)
    lag_max = int(fs / fmin)
    lag_max = min(lag_max, N - 1)

    # Autocorrelación normalizada
    autocorr = np.correlate(señal, señal, mode='full')
    autocorr = autocorr[N - 1:]          # solo lags positivos
    autocorr /= autocorr[0]              # normalizar

    # Buscar el pico máximo dentro del rango vocal
    segmento = autocorr[lag_min:lag_max]
    if len(segmento) == 0:
        return 0.0
    lag_pico = np.argmax(segmento) + lag_min
    f0 = fs / lag_pico if lag_pico > 0 else 0.0
    return round(f0, 2)


def calcular_caracteristicas(señal, fs):
    """
    Calcula F0, frecuencia media, brillo e intensidad (RMS).
    Devuelve un diccionario con los valores.
    """
    N = len(señal)

    # ── FFT ──────────────────────────────────────────────────
    Y       = np.fft.rfft(señal)
    freqs   = np.fft.rfftfreq(N, d=1/fs)
    magnitud = np.abs(Y)

    # ── F0 ───────────────────────────────────────────────────
    f0 = calcular_f0(señal, fs)

    # ── Frecuencia media (centroide espectral) ────────────────
    potencia      = magnitud ** 2
    suma_pot      = np.sum(potencia)
    if suma_pot > 0:
        freq_media = np.sum(freqs * potencia) / suma_pot
    else:
        freq_media = 0.0

    # ── Brillo (energía por encima de 1500 Hz relativa al total)
    mask_alto = freqs >= 1500
    brillo = np.sum(potencia[mask_alto]) / suma_pot if suma_pot > 0 else 0.0

    # ── Intensidad (RMS) ─────────────────────────────────────
    rms = np.sqrt(np.mean(señal ** 2))

    return {
        "F0 (Hz)"          : round(f0, 2),
        "Frec. media (Hz)" : round(freq_media, 2),
        "Brillo"           : round(brillo, 4),
        "Intensidad (RMS)" : round(rms, 6),
    }, freqs, magnitud


# ============================================================
#  PROCESAMIENTO PRINCIPAL
# ============================================================
resultados = {}
señales    = {}

print("\n" + "="*60)
print("  PARTE A — Análisis espectral de señales de voz")
print("="*60)

archivos_encontrados = []
for nombre in NOMBRES:
    ruta_wav = os.path.join(CARPETA_AUDIO, f"{nombre}.wav")
    if os.path.exists(ruta_wav):
        archivos_encontrados.append(nombre)
    else:
        print(f"\n  [!] No se encontró {nombre}.wav — se omite.")

if not archivos_encontrados:
    print("\n  No se encontraron archivos de audio. Coloca los .wav en la carpeta 'audio/' y vuelve a ejecutar.")

    exit()

print(f"\n  Archivos cargados: {len(archivos_encontrados)}/6\n")

for nombre in archivos_encontrados:
    fs, data = cargar_wav(nombre)
    señales[nombre] = (fs, data)
    caract, freqs, magnitud = calcular_caracteristicas(data, fs)
    resultados[nombre] = {"fs": fs, "N": len(data), **caract,
                          "freqs": freqs, "magnitud": magnitud}


# ============================================================
#  TABLA DE RESULTADOS EN CONSOLA
# ============================================================
print(f"\n{'Señal':<12} {'Género':<8} {'fs (Hz)':<10} {'F0 (Hz)':<10} "
      f"{'Frec.media (Hz)':<18} {'Brillo':<10} {'RMS':<12}")
print("-" * 80)
for nombre in archivos_encontrados:
    r = resultados[nombre]
    genero = GENEROS[nombre]
    print(f"{nombre:<12} {genero:<8} {r['fs']:<10} {r['F0 (Hz)']:<10} "
          f"{r['Frec. media (Hz)']:<18} {r['Brillo']:<10} {r['Intensidad (RMS)']:<12}")


# ============================================================
#  GRÁFICAS — DOMINIO DEL TIEMPO  (paso 3)
# ============================================================
fig, axes = plt.subplots(3, 2, figsize=(14, 10))
fig.suptitle("Señales de voz — Dominio del tiempo", fontsize=14, fontweight='bold')

for idx, nombre in enumerate(archivos_encontrados):
    fila = idx // 2
    col  = idx % 2
    fs, data = señales[nombre]
    t = np.arange(len(data)) / fs
    color = COLORES[GENEROS[nombre]]
    axes[fila, col].plot(t, data, color=color, linewidth=0.6)
    axes[fila, col].set_title(f"{nombre}  |  fs = {fs} Hz  |  {len(data)/fs:.1f} s",
                               fontsize=10)
    axes[fila, col].set_xlabel("Tiempo (s)")
    axes[fila, col].set_ylabel("Amplitud norm.")
    axes[fila, col].grid(True, alpha=0.3)

# Ocultar subplots vacíos si hay menos de 6 archivos
for idx in range(len(archivos_encontrados), 6):
    axes[idx // 2, idx % 2].set_visible(False)

plt.tight_layout()
ruta_tiempo = os.path.join(CARPETA_FIGS, "dominio_tiempo", "señales_tiempo.png")
plt.savefig(ruta_tiempo, dpi=150)
print(f"\n  ✓ Gráfica guardada: {ruta_tiempo}")
plt.show()


# ============================================================
#  GRÁFICAS — ESPECTROS FFT  (paso 4)
# ============================================================
fig, axes = plt.subplots(3, 2, figsize=(14, 10))
fig.suptitle("Espectros de magnitud — FFT", fontsize=14, fontweight='bold')

for idx, nombre in enumerate(archivos_encontrados):
    fila = idx // 2
    col  = idx % 2
    r     = resultados[nombre]
    freqs = r["freqs"]
    mag   = r["magnitud"]
    color = COLORES[GENEROS[nombre]]

    # Mostrar solo hasta 4000 Hz para mejor visualización
    mask = freqs <= 4000
    # Convertir a dB (escala logarítmica), evitar log(0) con clip
    mag_db = 20 * np.log10(np.clip(mag[mask], 1e-10, None))
    axes[fila, col].plot(freqs[mask], mag_db, color=color, linewidth=0.7)
    axes[fila, col].set_xscale('log')
    axes[fila, col].axvline(r["F0 (Hz)"], color="red", linestyle="--",
                             linewidth=1.2, label=f"F0 = {r['F0 (Hz)']} Hz")
    axes[fila, col].axvline(r["Frec. media (Hz)"], color="orange", linestyle="--",
                             linewidth=1.2,
                             label=f"Frec.media = {r['Frec. media (Hz)']:.0f} Hz")
    axes[fila, col].set_title(nombre, fontsize=10)
    axes[fila, col].set_xlabel("Frecuencia (Hz) — escala log")
    axes[fila, col].set_ylabel("Magnitud (dB)")
    axes[fila, col].legend(fontsize=7)
    axes[fila, col].grid(True, which='both', alpha=0.3)

for idx in range(len(archivos_encontrados), 6):
    axes[idx // 2, idx % 2].set_visible(False)

plt.tight_layout()
ruta_fft = os.path.join(CARPETA_FIGS, "espectros_fft", "espectros_magnitud.png")
plt.savefig(ruta_fft, dpi=150)
print(f"  ✓ Gráfica guardada: {ruta_fft}")
plt.show()

print("\n  Parte A completada.\n")