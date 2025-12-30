# 🤖 Guia de Instalação no Termux (Android)

## 🚀 Instalação Rápida

Execute os comandos abaixo **um por um** no Termux:

```bash
# 1. Atualiza e instala proot-distro
pkg update -y && pkg install -y proot-distro

# 2. Instala Ubuntu (aguarde ~5 minutos)
proot-distro install ubuntu

# 3. Configura tudo dentro do Ubuntu
proot-distro login ubuntu -- bash -c "
apt-get update && apt-get install -y python3 python3-pip python3-venv git ffmpeg
git clone -b playwright https://github.com/RogerAngell99/privacy-downloader.git /root/privacy-downloader
cd /root/privacy-downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt playwright
playwright install chromium
mkdir -p /root/downloads/privacy
echo 'downloaddir: /root/downloads/privacy' > settings.yaml
"

# 4. Cria atalho 'privacy'
echo 'proot-distro login ubuntu -- bash -c "cd /root/privacy-downloader && source venv/bin/activate && python main.py"' > $PREFIX/bin/privacy
chmod +x $PREFIX/bin/privacy
```

## ▶️ Como Usar

```bash
privacy
```

Na primeira execução, o script vai perguntar:
```
📧 Digite seu email/CPF: 
🔑 Digite sua senha:
💾 Salvar credenciais para próximas execuções? (s/n):
```

Digite **s** para salvar e não precisar digitar novamente!

---

## ⚠️ Notas Importantes

### Por que Ubuntu via proot?
O Playwright não tem binários para Android/ARM, então usamos Ubuntu dentro do Termux via `proot-distro`.

### Memória
Dispositivos com menos de 4GB RAM podem ter problemas. Feche outros apps antes de executar.

### Onde ficam os downloads?
Os arquivos são salvos em `/root/downloads/privacy` dentro do Ubuntu.

Para copiar para o armazenamento do Android:
```bash
proot-distro login ubuntu -- cp -r /root/downloads/privacy ~/storage/downloads/
```

---

## 🔧 Troubleshooting

### Erro: "cannot allocate memory"
- Feche outros apps
- Reinicie o Termux

### Erro ao executar `privacy`
```bash
# Entra no Ubuntu manualmente
proot-distro login ubuntu

# Executa o script
cd /root/privacy-downloader
source venv/bin/activate
python main.py
```

### Reinstalar do zero
```bash
proot-distro remove ubuntu
proot-distro install ubuntu
# Repita os passos de instalação
```
