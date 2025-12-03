# EventPerimeterAI

**EventPerimeterAI** é um sistema avançado de monitoramento inteligente projetado para vigilância em tempo real, segurança perimetral digital e Reconhecimento de Placas (LPR). Ele possui um Painel Web moderno para monitoramento contínuo de múltiplas câmeras com latência mínima.

## 🚀 Funcionalidades

*   **Painel Web**: Uma interface web responsiva e com tema escuro para monitorar várias câmeras simultaneamente.
*   **Configuração de Zonas ao Vivo**: Desenhe e atualize zonas de "Gravação" (Azul) e "Violação" (Vermelho) diretamente no feed de vídeo, sem precisar reiniciar o sistema.
*   **Controles Granulares de Câmera**:
    *   **Power**: Ativar/Desativar câmera.
    *   **AI Monitor**: Ativar/Desativar processamento de IA.
    *   **Rec**: Iniciar/Parar gravação manual.
    *   **Snap**: Tirar foto instantânea.
    *   **Zone Toggles**: Ativar/Desativar a visualização das zonas.
*   **Detecção de Violação**: Detecta automaticamente objetos (pessoas, veículos) que permanecem em uma zona de violação por muito tempo.
*   **Reconhecimento de Placas (LPR)**: Captura e lê placas de veículos envolvidos em violações usando PaddleOCR.
*   **Gravação Automática**:
    *   **Vídeo**: Grava em 4K (se disponível) quando atividade é detectada nas zonas.
    *   **Áudio**: Captura áudio junto com o vídeo.
    *   **Mesclagem Inteligente**: Mescla automaticamente vídeo e áudio em um arquivo `.mp4` com velocidade de reprodução corrigida.
*   **Suporte Multi-Câmera**: Design escalável que suporta múltiplos feeds de câmera.

## 🛠️ Tecnologias

*   **Backend**: Python 3.10+, FastAPI
*   **IA**: YOLOv8 (Rastreamento de Objetos), PaddleOCR (LPR)
*   **Processamento de Vídeo**: OpenCV, MoviePy
*   **Frontend**: HTML5, JavaScript, CSS (Templates Jinja2)

## 📦 Instalação

### Pré-requisitos
*   Python 3.10+
*   Uma webcam (ou múltiplas)

### Configuração

1.  **Clone o repositório**
    ```bash
    git clone https://github.com/CamilloOliveira15/EventPerimeterAI.git
    cd EventPerimeterAI
    ```

2.  **Instale as Dependências**
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: Certifique-se de ter `fastapi`, `uvicorn`, `ultralytics`, `paddlepaddle`, `paddleocr`, `opencv-python`, `moviepy` e `sounddevice` instalados.*

## 🚦 Uso

### 1. Inicie o Painel
Inicie o servidor central de monitoramento:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Acesse o Monitor
Abra seu navegador e vá para:
**[http://localhost:8000](http://localhost:8000)**

### 3. Configure as Zonas
1.  No painel, clique em **"Draw Rec (Blue)"** ou **"Draw Vio (Red)"** abaixo da câmera desejada.
2.  Clique no vídeo para desenhar os pontos do polígono.
3.  Clique em **"Save"** para aplicar a zona instantaneamente.

O sistema começará a monitorar, gravar e registrar violações automaticamente com base nas suas configurações.

## 📂 Estrutura do Projeto

```text
EventPerimeterAI/
├── app/
│   ├── main.py            # Ponto de Entrada do Servidor FastAPI
│   ├── camera_manager.py  # Gerenciamento de Câmera com Threads
│   ├── ai_processor.py    # Lógica de IA (YOLO + OCR)
│   ├── templates/
│   │   └── index.html     # Painel Web
│   └── static/            # Assets CSS/JS
├── perimeters.json        # Configurações de Zonas (Salvas automaticamente)
└── requirements.txt       # Dependências do Projeto
```
