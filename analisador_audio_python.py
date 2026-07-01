import sys
import os
import numpy as np
import sounddevice as sd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QComboBox, 
                             QMessageBox, QScrollArea, QCheckBox, QHBoxLayout, QGroupBox, QPushButton,
                             QTextEdit, QGridLayout, QFrame, QSpinBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import scipy.signal
from datetime import datetime
import csv

# Configurações de áudio
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048
SILENCE_THRESHOLD = 0.01
CLIPPING_THRESHOLD = 0.99
HISTORY_LEN = 300

class AudioAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle('Analisador de Qualidade de Audio')
        self.setGeometry(100, 100, 1400, 1000)
        
        # Configurar estilo
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
                         QComboBox {
                 background-color: #3c3c3c;
                 border: 1px solid #555;
                 color: white;
                 padding: 5px;
                 border-radius: 3px;
             }
             QSpinBox {
                 background-color: #3c3c3c;
                 border: 1px solid #555;
                 color: white;
                 padding: 5px;
                 border-radius: 3px;
                 min-width: 60px;
             }
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        # Variáveis de controle
        self.is_recording = False
        self.audio_buffer = np.zeros(BLOCK_SIZE)
        self.stream = None
        
        # Históricos
        self.rms_history = []
        self.peak_history = []
        self.clip_history = []
        self.snr_history = []
        self.silence_history = []
        self.pitch_history = []
        self.crest_history = []
        self.thd_history = []
        self.dynamic_range_history = []
        self.spectral_centroid_history = []
        
        # Métricas de média móvel (para dados mais sólidos)
        self.rms_avg_history = []
        self.peak_avg_history = []
        self.snr_avg_history = []
        self.thd_avg_history = []
        self.noise_floor_history = []
        self.avg_window = 10  # Janela de 10 amostras para média móvel
        
        self.setup_ui()
        self.detect_devices()
        if self.mic_index is not None:
            self.start_stream(0)  # Começa com microfone

        # Timer para atualização da UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Atualizar mais frequentemente para gráficos em tempo real

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Painel de controle
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Métricas em tempo real
        metrics_panel = self.create_metrics_panel()
        main_layout.addWidget(metrics_panel)
        
        # Gráficos
        graphs_panel = self.create_graphs_panel()
        main_layout.addWidget(graphs_panel)
        
        central_widget.setLayout(main_layout)

    def create_control_panel(self):
        group = QGroupBox("🎛️ Controles")
        layout = QHBoxLayout()
        
        # Seletor de dispositivo
        self.device_box = QComboBox()
        self.populate_device_list()
        self.device_box.currentIndexChanged.connect(self.change_device)
        
        # Botões
        self.start_btn = QPushButton("▶️ Iniciar Análise")
        self.start_btn.clicked.connect(self.toggle_recording)
        
        self.test_btn = QPushButton("🔧 Testar Dispositivo")
        self.test_btn.clicked.connect(self.test_device)
        
        self.info_btn = QPushButton("ℹ️ Info Dispositivo")
        self.info_btn.clicked.connect(self.show_device_info)
        
        self.save_btn = QPushButton("💾 Salvar Dados")
        self.save_btn.clicked.connect(self.save_data)
        
        # Controle de janela de média
        self.avg_label = QLabel("Janela Média:")
        self.avg_spinbox = QSpinBox()
        self.avg_spinbox.setRange(5, 50)
        self.avg_spinbox.setValue(10)
        self.avg_spinbox.valueChanged.connect(self.change_avg_window)
        
        self.clear_stats_btn = QPushButton("🗑️ Limpar Estatísticas")
        self.clear_stats_btn.clicked.connect(self.clear_statistics)
        
        self.restart_btn = QPushButton("🔄 Reiniciar App")
        self.restart_btn.clicked.connect(self.restart_application)
        
        layout.addWidget(QLabel("Dispositivo:"))
        layout.addWidget(self.device_box)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.test_btn)
        layout.addWidget(self.info_btn)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.avg_label)
        layout.addWidget(self.avg_spinbox)
        layout.addWidget(self.clear_stats_btn)
        layout.addWidget(self.restart_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group

    def create_metrics_panel(self):
        group = QGroupBox("📊 Métricas em Tempo Real")
        layout = QGridLayout()
        
        # Métricas principais
        self.label_rms = QLabel('RMS: 0.0000')
        self.label_peak = QLabel('Peak: 0.0000')
        self.label_crest = QLabel('Crest Factor: 0.00')
        self.label_clipping = QLabel('Clipping: 0')
        self.label_snr = QLabel('SNR: 0.00 dB')
        self.label_thd = QLabel('THD: 0.00%')
        
        # Métricas de média total
        self.label_rms_avg = QLabel('RMS (Média Total): 0.0000')
        self.label_peak_avg = QLabel('Peak (Média Total): 0.0000')
        self.label_snr_avg = QLabel('SNR (Média Total): 0.00 dB')
        self.label_thd_avg = QLabel('THD (Média Total): 0.00%')
        
        # Estatísticas adicionais
        self.label_rms_max = QLabel('RMS (Max): 0.0000')
        self.label_rms_min = QLabel('RMS (Min): 0.0000')
        self.label_snr_max = QLabel('SNR (Max): 0.00 dB')
        self.label_snr_min = QLabel('SNR (Min): 0.00 dB')
        
        # Métricas avançadas
        self.label_pitch = QLabel('Pitch: -- Hz')
        self.label_dynamic_range = QLabel('Dynamic Range: 0 dB')
        self.label_spectral_centroid = QLabel('Spectral Centroid: 0 Hz')
        self.label_silence = QLabel('Silêncio: 0%')
        self.label_noise_floor = QLabel('Noise Floor: 0.0000')
        
        # Diagnóstico
        self.label_diagnosis = QLabel('Diagnostico: Aguardando audio...')
        self.label_diagnosis.setStyleSheet("font-weight: bold; color: #FFD700;")
        
        # Nota de qualidade
        self.label_grade = QLabel('Nota: --')
        self.label_grade.setStyleSheet("font-weight: bold; font-size: 16px; color: #FFD700;")
        
        # Mensagem temporária
        self.label_message = QLabel('')
        self.label_message.setStyleSheet("font-weight: bold; color: #00FF00; font-size: 14px;")
        self.label_message.setAlignment(Qt.AlignCenter)
        
        # Layout das métricas
        layout.addWidget(QLabel("🎵 Volume:"), 0, 0)
        layout.addWidget(self.label_rms, 0, 1)
        layout.addWidget(self.label_peak, 0, 2)
        layout.addWidget(self.label_crest, 0, 3)
        
        layout.addWidget(QLabel("⚠️ Qualidade:"), 1, 0)
        layout.addWidget(self.label_clipping, 1, 1)
        layout.addWidget(self.label_snr, 1, 2)
        layout.addWidget(self.label_thd, 1, 3)
        
        layout.addWidget(QLabel("📊 Médias Totais:"), 2, 0)
        layout.addWidget(self.label_rms_avg, 2, 1)
        layout.addWidget(self.label_peak_avg, 2, 2)
        layout.addWidget(self.label_snr_avg, 2, 3)
        
        layout.addWidget(QLabel("📈 Estatísticas:"), 3, 0)
        layout.addWidget(self.label_thd_avg, 3, 1)
        layout.addWidget(self.label_silence, 3, 2)
        layout.addWidget(self.label_noise_floor, 3, 3)
        
        layout.addWidget(QLabel("📊 Extremos:"), 4, 0)
        layout.addWidget(self.label_rms_max, 4, 1)
        layout.addWidget(self.label_rms_min, 4, 2)
        layout.addWidget(self.label_snr_max, 4, 3)
        
        layout.addWidget(QLabel("📉 Variação:"), 5, 0)
        layout.addWidget(self.label_snr_min, 5, 1)
        layout.addWidget(QLabel(""), 5, 2)  # Espaço vazio
        layout.addWidget(QLabel(""), 5, 3)  # Espaço vazio
        
        layout.addWidget(QLabel("🎼 Características:"), 6, 0)
        layout.addWidget(self.label_pitch, 6, 1)
        layout.addWidget(self.label_dynamic_range, 6, 2)
        layout.addWidget(self.label_spectral_centroid, 6, 3)
        
        layout.addWidget(QLabel("🔇 Diagnostico:"), 7, 0)
        layout.addWidget(self.label_diagnosis, 7, 1, 1, 2)
        layout.addWidget(self.label_grade, 7, 3)
        
        # Mensagem temporária
        layout.addWidget(self.label_message, 8, 0, 1, 4)
        
        group.setLayout(layout)
        return group

    def create_graphs_panel(self):
        group = QGroupBox("📈 Gráficos e Análise")
        layout = QVBoxLayout()
        
        # Checkboxes para mostrar/ocultar gráficos
        checkbox_layout = QHBoxLayout()
        self.metric_names = ['RMS', 'Peak', 'Crest', 'Clipping', 'SNR', 'THD', 'Pitch', 'Dynamic Range']
        self.metric_checkboxes = []
        
        for name in self.metric_names:
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_graph_visibility)
            self.metric_checkboxes.append(cb)
            checkbox_layout.addWidget(cb)
        
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)
        
        # Gráficos
        self.fig, axes = plt.subplots(9, 1, figsize=(16, 20), 
                                     gridspec_kw={'height_ratios': [1,1,1,1,1,1,1,1,2]})
        self.fig.patch.set_facecolor('#2b2b2b')
        
        # Configurar eixos
        self.axes = []
        self.lines = []
        
        titles = ['RMS', 'Peak', 'Crest Factor', 'Clipping', 'SNR', 'THD', 'Pitch', 'Dynamic Range', 'Espectro']
        ylabels = ['RMS', 'Peak', 'Crest', 'Clipping', 'SNR (dB)', 'THD (%)', 'Pitch (Hz)', 'Dynamic Range (dB)', 'Amplitude']
        ylims = [(0, 1), (0, 1), (0, 20), (0, BLOCK_SIZE), (0, 60), (0, 10), (0, 1000), (0, 100), (0, 1)]
        
        for i, (ax, title, ylabel, ylim) in enumerate(zip(axes, titles, ylabels, ylims)):
            ax.set_facecolor('#3c3c3c')
            ax.set_title(title, color='white', fontsize=10)
            ax.set_ylabel(ylabel, color='white', fontsize=8)
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(ylim)
            
            if i < 8:  # Linhas de tempo
                line, = ax.plot([], [], lw=1, color=f'C{i}')
                self.lines.append(line)
            else:  # Espectro
                line, = ax.plot([], [], lw=1, color='cyan')
                self.lines.append(line)
                ax.set_xlabel('Frequência (Hz)', color='white', fontsize=8)
                ax.set_xlim(0, SAMPLE_RATE/2)
            
            self.axes.append(ax)
        
        # Canvas com scroll
        self.canvas = FigureCanvas(self.fig)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll)
        
        group.setLayout(layout)
        return group

    def detect_devices(self):
        devices = sd.query_devices()
        self.mic_index = None
        self.stereo_index = None
        
        print("Dispositivos de áudio encontrados:")
        for idx, dev in enumerate(devices):
            name = dev['name'].lower()
            print(f"  {idx}: {dev['name']} (inputs: {dev['max_input_channels']})")
            
            if dev['max_input_channels'] > 0:
                # Detectar microfone
                if self.mic_index is None and ('mic' in name or 'microfone' in name or 'input' in name):
                    self.mic_index = idx
                    print(f"    -> Microfone detectado: {dev['name']}")
                # Detectar áudio do sistema
                if self.stereo_index is None and ('stereo mix' in name or 'mixagem estéreo' in name or 
                                                 'loopback' in name or 'what u hear' in name or 'cable' in name):
                    self.stereo_index = idx
                    print(f"    -> Áudio do sistema detectado: {dev['name']}")
        
        # Fallback - primeiro input disponível
        if self.mic_index is None:
            self.mic_index = next((idx for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0), None)
            if self.mic_index is not None:
                print(f"    -> Microfone fallback: {devices[self.mic_index]['name']}")
        
        # Fallback - segundo input disponível (se diferente do microfone)
        if self.stereo_index is None:
            input_indices = [idx for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
            if len(input_indices) > 1:
                self.stereo_index = input_indices[1]
                print(f"    -> Áudio do sistema fallback: {devices[self.stereo_index]['name']}")
        
        print(f"Microfone selecionado: {self.mic_index}")
        print(f"Áudio do sistema selecionado: {self.stereo_index}")
        
        if self.stereo_index is None:
            self.show_message('Dispositivo de audio do sistema nao encontrado.')

    def start_stream(self, option_idx):
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        # Obter lista de dispositivos de entrada
        devices = sd.query_devices()
        input_devices = [idx for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
        
        if option_idx >= len(input_devices):
            self.show_message('Indice de dispositivo invalido.')
            return
        
        device = input_devices[option_idx]
        
        if device is None:
            self.show_message('Dispositivo nao disponivel.')
            return
        
        try:
            print(f"Iniciando stream com dispositivo {device}")
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=BLOCK_SIZE,
                device=device,
                callback=self.audio_callback
            )
            self.stream.start()
            print(f"Stream iniciado com sucesso no dispositivo {device}")
        except Exception as e:
            print(f"Erro ao iniciar stream: {str(e)}")
            self.show_message(f'Erro ao iniciar stream: {str(e)}')

    def change_avg_window(self, value):
        """Mudar o tamanho da janela de média móvel"""
        self.avg_window = value
        print(f"Janela de média alterada para: {value} amostras")

    def change_device(self, idx):
        self.start_stream(idx)
        self.clear_histories()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        self.audio_buffer = indata[:, 0]
        # Debug: verificar se há dados de áudio
        if np.max(np.abs(self.audio_buffer)) > 0.001:
            print(f"Áudio detectado: RMS={np.sqrt(np.mean(self.audio_buffer**2)):.4f}")

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.start_btn.setText("⏹️ Parar Análise")
            self.start_btn.setStyleSheet("background-color: #f44336;")
        else:
            self.is_recording = False
            self.start_btn.setText("▶️ Iniciar Análise")
            self.start_btn.setStyleSheet("background-color: #4CAF50;")

    def show_device_info(self):
        """Mostrar informações do dispositivo selecionado"""
        try:
            current_idx = self.device_box.currentIndex()
            if current_idx < 0:
                self.show_message('Nenhum dispositivo selecionado.')
                return
            
            devices = sd.query_devices()
            input_devices = [idx for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
            
            if current_idx >= len(input_devices):
                self.show_message('Dispositivo invalido.')
                return
            
            device_idx = input_devices[current_idx]
            device = devices[device_idx]
            
            info_text = f"Dispositivo: {device['name']} | Indice: {device_idx} | Canais: {device['max_input_channels']}"
            self.show_message(info_text)
        except Exception as e:
            self.show_message(f'Erro ao obter informacoes: {str(e)}')

    def test_device(self):
        try:
            # Teste rápido de captura
            duration = 1  # 1 segundo
            recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
            sd.wait()
            
            rms = np.sqrt(np.mean(recording ** 2))
            if rms > 0.001:
                self.show_message(f'Dispositivo funcionando! RMS: {rms:.4f}')
            else:
                self.show_message('Dispositivo funcionando, mas nenhum audio detectado.')
        except Exception as e:
            self.show_message(f'Erro no teste: {str(e)}')

    def save_data(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analise_audio_{timestamp}.csv"
            
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Timestamp', 'RMS', 'Peak', 'Crest', 'Clipping', 'SNR', 'THD', 'Pitch', 'Dynamic Range'])
                
                for i in range(len(self.rms_history)):
                    writer.writerow([
                        i * 0.1,  # Timestamp em segundos
                        self.rms_history[i] if i < len(self.rms_history) else 0,
                        self.peak_history[i] if i < len(self.peak_history) else 0,
                        self.crest_history[i] if i < len(self.crest_history) else 0,
                        self.clip_history[i] if i < len(self.clip_history) else 0,
                        self.snr_history[i] if i < len(self.snr_history) else 0,
                        self.thd_history[i] if i < len(self.thd_history) else 0,
                        self.pitch_history[i] if i < len(self.pitch_history) else 0,
                        self.dynamic_range_history[i] if i < len(self.dynamic_range_history) else 0
                    ])
            
            self.show_message(f'Dados salvos em {filename}')
        except Exception as e:
            self.show_message(f'Erro ao salvar: {str(e)}')

    def clear_histories(self):
        self.rms_history = []
        self.peak_history = []
        self.clip_history = []
        self.snr_history = []
        self.silence_history = []
        self.pitch_history = []
        self.crest_history = []
        self.thd_history = []
        self.dynamic_range_history = []
        self.spectral_centroid_history = []
        
        # Limpar também as médias móveis
        self.rms_avg_history = []
        self.peak_avg_history = []
        self.snr_avg_history = []
        self.thd_avg_history = []
        self.noise_floor_history = []

    def show_message(self, message, duration=3000):
        """Mostrar mensagem temporária na interface"""
        self.label_message.setText(message)
        self.label_message.setStyleSheet("font-weight: bold; color: #00FF00; font-size: 14px;")
        
        # Timer para ocultar a mensagem
        QTimer.singleShot(duration, lambda: self.label_message.setText(''))

    def clear_statistics(self):
        """Limpar todas as estatísticas e históricos"""
        self.clear_histories()
        self.show_message('Todas as estatisticas foram limpas!')

    def restart_application(self):
        """Reiniciar completamente o aplicativo"""
        self.show_message('Reiniciando aplicativo...')
        
        # Parar análise se estiver rodando
        if self.is_recording:
            self.toggle_recording()
            # Parar análise se estiver rodando
            if self.is_recording:
                self.toggle_recording()
            
            # Limpar todos os históricos
            self.clear_histories()
            
            # Resetar todas as labels
            self.label_rms.setText('RMS: 0.0000')
            self.label_peak.setText('Peak: 0.0000')
            self.label_crest.setText('Crest Factor: 0.00')
            self.label_clipping.setText('Clipping: 0')
            self.label_snr.setText('SNR: 0.00 dB')
            self.label_thd.setText('THD: 0.00%')
            self.label_pitch.setText('Pitch: -- Hz')
            self.label_dynamic_range.setText('Dynamic Range: 0 dB')
            self.label_spectral_centroid.setText('Spectral Centroid: 0 Hz')
            self.label_silence.setText('Silencio: 0%')
            self.label_noise_floor.setText('Noise Floor: 0.0000')
            
            # Resetar médias totais
            self.label_rms_avg.setText('RMS (Média Total): 0.0000')
            self.label_peak_avg.setText('Peak (Média Total): 0.0000')
            self.label_snr_avg.setText('SNR (Média Total): 0.00 dB')
            self.label_thd_avg.setText('THD (Média Total): 0.00%')
            
            # Resetar estatísticas
            self.label_rms_max.setText('RMS (Max): 0.0000')
            self.label_rms_min.setText('RMS (Min): 0.0000')
            self.label_snr_max.setText('SNR (Max): 0.00 dB')
            self.label_snr_min.setText('SNR (Min): 0.00 dB')
            
            # Resetar diagnóstico e nota
            self.label_diagnosis.setText('Diagnostico: Aguardando audio...')
            self.label_grade.setText('Nota: --')
            self.label_grade.setStyleSheet("font-weight: bold; font-size: 16px; color: #FFD700;")
            
            # Limpar gráficos
            for line in self.lines:
                line.set_data([], [])
            
            # Forçar atualização dos gráficos
            self.canvas.draw()
            
            # Resetar janela de média
            self.avg_spinbox.setValue(10)
            self.avg_window = 10
            
            self.show_message('Aplicativo reiniciado com sucesso!')

    def update_graph_visibility(self):
        for i, cb in enumerate(self.metric_checkboxes):
            if i < len(self.axes) - 1:  # Exceto o último (espectro)
                self.axes[i].set_visible(cb.isChecked())
        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()

    def update_ui(self):
        if not self.is_recording:
            return
            
        x = self.audio_buffer
        
        # Debug: verificar se há dados
        if len(x) == 0 or np.all(x == 0):
            return
        
        # Calcular métricas
        rms = np.sqrt(np.mean(x ** 2))
        peak = np.max(np.abs(x))
        crest_factor = peak / (rms + 1e-10)
        clipping = np.sum(np.abs(x) > CLIPPING_THRESHOLD)
        
        # SNR - Método melhorado
        signal_power = np.mean(x ** 2)
        
        # Detectar ruído de fundo usando regiões de silêncio
        silence_threshold = 0.02  # Limiar para considerar silêncio
        silent_samples = x[np.abs(x) < silence_threshold]
        
        if len(silent_samples) > 10:  # Precisa de amostras suficientes
            noise_power = np.mean(silent_samples ** 2)
        else:
            # Fallback: estimar ruído usando o menor 10% das amplitudes
            sorted_amplitudes = np.sort(np.abs(x))
            noise_samples = sorted_amplitudes[:len(sorted_amplitudes)//10]
            noise_power = np.mean(noise_samples ** 2)
        
        snr = 10 * np.log10(signal_power / (noise_power + 1e-10)) if noise_power > 0 else 60
        noise_floor = np.sqrt(noise_power)  # RMS do ruído
        
        # THD (simplificado)
        thd = self.calculate_thd(x)
        
        # Pitch
        pitch = self.detect_pitch(x, SAMPLE_RATE) if rms > 0.01 else None
        
        # Dynamic Range
        dynamic_range = 20 * np.log10(peak / (rms + 1e-10))
        
        # Spectral Centroid
        spectral_centroid = self.calculate_spectral_centroid(x, SAMPLE_RATE)
        
        # Silêncio
        silence_pct = np.mean(np.abs(x) < SILENCE_THRESHOLD) * 100
        
        # Atualizar labels
        self.label_rms.setText(f'RMS: {rms:.4f}')
        self.label_peak.setText(f'Peak: {peak:.4f}')
        self.label_crest.setText(f'Crest Factor: {crest_factor:.2f}')
        self.label_clipping.setText(f'Clipping: {clipping}')
        self.label_snr.setText(f'SNR: {snr:.2f} dB')
        self.label_thd.setText(f'THD: {thd:.2f}%')
        self.label_pitch.setText(f'Pitch: {pitch:.1f} Hz' if pitch else 'Pitch: -- Hz')
        self.label_dynamic_range.setText(f'Dynamic Range: {dynamic_range:.1f} dB')
        self.label_spectral_centroid.setText(f'Spectral Centroid: {spectral_centroid:.0f} Hz')
        self.label_silence.setText(f'Silencio: {silence_pct:.1f}%')
        self.label_noise_floor.setText(f'Noise Floor: {noise_floor:.4f}')
        
        # Calcular médias desde o início da medição
        rms_avg = self.calculate_total_average(self.rms_history)
        peak_avg = self.calculate_total_average(self.peak_history)
        snr_avg = self.calculate_total_average(self.snr_history)
        thd_avg = self.calculate_total_average(self.thd_history)
        noise_floor_avg = self.calculate_total_average(self.noise_floor_history)
        
        self.label_rms_avg.setText(f'RMS (Média Total): {rms_avg:.4f}')
        self.label_peak_avg.setText(f'Peak (Média Total): {peak_avg:.4f}')
        self.label_snr_avg.setText(f'SNR (Média Total): {snr_avg:.2f} dB')
        self.label_thd_avg.setText(f'THD (Média Total): {thd_avg:.2f}%')
        
        # Calcular e mostrar nota de qualidade
        grade, color = self.calculate_audio_grade(rms_avg, snr_avg, thd_avg, noise_floor_avg)
        self.label_grade.setText(f'Nota: {grade}')
        self.label_grade.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {color};")
        
        # Calcular estatísticas adicionais
        if len(self.rms_history) > 0:
            rms_max = np.max(self.rms_history)
            rms_min = np.min(self.rms_history)
            snr_max = np.max(self.snr_history)
            snr_min = np.min(self.snr_history)
            
            self.label_rms_max.setText(f'RMS (Max): {rms_max:.4f}')
            self.label_rms_min.setText(f'RMS (Min): {rms_min:.4f}')
            self.label_snr_max.setText(f'SNR (Max): {snr_max:.2f} dB')
            self.label_snr_min.setText(f'SNR (Min): {snr_min:.2f} dB')
        
        # Diagnóstico
        diagnosis = self.get_diagnosis(rms, peak, clipping, snr, pitch, silence_pct, noise_floor)
        self.label_diagnosis.setText(f'Diagnostico: {diagnosis}')
        
        # Atualizar históricos
        self.update_histories(rms, peak, crest_factor, clipping, snr, thd, pitch, dynamic_range, spectral_centroid, noise_floor)
        
        # Atualizar gráficos
        self.update_graphs()
        
        # Atualizar espectro
        self.update_spectrum(x)

    def calculate_thd(self, x):
        # THD simplificado baseado na relação harmônicos/fundamental
        if len(x) < 1024:
            return 0
        
        # FFT
        spectrum = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1/SAMPLE_RATE)
        
        # Encontrar fundamental
        peak_idx = np.argmax(spectrum[1:]) + 1
        fundamental_freq = freqs[peak_idx]
        fundamental_amp = spectrum[peak_idx]
        
        if fundamental_amp == 0:
            return 0
        
        # Calcular harmônicos
        harmonic_amps = []
        for h in range(2, 6):  # 2º ao 5º harmônico
            harm_freq = fundamental_freq * h
            if harm_freq < SAMPLE_RATE / 2:
                harm_idx = np.argmin(np.abs(freqs - harm_freq))
                if harm_idx < len(spectrum):
                    harmonic_amps.append(spectrum[harm_idx])
        
        if not harmonic_amps:
            return 0
        
        thd = np.sqrt(np.sum(np.array(harmonic_amps) ** 2)) / fundamental_amp * 100
        return min(thd, 50)  # Limitar a 50% para permitir valores mais realistas

    def detect_pitch(self, x, fs):
        # Autocorrelação para pitch
        x = x - np.mean(x)
        corr = np.correlate(x, x, mode='full')
        corr = corr[len(corr)//2:]
        
        # Encontrar picos
        d = np.diff(corr)
        start = np.where(d > 0)[0]
        if len(start) == 0:
            return None
        
        peak = np.argmax(corr[start[0]:]) + start[0]
        if peak == 0:
            return None
        
        pitch = fs / peak
        return pitch if 60 < pitch < 1000 else None

    def calculate_spectral_centroid(self, x, fs):
        # Calcular centroide espectral
        spectrum = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1/fs)
        
        if np.sum(spectrum) == 0:
            return 0
        
        centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
        return centroid

    def get_diagnosis(self, rms, peak, clipping, snr, pitch, silence_pct, noise_floor):
        if rms < 0.01:
            return "Silencio"
        elif rms > 0.7:
            return "Volume muito alto - risco de clipping"
        elif clipping > 10:
            return "Clipping detectado - reduzir volume"
        elif snr < 15:
            return f"Ruido alto (SNR: {snr:.1f}dB) - verificar ambiente"
        elif noise_floor > 0.01:
            return f"Ruido de fundo detectado ({noise_floor:.4f})"
        elif silence_pct > 80:
            return "Silencio predominante"
        elif pitch and 60 < pitch < 400:
            return "Voz humana detectada"
        elif snr > 40:
            return f"Audio muito limpo (SNR: {snr:.1f}dB)"
        elif rms > 0.1:
            return f"Audio de boa qualidade (SNR: {snr:.1f}dB)"
        else:
            return "Audio de baixa intensidade"

    def update_histories(self, rms, peak, crest, clipping, snr, thd, pitch, dynamic_range, spectral_centroid, noise_floor):
        histories = [self.rms_history, self.peak_history, self.crest_history, self.clip_history,
                    self.snr_history, self.thd_history, self.pitch_history, self.dynamic_range_history, self.noise_floor_history]
        values = [rms, peak, crest, clipping, snr, thd, pitch or 0, dynamic_range, noise_floor]
        
        for history, value in zip(histories, values):
            history.append(value)
            if len(history) > HISTORY_LEN:
                history.pop(0)

    def update_graphs(self):
        histories = [self.rms_history, self.peak_history, self.crest_history, self.clip_history,
                    self.snr_history, self.thd_history, self.pitch_history, self.dynamic_range_history]
        
        for i, (line, history) in enumerate(zip(self.lines[:-1], histories)):
            if history:
                x_data = np.arange(len(history))
                line.set_data(x_data, history)
                self.axes[i].set_xlim(0, len(history))
        
        # Forçar atualização do canvas
        self.canvas.draw_idle()
        self.canvas.flush_events()

    def calculate_moving_average(self, history, window_size):
        """Calcular média móvel dos últimos valores"""
        if len(history) < window_size:
            return np.mean(history) if history else 0
        return np.mean(history[-window_size:])

    def calculate_total_average(self, history):
        """Calcular média de todas as amostras desde o início"""
        return np.mean(history) if history else 0

    def calculate_audio_grade(self, rms_avg, snr_avg, thd_avg, noise_floor_avg):
        """Calcular nota de qualidade do áudio baseada nas médias"""
        if len(self.rms_history) < 5:  # Precisa de pelo menos 5 amostras
            return "--", "#FFD700"
        
        # Pontuação baseada em cada métrica
        score = 0
        max_score = 100
        
        # RMS (0-25 pontos)
        if 0.1 <= rms_avg <= 0.7:  # Ideal
            score += 25
        elif 0.05 <= rms_avg <= 0.9:  # Aceitável
            score += 15
        elif 0.01 <= rms_avg <= 1.0:  # Baixo/Alto
            score += 5
        
        # SNR (0-40 pontos) - AJUSTADO para ser mais realista
        if snr_avg >= 25:  # Excelente (era 40)
            score += 40
        elif snr_avg >= 20:  # Muito bom (era 30)
            score += 35
        elif snr_avg >= 15:  # Bom (era 20)
            score += 25
        elif snr_avg >= 10:  # Aceitável (era 15)
            score += 15
        elif snr_avg >= 5:  # Regular
            score += 8
        else:  # Ruim
            score += 0
        
        # THD (0-20 pontos)
        if thd_avg <= 1:  # Excelente
            score += 20
        elif thd_avg <= 3:  # Muito bom
            score += 15
        elif thd_avg <= 5:  # Bom
            score += 10
        elif thd_avg <= 8:  # Aceitável
            score += 5
        else:  # Ruim
            score += 0
        
        # Noise Floor (0-15 pontos) - AJUSTADO para ser mais realista
        if noise_floor_avg <= 0.01:  # Excelente (era 0.005)
            score += 15
        elif noise_floor_avg <= 0.02:  # Muito bom (era 0.01)
            score += 12
        elif noise_floor_avg <= 0.05:  # Bom (era 0.02)
            score += 8
        elif noise_floor_avg <= 0.1:  # Aceitável (era 0.05)
            score += 4
        else:  # Ruim
            score += 0
        
        # Converter pontuação para nota
        percentage = (score / max_score) * 100
        
        if percentage >= 90:
            grade = "A+"
            color = "#00FF00"  # Verde
        elif percentage >= 80:
            grade = "A"
            color = "#00FF00"  # Verde
        elif percentage >= 70:
            grade = "B"
            color = "#90EE90"  # Verde claro
        elif percentage >= 60:
            grade = "C"
            color = "#FFD700"  # Dourado
        elif percentage >= 50:
            grade = "D"
            color = "#FFA500"  # Laranja
        else:
            grade = "E"
            color = "#FF0000"  # Vermelho
        
        return grade, color

    def populate_device_list(self):
        """Popular a lista de dispositivos de entrada disponíveis"""
        devices = sd.query_devices()
        input_devices = []
        
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                device_name = dev['name']
                # Adicionar ícone baseado no tipo de dispositivo
                if any(keyword in device_name.lower() for keyword in ['stereo mix', 'mixagem estéreo', 'loopback', 'what u hear', 'cable']):
                    icon = "🔊"
                elif any(keyword in device_name.lower() for keyword in ['mic', 'microfone', 'input']):
                    icon = "🎤"
                else:
                    icon = "🎵"
                
                input_devices.append(f"{icon} {device_name}")
        
        self.device_box.addItems(input_devices)
        print(f"Dispositivos disponíveis: {len(input_devices)}")

    def change_device(self, idx):
        """Mudar dispositivo de áudio"""
        if idx >= 0:
            self.start_stream(idx)
            self.clear_histories()

    def update_spectrum(self, x):
        freqs, spectrum = scipy.signal.welch(x, fs=SAMPLE_RATE, nperseg=min(BLOCK_SIZE, len(x)))
        if np.max(spectrum) > 0:
            spectrum = spectrum / np.max(spectrum)
        
        self.lines[-1].set_data(freqs, spectrum)
        self.axes[-1].set_xlim(0, SAMPLE_RATE/2)
        self.axes[-1].set_ylim(0, 1)
        
        # Forçar atualização do espectro
        self.canvas.draw_idle()
        self.canvas.flush_events()

if __name__ == '__main__':
    # Configurar codificação antes de criar o QApplication
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    app = QApplication(sys.argv)
    app.setApplicationName('Analisador de Audio')
    
    window = AudioAnalyzer()
    window.show()
    sys.exit(app.exec_())
