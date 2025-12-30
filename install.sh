#!/data/data/com.termux/files/usr/bin/bash
# Script de instalação automática para Termux
# Uso: curl -sL https://raw.githubusercontent.com/RogerAngell99/privacy-downloader/playwright/install.sh | bash

set -e

echo "🤖 Privacy Downloader - Instalador Termux"
echo "=========================================="

# Configura dpkg para não pedir input (mantém versão atual em conflitos)
export DEBIAN_FRONTEND=noninteractive

# Atualiza pacotes (sem prompts interativos)
echo "📦 Atualizando repositórios..."
yes | pkg update -y
yes | pkg upgrade -y -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" || true

# Instala dependências do sistema
echo "📦 Instalando dependências..."
pkg install -y python python-pip git ffmpeg libxml2 libxslt libjpeg-turbo || true

# Configura armazenamento (se ainda não configurado)
if [ ! -d "$HOME/storage" ]; then
    echo "📁 Configurando acesso ao armazenamento..."
    termux-setup-storage
    sleep 3
fi

# Define diretório de instalação
INSTALL_DIR="$HOME/privacy-downloader"

# Remove instalação anterior se existir
if [ -d "$INSTALL_DIR" ]; then
    echo "🗑️ Removendo instalação anterior..."
    rm -rf "$INSTALL_DIR"
fi

# Clona repositório
echo "📥 Baixando Privacy Downloader..."
git clone -b playwright https://github.com/RogerAngell99/privacy-downloader.git "$INSTALL_DIR"

# Entra no diretório
cd "$INSTALL_DIR"

# Instala dependências Python
echo "🐍 Instalando dependências Python..."
# No Termux, pip não pode ser atualizado - configuramos para ignorar
export PIP_DISABLE_PIP_VERSION_CHECK=1
pip install --no-cache-dir -r requirements.txt

# Instala Playwright e Chromium
echo "🌐 Instalando navegador (pode demorar)..."
pip install --no-cache-dir playwright
playwright install chromium

# Cria arquivo de configuração
echo "⚙️ Criando configuração inicial..."
cat > settings.yaml << 'EOF'
downloaddir: ~/storage/downloads/privacy
EOF

# Cria template de credenciais
if [ ! -f .secrets.yaml ]; then
    cat > .secrets.yaml << 'EOF'
user: SEU_EMAIL_AQUI
pwd: SUA_SENHA_AQUI
EOF
    echo ""
    echo "⚠️ IMPORTANTE: Edite o arquivo .secrets.yaml com suas credenciais!"
    echo "   nano $INSTALL_DIR/.secrets.yaml"
fi

# Cria alias para facilitar execução
echo "🔧 Criando atalho 'privacy'..."
echo "alias privacy='cd $INSTALL_DIR && python main.py'" >> ~/.bashrc

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "   1. Edite suas credenciais:"
echo "      nano $INSTALL_DIR/.secrets.yaml"
echo ""
echo "   2. Reinicie o Termux ou execute:"
echo "      source ~/.bashrc"
echo ""
echo "   3. Execute o downloader:"
echo "      privacy"
echo ""
echo "   Ou diretamente:"
echo "      cd $INSTALL_DIR && python main.py"
