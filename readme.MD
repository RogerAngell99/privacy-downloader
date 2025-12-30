# Privacy Downloader

Ferramenta para baixar mídias de perfis do Privacy.com.br

## 🚀 Instalação Rápida

### 🤖 Termux (Android)

```bash
curl -sL https://raw.githubusercontent.com/RogerAngell99/privacy-downloader/playwright/install.sh | bash
```

Após instalação, edite suas credenciais e execute:
```bash
nano ~/privacy-downloader/.secrets.yaml
privacy
```

### 💻 Windows/Linux

```bash
git clone -b playwright https://github.com/RogerAngell99/privacy-downloader.git
cd privacy-downloader
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuração

### 1. Credenciais (`.secrets.yaml`)
```yaml
user: "seu_email@exemplo.com"
pwd: "sua_senha"
```

### 2. Diretório de download (`settings.yaml`)
```yaml
# Windows
downloaddir: C:\downloads\privacy

# Linux/Termux
downloaddir: ~/storage/downloads/privacy
```

## 📖 Como usar

```bash
python main.py
```

Quando aparecer a lista de perfis, digite:
- `0` para baixar todos os perfis
- Número do perfil para baixar apenas aquele

### Opções

```bash
python main.py --backlog  # Baixa apenas mídias pendentes no banco
```

## 📋 Requisitos

- Python 3.8+
- FFmpeg (para vídeos HLS)
- Playwright + Chromium

## 📱 Compatibilidade

| Plataforma | Status |
|------------|--------|
| Windows | ✅ |
| Linux | ✅ |
| Termux (Android) | ✅ |

## 📄 Licença

Creative Commons
