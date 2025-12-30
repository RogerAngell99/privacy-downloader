# 🤖 Guia de Instalação no Termux (Android)

## 🚀 Instalação Rápida (Um Comando)

Cole este comando no Termux:

```bash
curl -sL https://raw.githubusercontent.com/RogerAngell99/privacy-downloader/playwright/install.sh | bash
```

Depois é só executar:
```bash
privacy
```

O script vai pedir seu **email** e **senha** na primeira execução e salva automaticamente!

---

## Instalação Manual

### Pré-requisitos

Instale os pacotes necessários no Termux:

```bash
# Atualiza repositórios
pkg update && pkg upgrade -y

# Instala Python e dependências
pkg install python python-pip git ffmpeg -y

# Instala bibliotecas de sistema necessárias
pkg install libxml2 libxslt libjpeg-turbo -y
```

## Instalação do Projeto

```bash
# Clone ou copie o projeto para algum diretório
cd ~/storage/shared/privacy-scraper

# Instala dependências Python
pip install -r requirements.txt

# Instala Playwright (IMPORTANTE: no Termux precisa de setup especial)
pip install playwright

# Instala os navegadores do Playwright
# NOTA: No Termux, apenas Chromium funciona bem
playwright install chromium
```

## Configuração

1. **Crie/Edite o arquivo `settings.yaml`**:
```yaml
downloaddir: /storage/emulated/0/Download/privacy
```

2. **Crie/Edite o arquivo `.secrets.yaml`** com suas credenciais:
```yaml
user: seu_email@exemplo.com
pwd: sua_senha
```

## ⚠️ Notas Importantes para Termux

### Armazenamento
Para acessar o armazenamento externo do Android:
```bash
termux-setup-storage
```
Isso cria a pasta `~/storage` com acesso ao armazenamento.

### Chromium no Termux
O script já inclui flags especiais para rodar Chromium no Termux:
- `--no-sandbox`
- `--disable-setuid-sandbox`
- `--disable-dev-shm-usage`
- `--single-process`

### Memória
Em dispositivos com pouca RAM (< 4GB), pode haver problemas. Considere:
- Fechar outros apps antes de rodar
- Usar `--single-process` (já ativado automaticamente)

## Execução

```bash
# Navega até o diretório do projeto
cd ~/storage/shared/privacy-scraper

# Executa o script
python main.py

# Ou com a flag de backlog
python main.py --backlog
```

## Alternativa: Usar proot-distro

Se tiver problemas com Chromium nativo, considere usar uma distro Linux via proot:

```bash
pkg install proot-distro
proot-distro install ubuntu
proot-distro login ubuntu

# Dentro do Ubuntu, instale normalmente:
apt update && apt install python3 python3-pip ffmpeg -y
pip3 install -r requirements.txt
playwright install chromium
python3 main.py
```

## Troubleshooting

### Erro: "cannot allocate memory"
- Feche outros apps
- Reinicie o Termux

### Erro: "No module named 'playwright'"
```bash
pip install --upgrade playwright
playwright install chromium
```

### Erro: "Permission denied" ao salvar arquivos
```bash
termux-setup-storage
# Então use ~/storage/downloads/ como downloaddir
```
