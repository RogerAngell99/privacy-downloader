#!/data/data/com.termux/files/usr/bin/bash
# Script de instalação automática para Termux
# Usa proot-distro com Ubuntu porque Playwright não funciona nativamente no Android/ARM
# Uso: curl -sL https://raw.githubusercontent.com/RogerAngell99/privacy-downloader/playwright/install.sh | bash

set -e

echo "🤖 Privacy Downloader - Instalador Termux"
echo "=========================================="
echo ""
echo "⚠️  NOTA: Playwright não funciona nativamente no Termux."
echo "   Vamos instalar usando Ubuntu via proot-distro."
echo ""

# Configura dpkg para não pedir input
export DEBIAN_FRONTEND=noninteractive

# Atualiza pacotes (sem prompts interativos)
echo "📦 Atualizando Termux..."
yes | pkg update -y 2>/dev/null || true
yes | pkg upgrade -y -o Dpkg::Options::="--force-confold" 2>/dev/null || true

# Instala proot-distro
echo "📦 Instalando proot-distro..."
pkg install -y proot-distro 2>/dev/null || true

# Configura armazenamento (se ainda não configurado)
if [ ! -d "$HOME/storage" ]; then
    echo "📁 Configurando acesso ao armazenamento..."
    termux-setup-storage
    sleep 3
fi

# Instala Ubuntu se não existir
if ! proot-distro list | grep -q "ubuntu"; then
    echo "📥 Instalando Ubuntu (pode demorar)..."
    proot-distro install ubuntu
fi

# Cria script de setup para rodar dentro do Ubuntu
SETUP_SCRIPT="$HOME/privacy_setup.sh"
cat > "$SETUP_SCRIPT" << 'INNERSCRIPT'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "🐧 Configurando Ubuntu..."

# Atualiza Ubuntu
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git ffmpeg curl wget > /dev/null 2>&1

# Define diretório
INSTALL_DIR="/root/privacy-downloader"

# Remove instalação anterior
rm -rf "$INSTALL_DIR"

# Clona repositório
echo "📥 Baixando Privacy Downloader..."
git clone -b playwright https://github.com/RogerAngell99/privacy-downloader.git "$INSTALL_DIR"

cd "$INSTALL_DIR"

# Cria ambiente virtual
echo "🐍 Criando ambiente Python..."
python3 -m venv venv
source venv/bin/activate

# Instala dependências
echo "🐍 Instalando dependências..."
pip install --quiet -r requirements.txt
pip install --quiet playwright

# Instala navegador
echo "🌐 Instalando Chromium (pode demorar)..."
playwright install chromium
playwright install-deps chromium 2>/dev/null || true

# Cria arquivo de configuração
echo "⚙️ Criando configuração..."
cat > settings.yaml << 'EOF'
downloaddir: /root/downloads/privacy
EOF

mkdir -p /root/downloads/privacy

echo ""
echo "✅ Instalação concluída dentro do Ubuntu!"
echo ""
INNERSCRIPT

chmod +x "$SETUP_SCRIPT"

# Executa o setup dentro do Ubuntu
echo "🐧 Executando instalação no Ubuntu..."
proot-distro login ubuntu -- bash /root/privacy_setup.sh

# Cria script de execução no Termux
echo "🔧 Criando atalho 'privacy'..."
cat > "$PREFIX/bin/privacy" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login ubuntu -- bash -c "cd /root/privacy-downloader && source venv/bin/activate && python main.py $*"
EOF
chmod +x "$PREFIX/bin/privacy"

# Remove script temporário
rm -f "$SETUP_SCRIPT"

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "📋 Para executar, digite:"
echo "   privacy"
echo ""
echo "   O script vai pedir seu email e senha na primeira vez."
echo ""
