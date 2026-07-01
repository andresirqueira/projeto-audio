
import time
import json
import os
import pytesseract
import pyautogui
from datetime import datetime
import csv
from PIL import Image
import re
import unicodedata
from typing import Optional
import numpy as np
import sounddevice as sd

# --- CONFIGURAÇÕES ---
# Coordenadas da área dos participantes (ajuste se necessário)
X, Y, WIDTH, HEIGHT = 1450, 194, 437, 712
# Parâmetros de áudio
SAMPLE_RATE = 44100
# Intervalo entre registos e duração de cada análise (segundos) — RMS/Peak/SNR refletem este período
CAPTURE_INTERVAL = 1.0
NUM_SAMPLES = int(round(SAMPLE_RATE * CAPTURE_INTERVAL))
CSV_FILE = 'log_reuniao_unificado.csv'
SALAS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'salas_canonicas.json')

# --- DETECÇÃO DO DISPOSITIVO STEREO MIX/LOOPBACK ---
def get_stereo_mix_index():
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        name = dev['name'].lower()
        if dev['max_input_channels'] > 0 and (
            'stereo mix' in name or 'mixagem estéreo' in name or 'loopback' in name or 'what u hear' in name
        ):
            return idx
    # Fallback: segundo input se não encontrar
    input_indices = [idx for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
    if len(input_indices) > 1:
        return input_indices[1]
    elif input_indices:
        return input_indices[0]
    else:
        raise RuntimeError('Nenhum dispositivo de entrada de áudio encontrado!')

DEVICE_INDEX = get_stereo_mix_index()
_DISPOSITIVO_NOME = sd.query_devices(DEVICE_INDEX).get('name', '')

def snr_bandas(x, fs):
    """Razão dB entre energia espectral ~100–8000 Hz vs fora (proxy, não SNR ITU). Janela Hanning reduz vazamento."""
    n = len(x)
    if n < 4:
        return 0.0
    w = np.hanning(n)
    xw = x * w
    spectrum = np.abs(np.fft.rfft(xw))
    freqs = np.fft.rfftfreq(n, 1 / fs)
    # Sinal: energia entre 100 e 8000 Hz (voz/música)
    sinal_mask = (freqs > 100) & (freqs < 8000)
    sinal_power = np.sum(spectrum[sinal_mask] ** 2)
    # Ruído: energia fora dessa faixa
    ruido_mask = ~sinal_mask
    ruido_power = np.sum(spectrum[ruido_mask] ** 2)
    snr = 10 * np.log10((sinal_power + 1e-10) / (ruido_power + 1e-10))
    return snr

# --- FUNÇÕES DE ÁUDIO ---
def capturar_audio():
    audio = sd.rec(NUM_SAMPLES, samplerate=SAMPLE_RATE, channels=1, dtype='float32', device=DEVICE_INDEX)
    sd.wait()
    x = audio.flatten()
    n = int(x.shape[0])
    # Métricas sobre toda a janela NUM_SAMPLES (ex.: ~1 s a 44,1 kHz)
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    n_clip = int(np.sum(np.abs(x) > 0.99))
    clipping_pct = float(100.0 * n_clip / n) if n else 0.0
    snr = float(snr_bandas(x, SAMPLE_RATE))
    return rms, peak, n_clip, clipping_pct, snr

def diagnostico_audio(rms, snr, clipping_pct):
    if rms > 0.7:
        status = 'Muito alto'
    elif rms > 0.1:
        status = 'Bom'
    elif rms > 0.03:
        status = 'Baixo'
    else:
        status = 'Muito baixo'
    # ~1% das amostras acima de 0,99 ≈ alerta de clipping na janela
    if clipping_pct >= 1.0:
        status += ' (Clipping)'
    # Diagnóstico de ruído mais flexível e tolerante
    if rms < 0.01:
        status += ' (Silêncio)'
    else:
        if snr < 0:
            status += ' (Ruído moderado)'
        else:
            status += ' (Ruído baixo/OK)'
    return status

def _norm_sala(s: str) -> str:
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def carregar_regras_salas():
    if not os.path.isfile(SALAS_JSON):
        return []
    try:
        with open(SALAS_JSON, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('salas') or []
    except (json.JSONDecodeError, OSError):
        return []


REGRAS_SALAS = carregar_regras_salas()


def texto_para_nome_canonico(texto: str) -> Optional[str]:
    if not texto or not REGRAS_SALAS:
        return None
    n = _norm_sala(texto)
    for regra in REGRAS_SALAS:
        palavras = regra.get('todas_as_palavras') or []
        nome = regra.get('nome_canonico')
        if not nome or not palavras:
            continue
        if all(_norm_sala(p) in n for p in palavras):
            return nome
    return None


def normalizar_lista_participantes(nomes):
    """Junta variantes de OCR da mesma sala (regras em salas_canonicas.json)."""
    vistos = set()
    saida = []
    for nome in nomes:
        canon = texto_para_nome_canonico(nome)
        chave = canon or nome
        if chave not in vistos:
            vistos.add(chave)
            saida.append(canon if canon else nome)
    return sorted(saida)


# --- FUNÇÃO DE OCR ---
palavras_ignorar = [
    'add people', 'search for people', 'in the meeting', 'contributors',
    'meeting host', 'you', 'people'
]
def capturar_participantes():
    img = pyautogui.screenshot(region=(X, Y, WIDTH, HEIGHT))
    img = img.convert('L')
    texto = pytesseract.image_to_string(img, lang='eng')
    nomes = set()
    for linha in texto.split('\n'):
        linha = linha.strip()
        if (
            linha
            and re.search(r'[A-Za-zÀ-ÿ]{2,}', linha)
            and not any(palavra in linha.lower() for palavra in palavras_ignorar)
            and not re.fullmatch(r'[^A-Za-zÀ-ÿ]+', linha)
            and len(linha) > 2
        ):
            nomes.add(linha)
    return sorted(nomes)

# --- LOOP PRINCIPAL ---
print('Iniciando monitoramento unificado da reunião...')
print(f'Usando dispositivo de áudio índice {DEVICE_INDEX}: {_DISPOSITIVO_NOME or "(nome desconhecido)"}')
print(f'Cada linha do CSV: {NUM_SAMPLES / SAMPLE_RATE:.2f} s de áudio analisados; intervalo entre linhas ~{CAPTURE_INTERVAL:.1f} s.')
if REGRAS_SALAS:
    print(f'Regras de salas carregadas: {len(REGRAS_SALAS)} entrada(s) em {SALAS_JSON}')
else:
    print(f'Sem regras de salas (crie {os.path.basename(SALAS_JSON)} para normalizar nomes).')
print('Pressione Ctrl+C para parar e salvar o log.')

with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(
        ['Data/Hora', 'RMS', 'Peak', 'Clipping', 'Clipping_pct', 'SNR', 'Diagnóstico', 'Participantes']
    )
    try:
        while True:
            agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            rms, peak, n_clip, clipping_pct, snr = capturar_audio()
            status = diagnostico_audio(rms, snr, clipping_pct)
            participantes = normalizar_lista_participantes(capturar_participantes())
            if participantes:  # Só registra se houver pelo menos um participante
                writer.writerow(
                    [
                        agora,
                        f'{rms:.4f}',
                        f'{peak:.4f}',
                        n_clip,
                        f'{clipping_pct:.4f}',
                        f'{snr:.2f}',
                        status,
                        '; '.join(participantes),
                    ]
                )
                print(
                    f'{agora} | RMS: {rms:.4f} | clip%: {clipping_pct:.3f} | SNR: {snr:.2f} | {status} | Participantes: {participantes}'
                )
                f.flush()
            time.sleep(CAPTURE_INTERVAL)
    except KeyboardInterrupt:
        print('\nFinalizando e salvando log...')
        print(f'Log salvo em {CSV_FILE}') 