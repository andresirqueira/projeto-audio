# 🎵 Analisador de Qualidade de Áudio - Media Player

## 📋 Descrição
Analisador de áudio em tempo real desenvolvido em Python com interface gráfica PyQt5. Permite capturar e analisar áudio do microfone ou do sistema (Stereo Mix) para avaliar a qualidade do áudio reproduzido pelo media player.

## ✨ Funcionalidades

### 🎛️ Controles
- **Seletor de Dispositivo**: Lista todos os dispositivos de entrada disponíveis
- **Iniciar/Parar Análise**: Controle de gravação em tempo real
- **Testar Dispositivo**: Verificação rápida de funcionamento
- **Info Dispositivo**: Mostra informações detalhadas do dispositivo selecionado
- **Janela de Média**: Ajusta o número de amostras para cálculo da média móvel (5-50)
- **Limpar Estatísticas**: Reseta todos os dados coletados
- **Salvar Dados**: Exportação dos dados para CSV

### 📊 Métricas Analisadas
- **RMS (Volume Médio)**: Intensidade do sinal
- **Peak (Pico Máximo)**: Amplitude máxima
- **Crest Factor**: Relação entre pico e RMS
- **Clipping**: Detecção de distorção
- **SNR (Signal-to-Noise Ratio)**: Relação sinal/ruído (baseado em regiões de silêncio)
- **Noise Floor**: Nível de ruído de fundo detectado
- **THD (Total Harmonic Distortion)**: Distorção harmônica total
- **Pitch**: Frequência fundamental (para voz)
- **Dynamic Range**: Faixa dinâmica do áudio
- **Spectral Centroid**: Centro de massa espectral
- **Silêncio**: Percentual de silêncio

### 📈 Estatísticas Avançadas
- **Médias Totais**: Valores médios de todas as amostras desde o início
- **Valores Máximos**: Picos mais altos detectados
- **Valores Mínimos**: Valores mais baixos detectados
- **Janela de Média Ajustável**: De 5 a 50 amostras (para outras análises)
- **Limpeza de Estatísticas**: Reset completo dos dados
- **Sistema de Notas**: Avaliação automática da qualidade (A+ a E) baseada nas médias totais

### 📈 Visualizações
- **Gráficos em Tempo Real**: 8 gráficos de linha para cada métrica
- **Espectro de Frequências**: Análise espectral em tempo real
- **Controle de Visibilidade**: Mostrar/ocultar gráficos individuais
- **Histórico**: Últimos 30 segundos de dados

## 🚀 Instalação

### 1. Instalar Dependências
```bash
pip install -r requirements_audio.txt
```

### 2. Testar Dispositivos (Opcional)
```bash
python teste_audio.py
```

### 3. Executar o Programa
```bash
python analisador_audio_python.py
```

## 📋 Como Usar

### Como Usar

1. **Execute o programa** e aguarde a detecção automática de dispositivos
2. **Selecione o dispositivo** desejado no dropdown (todos os dispositivos de entrada são listados)
3. **Clique em "ℹ️ Info Dispositivo"** para ver detalhes do dispositivo selecionado
4. **Clique em "🔧 Testar Dispositivo"** para verificar se está funcionando
5. **Clique em "▶️ Iniciar Análise"** para começar a análise em tempo real

### Métodos de Captura

#### 🎤 Microfone (Recomendado)
- **Reproduza o áudio** no seu media player (VLC, Windows Media Player, etc.)
- **Posicione o microfone** próximo aos alto-falantes
- **Selecione o microfone** na lista de dispositivos

#### 🔊 Stereo Mix (Avançado)
- **Habilite o Stereo Mix**:
  - Clique com botão direito no ícone de som → "Configurações de som"
  - Vá em "Som" → "Configurações avançadas" → "Configurações de som"
  - Na aba "Gravação", clique com botão direito → "Mostrar dispositivos desabilitados"
  - Habilite "Stereo Mix" ou "Mixagem Estéreo"
- **Selecione o Stereo Mix** na lista de dispositivos

#### 🎧 Fones de Ouvido
- **Use fones de ouvido** para reproduzir o áudio
- **Posicione o microfone** próximo aos fones
- **Selecione o microfone** na lista de dispositivos

## 🎯 Interpretação dos Resultados

### 📊 Métricas de Volume
- **RMS < 0.01**: Silêncio
- **RMS 0.01-0.03**: Muito baixo
- **RMS 0.03-0.1**: Baixo
- **RMS 0.1-0.7**: Ideal
- **RMS > 0.7**: Muito alto (risco de clipping)

### ⚠️ Qualidade
- **Clipping > 10**: Distorção detectada
- **SNR < 15 dB**: Ruído alto
- **SNR > 40 dB**: Áudio muito limpo
- **Noise Floor > 0.01**: Ruído de fundo detectado
- **THD > 5%**: Distorção harmônica significativa

### 📊 Sistema de Notas
- **A+ (90-100%)**: Qualidade excepcional
- **A (80-89%)**: Qualidade excelente
- **B (70-79%)**: Qualidade muito boa
- **C (60-69%)**: Qualidade boa
- **D (50-59%)**: Qualidade aceitável
- **E (<50%)**: Qualidade ruim
- **Baseado em**: Médias de todas as amostras desde o início da medição

### 🎼 Características
- **Pitch 60-400 Hz**: Voz humana
- **Dynamic Range > 20 dB**: Boa dinâmica
- **Spectral Centroid**: Indica timbre (agudo/grave)

## 💡 Dicas para Melhor Qualidade

### 🎵 Configuração do Ambiente
- **Ambiente silencioso** para reduzir ruído de fundo
- **Distância constante** entre microfone e fonte de áudio
- **Evite eco e reverberação** no ambiente
- **Use microfone de boa qualidade** se possível

### 🎚️ Configuração do Volume
- **Teste diferentes volumes** do media player
- **Mantenha RMS entre 0.1 e 0.7** para melhor análise
- **Evite clipping** (picos > 0.99)
- **Ajuste a distância** se necessário

### 📱 Configuração do Sistema
- **Desative processamento de áudio** (eco cancellation, noise suppression)
- **Use taxa de amostragem de 44.1 kHz**
- **Verifique permissões** do microfone

## 💾 Salvando Dados

### 📄 Formato CSV
O arquivo salvo contém:
- **Timestamp**: Tempo em segundos
- **RMS**: Volume médio
- **Peak**: Pico máximo
- **Crest**: Crest factor
- **Clipping**: Número de amostras com clipping
- **SNR**: Relação sinal/ruído
- **THD**: Distorção harmônica total
- **Pitch**: Frequência fundamental
- **Dynamic Range**: Faixa dinâmica

### 📊 Análise Posterior
Os dados podem ser importados em:
- **Excel/Google Sheets**
- **Python (pandas)**
- **R/Matlab**
- **Ferramentas de análise de dados**

## 🔧 Solução de Problemas

### ❌ Erro de Dispositivo
- **Verifique permissões** do microfone
- **Teste o dispositivo** primeiro
- **Reinicie o programa** se necessário

### 🎵 Sem Áudio Detectado
- **Verifique o volume** do media player
- **Teste com som** próximo ao microfone
- **Verifique conexões** de áudio

### 📈 Gráficos Não Atualizam
- **Clique em "Iniciar Análise"** primeiro
- **Verifique se há áudio** sendo capturado
- **Reinicie o programa** se necessário

### 🔄 Stereo Mix Não Funciona
- **Habilite nas configurações** do Windows
- **Use microfone** como alternativa
- **Verifique drivers** de áudio

## 🎯 Casos de Uso

### 🎵 Análise de Música
- **Qualidade de reprodução**
- **Detecção de clipping**
- **Análise de frequências**

### 🎤 Análise de Voz
- **Detecção de pitch**
- **Qualidade de gravação**
- **Análise de clareza**

### 🎧 Teste de Equipamentos
- **Qualidade de alto-falantes**
- **Teste de microfones**
- **Análise de amplificadores**

### 📊 Pesquisa e Desenvolvimento
- **Análise acústica**
- **Processamento de sinais**
- **Controle de qualidade**

## 📞 Suporte

Para problemas ou dúvidas:
1. **Verifique as configurações** de áudio
2. **Teste com diferentes** dispositivos
3. **Consulte a documentação** das bibliotecas
4. **Verifique logs** de erro no console

---

**Desenvolvido para análise profissional de qualidade de áudio** 🎵
