# Privacy Downloader

Ferramenta para baixar mídias de perfis do Privacy.com.br

## 🚀 Instalação

### 🤖 Termux (Android)

Veja instruções completas em [TERMUX_SETUP.md](TERMUX_SETUP.md)

**Resumo:**
```bash
pkg install -y proot-distro
proot-distro install ubuntu
# Ver TERMUX_SETUP.md para comandos completos
```

### 💻 Windows/Linux

```bash
git clone -b playwright https://github.com/RogerAngell99/privacy-downloader.git
cd privacy-downloader
pip install -r requirements.txt
playwright install chromium
python main.py
```

## ⚙️ Configuração

Na primeira execução, o script pergunta automaticamente:
```
📧 Digite seu email/CPF: 
🔑 Digite sua senha:
💾 Salvar credenciais para próximas execuções? (s/n):
```

Digitando **s**, as credenciais são salvas e você não precisa digitar novamente!

## 📖 Como usar

```bash
python main.py
```

Quando aparecer a lista de perfis:
- `0` = baixar todos os perfis
- Número do perfil = baixar apenas aquele

### Opções

```bash
python main.py --backlog  # Baixa apenas mídias pendentes
```

## 📱 Compatibilidade

| Plataforma | Status |
|------------|--------|
| Windows | ✅ |
| Linux | ✅ |
| Termux (Android) | ✅ (via proot-distro) |

## 📄 Licença

Creative Commons
