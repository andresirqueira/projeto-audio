#!/usr/bin/env python3
"""
Script de teste para verificar dispositivos de áudio
"""

import sounddevice as sd
import numpy as np
import time

def list_audio_devices():
    """Listar todos os dispositivos de áudio disponíveis"""
    print("=== DISPOSITIVOS DE ÁUDIO DISPONÍVEIS ===")
    devices = sd.query_devices()
    
    print("\n📥 DISPOSITIVOS DE ENTRADA:")
    input_devices = []
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append(idx)
            print(f"  {idx}: {dev['name']}")
            print(f"     - Canais: {dev['max_input_channels']}")
            print(f"     - Sample Rate: {dev['default_samplerate']} Hz")
            print(f"     - Padrão: {'Sim' if dev['name'] == sd.default.device[0] else 'Não'}")
            print()
    
    print("\n📤 DISPOSITIVOS DE SAÍDA:")
    for idx, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            print(f"  {idx}: {dev['name']}")
            print(f"     - Canais: {dev['max_output_channels']}")
            print(f"     - Sample Rate: {dev['default_samplerate']} Hz")
            print(f"     - Padrão: {'Sim' if dev['name'] == sd.default.device[1] else 'Não'}")
            print()
    
    return input_devices

def test_device(device_idx, duration=3):
    """Testar um dispositivo específico"""
    print(f"\n=== TESTANDO DISPOSITIVO {device_idx} ===")
    
    try:
        # Configurar stream
        stream = sd.InputStream(
            device=device_idx,
            channels=1,
            samplerate=44100,
            blocksize=1024,
            callback=None
        )
        
        print("🎵 Gravando áudio por 3 segundos...")
        print("   (Faça algum som ou reproduza áudio)")
        
        # Gravar áudio
        recording = sd.rec(int(duration * 44100), samplerate=44100, channels=1, device=device_idx)
        sd.wait()
        
        # Analisar áudio
        rms = np.sqrt(np.mean(recording ** 2))
        peak = np.max(np.abs(recording))
        
        print(f"📊 Resultados:")
        print(f"   - RMS: {rms:.6f}")
        print(f"   - Peak: {peak:.6f}")
        
        if rms > 0.001:
            print("✅ Áudio detectado! Dispositivo funcionando.")
        else:
            print("⚠️ Sem áudio detectado. Verifique se há som sendo reproduzido.")
        
        stream.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def main():
    print("🎵 TESTE DE DISPOSITIVOS DE ÁUDIO")
    print("=" * 40)
    
    # Listar dispositivos
    input_devices = list_audio_devices()
    
    if not input_devices:
        print("❌ Nenhum dispositivo de entrada encontrado!")
        return
    
    # Testar cada dispositivo
    print("\n=== TESTANDO DISPOSITIVOS ===")
    working_devices = []
    
    for device_idx in input_devices:
        if test_device(device_idx):
            working_devices.append(device_idx)
        print("-" * 30)
    
    # Resumo
    print(f"\n📋 RESUMO:")
    print(f"   - Dispositivos encontrados: {len(input_devices)}")
    print(f"   - Dispositivos funcionando: {len(working_devices)}")
    
    if working_devices:
        print(f"   - Dispositivos OK: {working_devices}")
        print("\n✅ Você pode usar qualquer um desses dispositivos no analisador!")
    else:
        print("\n❌ Nenhum dispositivo funcionando. Verifique as configurações de áudio.")

if __name__ == "__main__":
    main()
