"""
Atualiza calibragem_salas.json a partir de CSV(s) gerados pelo monitor
(reunião + áudio padrão reproduzido na sala).

Uso:
  python salvar_calibragem.py --csv log_calibragem.csv --audio-referencia referencia.wav
  python salvar_calibragem.py --csv a.csv b.csv --audio-referencia ref.wav --volume-pc 50

Cada sala canónica presente no CSV recebe médias de RMS, Peak, Clipping_pct e SNR
(apenas linhas com Participantes que casem com salas_canonicas.json).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SALAS_JSON = os.path.join(BASE_DIR, 'salas_canonicas.json')
CALIBRAGEM_JSON = os.path.join(BASE_DIR, 'calibragem_salas.json')


def _norm_sala(s: str) -> str:
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def carregar_regras() -> list:
    if not os.path.isfile(SALAS_JSON):
        return []
    with open(SALAS_JSON, encoding='utf-8') as f:
        return json.load(f).get('salas') or []


def texto_para_nome_canonico(texto: str, regras: list) -> Optional[str]:
    if not texto or not regras:
        return None
    n = _norm_sala(texto)
    for regra in regras:
        palavras = regra.get('todas_as_palavras') or []
        nome = regra.get('nome_canonico')
        if not nome or not palavras:
            continue
        if all(_norm_sala(p) in n for p in palavras):
            return nome
    return None


def resolver_sala_linha(participantes: str, regras: list) -> Optional[str]:
    """Igual à ideia do dashboard: só segmentos que casam com alguma sala canónica."""
    if not participantes or not regras:
        return None
    parts = [p.strip() for p in participantes.split(';') if p.strip()]
    canon = set()
    for part in parts:
        c = texto_para_nome_canonico(part, regras)
        if c:
            canon.add(c)
    if not canon:
        return None
    if len(canon) == 1:
        return next(iter(canon))
    return ' + '.join(sorted(canon))


def _float(row: dict, key: str, default: Optional[float] = None) -> Optional[float]:
    v = row.get(key)
    if v is None or v == '':
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def clipping_pct_da_linha(row: dict) -> Optional[float]:
    v = _float(row, 'Clipping_pct')
    if v is not None:
        return v
    return None


def _parse_data_hora(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s[:19] if len(s) > 16 else s, fmt)
        except ValueError:
            continue
    return None


def duracao_seg_min_max_datas(datas: List[str]) -> Tuple[int, Optional[str], Optional[str]]:
    """Igual ao dashboard: último − primeiro timestamp (segundos)."""
    parsed = [_parse_data_hora(d) for d in datas]
    parsed = [p for p in parsed if p is not None]
    if len(parsed) < 2:
        if len(parsed) == 1:
            t = parsed[0].strftime('%Y-%m-%d %H:%M:%S')
            return 0, t, t
        return 0, None, None
    min_dt = min(parsed)
    max_dt = max(parsed)
    seg = int(round((max_dt - min_dt).total_seconds()))
    return seg, min_dt.strftime('%Y-%m-%d %H:%M:%S'), max_dt.strftime('%Y-%m-%d %H:%M:%S')


def agregar_csvs(paths: List[str], regras: list) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Retorna por sala canónica:
      linhas, somas rms/peak/snr/clip, datas
    """
    ac: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            'n': 0,
            'rms': 0.0,
            'peak': 0.0,
            'snr': 0.0,
            'clip_sum': 0.0,
            'clip_n': 0,
            'datas': [],
            'fontes': set(),
        }
    )
    erros: list[str] = []

    for path in paths:
        if not os.path.isfile(path):
            erros.append(f'Ficheiro inexistente: {path}')
            continue
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                erros.append(f'CSV vazio ou sem cabeçalho: {path}')
                continue
            for row in reader:
                if not row.get('Data/Hora'):
                    continue
                sala = resolver_sala_linha(row.get('Participantes') or '', regras)
                if not sala:
                    continue
                if ' + ' in sala:
                    erros.append(f'Linha com várias salas ignorada ({sala}): {path}')
                    continue
                rms = _float(row, 'RMS')
                peak = _float(row, 'Peak')
                snr = _float(row, 'SNR')
                if rms is None or peak is None or snr is None:
                    continue
                cp = clipping_pct_da_linha(row)
                b = ac[sala]
                b['n'] += 1
                b['rms'] += rms
                b['peak'] += peak
                b['snr'] += snr
                b['datas'].append(row['Data/Hora'])
                b['fontes'].add(os.path.basename(path))
                if cp is not None:
                    b['clip_sum'] += cp
                    b['clip_n'] += 1

    out: dict[str, dict[str, Any]] = {}
    for sala, b in ac.items():
        if b['n'] == 0:
            continue
        clip_med = (b['clip_sum'] / b['clip_n']) if b['clip_n'] else None
        duracao_seg, data_inicio, data_fim = duracao_seg_min_max_datas(b['datas'])
        out[sala] = {
            'data_calibragem': data_fim or (max(b['datas']) if b['datas'] else datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'duracao_seg': duracao_seg,
            'fonte_csv': '; '.join(sorted(b['fontes'])),
            'n_linhas': b['n'],
            'rms_medio': round(b['rms'] / b['n'], 6),
            'peak_medio': round(b['peak'] / b['n'], 6),
            'snr_medio': round(b['snr'] / b['n'], 4),
            'clipping_pct_medio': None if clip_med is None else round(clip_med, 6),
        }
    return out, erros


def main() -> None:
    p = argparse.ArgumentParser(description='Grava médias por sala em calibragem_salas.json')
    p.add_argument('--csv', nargs='+', required=True, help='Um ou mais CSV do monitor')
    p.add_argument('--audio-referencia', required=True, help='Nome do ficheiro de áudio padrão usado nas salas')
    p.add_argument('--volume-pc', type=int, default=None, help='Percentagem de volume do Windows (opcional)')
    p.add_argument('--output', default=CALIBRAGEM_JSON, help='Caminho do JSON de saída')
    args = p.parse_args()

    regras = carregar_regras()
    if not regras:
        raise SystemExit(f'Não foi possível carregar regras em {SALAS_JSON}')

    novos, erros = agregar_csvs(args.csv, regras)
    if not novos:
        raise SystemExit('Nenhuma linha válida por sala canónica. Verifique OCR/Participantes e salas_canonicas.json.')

    if os.path.isfile(args.output):
        with open(args.output, encoding='utf-8') as f:
            atual = json.load(f)
    else:
        atual = {'salas': {}}

    salas = atual.get('salas') or {}
    if not isinstance(salas, dict):
        salas = {}

    for sala, ref in novos.items():
        salas[sala] = ref

    atual['salas'] = salas
    atual['audio_referencia_arquivo'] = args.audio_referencia
    if args.volume_pc is not None:
        atual['volume_pc_percent'] = args.volume_pc
    atual['ultima_atualizacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if 'notas' not in atual:
        atual['notas'] = ''

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)

    print(f'Gravado: {args.output}')
    for sala, ref in sorted(novos.items()):
        print(
            f'  {sala}: n={ref["n_linhas"]} duracao={ref.get("duracao_seg", 0)}s '
            f'RMS={ref["rms_medio"]} Peak={ref["peak_medio"]} SNR={ref["snr_medio"]}'
        )
    for e in erros:
        print('Aviso:', e)


if __name__ == '__main__':
    main()
