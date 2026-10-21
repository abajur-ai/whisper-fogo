#!/usr/bin/env bash
# Instalador do Whisper Fogo para macOS.
#
# Instala um aplicativo só, em ~/Applications, com o interpretador, as
# bibliotecas, o código e os modelos dentro dele. O macOS então pede microfone e
# acessibilidade uma vez, em nome do Whisper Fogo.
#
# Se algo quebrar, abra uma issue: https://github.com/abajur-ai/whisper-fogo/issues
#

set -euo pipefail

# Cada janela do macOS monta o PATH de um jeito, e o Homebrew muda de lugar entre
# Apple Silicon e Intel. Os três caminhos onde as ferramentas costumam morar
# entram desde já, para que o que já está na máquina seja reaproveitado.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# O interpretador que roda aqui usa a biblioteca padrão de dentro do aplicativo
# assinado: nada de gravar arquivo compilado lá dentro.
export PYTHONDONTWRITEBYTECODE=1

# O aplicativo é só o interpretador, com o nome e o ícone do Whisper Fogo: é a
# ele que o macOS concede microfone e acessibilidade. A permissão fica presa à
# assinatura do aplicativo, então ele não muda entre versões. O código, as
# bibliotecas, o modelo e os dados de uso moram na pasta de dados, e é só ela
# que a atualização troca.
APP="$HOME/Applications/Whisper Fogo.app"
RECURSOS="$APP/Contents/Resources"
DADOS="$HOME/Library/Application Support/WhisperFogo"
DESTINO="$DADOS/app"
VENV="$DADOS/venv"
PYTHON="$VENV/bin/python"
RELEASE="https://api.github.com/repos/abajur-ai/whisper-fogo/releases/latest"
REPO_ZIP="https://github.com/abajur-ai/whisper-fogo/archive/refs/heads/main.zip"

titulo() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
ok()     { printf "  \033[32m[ok]\033[0m %s\n" "$1"; }
aviso()  { printf "  \033[33m[!]\033[0m  %s\n" "$1"; }
erro()   { printf "  \033[31m[X]\033[0m  %s\n" "$1"; }

cat <<'ARTE'

  ####   WHISPER FOGO
  ####   Transcrição de voz grátis e offline, especialista em língua portuguesa.
         Um produto da Abajur (abajur.ai). Instalador para macOS

ARTE

# ------------------------------------------------------------------ requisitos
titulo "Conferindo se a sua máquina aguenta"

problemas=0

if [[ "$(uname)" != "Darwin" ]]; then
  erro "Este instalador é do macOS. No Windows use o Instalar-Whisper-Fogo.bat."
  exit 1
fi
ok "macOS $(sw_vers -productVersion)"

arquitetura="$(uname -m)"
if [[ "$arquitetura" == "arm64" ]]; then
  ok "Apple Silicon ($(sysctl -n machdep.cpu.brand_string)), transcrição na placa pelo Metal"
else
  aviso "Mac Intel. A transcrição roda na CPU e fica bem mais lenta."
fi

ramGB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
if (( ramGB >= 8 )); then ok "Memória RAM: ${ramGB} GB"
else aviso "Você tem ${ramGB} GB de RAM. O recomendado são 8 GB."; fi

livreGB=$(df -g "$HOME" | awk 'NR==2 {print $4}')
if (( livreGB >= 6 )); then ok "Espaço livre: ${livreGB} GB"
else erro "Faltam $(( 6 - livreGB )) GB de espaço. A instalação ocupa cerca de 4 GB."; problemas=1; fi

# Tudo o que a instalação usa vem no macOS de fábrica (curl, tar, unzip) ou é
# binário pronto para esta arquitetura: o Python isolado do uv e as bibliotecas
# em formato wheel. Nada é compilado na sua máquina.
for ferramenta in curl tar unzip; do
  command -v "$ferramenta" >/dev/null 2>&1 || { erro "Falta o comando $ferramenta."; problemas=1; }
done

if ! curl -fsS --head --max-time 20 https://github.com >/dev/null 2>&1; then
  erro "Não consegui falar com a internet. Confira a sua conexão e rode de novo."
  problemas=1
fi
ok "Conexão com a internet"

(( problemas == 0 )) || { erro "Corrija os itens acima e rode de novo."; exit 1; }

# ------------------------------------------------------------------- programa
titulo "Instalando o programa"
mkdir -p "$DESTINO" "$DADOS"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Baixa a última versão publicada, e é ela que fica registrada: o programa
# compara esse número com o do GitHub para saber se há versão nova.
versao=""
origem="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$origem/whisper_fogo/voz.py" ]]; then
  ok "Usando os arquivos do repositório clonado"
else
  echo "  Baixando o programa..."
  info="$(curl -fsSL -H "User-Agent: whisper-fogo" "$RELEASE" 2>/dev/null || true)"
  pacote="$(printf '%s' "$info" | sed -n 's/.*"zipball_url": *"\([^"]*\)".*/\1/p' | head -1)"
  versao="$(printf '%s' "$info" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)"
  if [[ -n "$pacote" ]]; then
    curl -fsSL -H "User-Agent: whisper-fogo" "$pacote" -o "$tmp/programa.zip"
  else
    versao=""
    curl -fsSL "$REPO_ZIP" -o "$tmp/programa.zip"
  fi
  unzip -q "$tmp/programa.zip" -d "$tmp"
  origem="$(dirname "$(dirname "$(find "$tmp" -maxdepth 3 -path '*/whisper_fogo/voz.py' | head -1)")")"
  if [[ -n "$versao" ]]; then ok "Programa baixado: versão $versao"; else ok "Programa baixado"; fi
fi
# O programa aberto é fechado antes, senão ele seguiria com o código antigo e o
# novo não abriria (instância única).
pkill -f "$APP/Contents/MacOS/whisper-fogo" 2>/dev/null || true
pkill -f "$DADOS/motor/motor-whispercpp" 2>/dev/null || true
# O código é trocado inteiro: arquivo de versão antiga não fica para trás. Os
# dados da pessoa ficam na raiz da pasta de dados e não são tocados.
rm -rf "$DESTINO" && mkdir -p "$DESTINO"
cp -R "$origem/whisper_fogo/." "$DESTINO/"
# A revisão de texto por modelo local saiu do programa na versão 1.4.
rm -rf "$DADOS/llama" "$DADOS/modelos"
if [[ -n "$versao" ]]; then
  printf '{\n  "versao": "%s",\n  "instalada_em": "%s"\n}\n' "$versao" "$(date '+%d/%m/%Y %H:%M')" \
    > "$DADOS/versao_instalada.json"
fi
ok "Arquivos copiados"

# -------------------------------------------------------------------- python
titulo "Preparando o Python"
if ! command -v uv >/dev/null 2>&1; then
  echo "  Instalando o uv (gerenciador de Python)..."
  # Mesma lógica do arquivo de um clique: baixa, confere, depois roda.
  curl -fsSL -o "$tmp/instalar-uv.sh" https://astral.sh/uv/install.sh
  sh "$tmp/instalar-uv.sh"
  export PATH="$HOME/.local/bin:$PATH"
fi
ok "uv pronto"

# O aplicativo de uma instalação anterior é mantido como está quando ainda
# serve: refeito, ele ganharia outra assinatura, e o macOS pediria microfone e
# acessibilidade de novo. Só é refeito na primeira instalação, quando a
# assinatura não confere ou quando vem do formato antigo, com o código dentro.
refazer_app=1
if [[ -x "$APP/Contents/MacOS/whisper-fogo" && -x "$RECURSOS/python/bin/python3.12" \
      && ! -e "$RECURSOS/app" ]] && codesign -v "$APP" >/dev/null 2>&1; then
  refazer_app=0
  ok "Aplicativo mantido: as permissões do macOS continuam valendo"
else
  # O interpretador vem para dentro do aplicativo como arquivo, e não como
  # atalho para uma pasta de fora. O macOS resolve o atalho até o arquivo
  # verdadeiro quando decide de quem é o pedido de permissão, e é o arquivo
  # verdadeiro que ele mostra na lista de Ajustes.
  rm -rf "$APP"
  mkdir -p "$APP/Contents/MacOS" "$RECURSOS"
  uv venv --python 3.12 "$tmp/venv-base" >/dev/null
  raiz_python="$("$tmp/venv-base/bin/python" -c \
    'import os, sys; print(os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))))')"
  cp -R "$raiz_python" "$RECURSOS/python"
  ok "Python embarcado no aplicativo ($(du -sh "$RECURSOS/python" | cut -f1))"
fi

rm -rf "$VENV"
uv venv --python "$RECURSOS/python/bin/python3.12" "$VENV" >/dev/null
ok "Ambiente Python isolado criado"

echo "  Instalando as bibliotecas (pode levar alguns minutos)..."
uv pip install --python "$PYTHON" \
  sounddevice numpy pystray pillow pynput pyobjc-framework-Quartz
ok "Bibliotecas instaladas"

# -------------------------------------------------------------------- modelos
titulo "Baixando o motor e o modelo de transcrição"
echo "  Motor whisper.cpp e modelo large-v3-turbo: 1,6 GB no Apple Silicon, 0,9 GB no Mac Intel. Só acontece uma vez."
# O motor e o modelo moram na pasta de dados, fora do aplicativo assinado.
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$DESTINO/motor.py" --preparar \
  || { erro "Não consegui baixar o motor. Confira a conexão e rode de novo: o download continua de onde parou."; exit 1; }
ok "Motor e modelo no lugar"

# --------------------------------------------------------------- dicionario
[[ -f "$DADOS/dicionario.json" ]] || cp "$origem/whisper_fogo/dicionario.exemplo.json" "$DADOS/dicionario.json" 2>/dev/null || true

# ----------------------------------------------------------------- aplicativo
titulo "Finalizando o aplicativo"
# O ponto de entrada abre o programa quando o Finder ou o login lançam o
# aplicativo. Ele mora nas bibliotecas, fora do aplicativo.
cp "$origem/instalador/macos/sitecustomize.py" \
   "$VENV/lib/python3.12/site-packages/sitecustomize.py"

if (( refazer_app )); then
# O executável do pacote é o próprio interpretador. É assim que o macOS trata
# tudo como um programa só: a lista de Ajustes mostra uma linha, com o nome e o
# ícone do Whisper Fogo, em vez do interpretador que roda por baixo.
cp "$RECURSOS/python/bin/python3.12" "$APP/Contents/MacOS/whisper-fogo"
chmod +x "$APP/Contents/MacOS/whisper-fogo"

# O interpretador do pacote acha a biblioteca padrão pelo pyvenv.cfg e as
# bibliotecas do programa, na pasta de dados, por um .pth. Atalho para fora do
# aplicativo não serve: a assinatura recusa.
cat > "$APP/Contents/pyvenv.cfg" <<CFG
home = $RECURSOS/python/bin
include-system-site-packages = false
version = $("$PYTHON" -c 'import platform; print(platform.python_version())')
CFG
mkdir -p "$APP/Contents/lib/python3.12/site-packages"
printf 'import site; site.addsitedir(%s)\n' \
  "$("$PYTHON" -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$VENV/lib/python3.12/site-packages")" \
  > "$APP/Contents/lib/python3.12/site-packages/whisper-fogo.pth"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Whisper Fogo</string>
  <key>CFBundleIdentifier</key><string>ai.whisperfogo.app</string>
  <key>CFBundleExecutable</key><string>whisper-fogo</string>
  <key>CFBundleIconFile</key><string>fogo</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>O Whisper Fogo grava a sua voz para transcrever, sempre na sua máquina.</string>
</dict></plist>
PLIST
cp "$DESTINO/fogo.icns" "$RECURSOS/fogo.icns" 2>/dev/null || true
ok "Aplicativo criado em ~/Applications"
fi

# --------------------------------------------------------------------- testes
titulo "Conferindo a instalação"
# A conferência é informativa: o programa já está instalado neste ponto, e o
# resultado de cada suíte aparece na tela sem interromper o restante.
export PYTHONDONTWRITEBYTECODE=1
for t in corrigir.py tema.py grafias.py atualizacao.py motor.py; do
  "$PYTHON" "$DESTINO/$t" 2>&1 | tail -1 || true
done
# o historico.py abre a janela quando chamado sem argumento, por isso o --teste
"$PYTHON" "$DESTINO/historico.py" --teste 2>&1 | tail -1 || true

# A assinatura local dá identidade ao pacote, e é por ela que o macOS mostra o
# nome e o ícone do Whisper Fogo ao pedir microfone e acessibilidade, em vez do
# caminho de um arquivo solto. O codesign vem no macOS de fábrica, e a
# assinatura é a última etapa porque vale a partir do que está no pacote agora.
# O Python guarda uma versão compilada de cada módulo na primeira vez que o usa.
# Deixar essa etapa pronta agora é o que mantém o pacote igual ao que foi
# assinado, em vez de ele mudar sozinho durante o primeiro uso.
if (( refazer_app )); then
  echo "  Preparando os módulos..."
  PYTHONDONTWRITEBYTECODE= "$RECURSOS/python/bin/python3.12" -m compileall -q "$RECURSOS/python/lib" >/dev/null 2>&1 || true
  codesign --force --deep --sign - "$APP" >/dev/null 2>&1   && ok "Aplicativo assinado"   || aviso "Não consegui assinar o aplicativo. Ele funciona, e o pedido de permissão é que fica com o nome do arquivo."
fi

# ------------------------------------------------------------------ na conta
titulo "Deixando o Whisper Fogo pronto"

# Abre junto com o Mac pelo caminho oficial: a lista "Abrir ao iniciar sessão"
# dos Ajustes, com o nome e o ícone do Whisper Fogo, de onde qualquer um tira o
# programa se quiser. No macOS 13 em diante o próprio programa se registra ao
# abrir (SMAppService); no 11 e no 12, o item entra pelo System Events. O agente
# de inicialização das versões anteriores sai, senão o programa abriria duas vezes.
AGENTE="$HOME/Library/LaunchAgents/ai.whisperfogo.app.plist"
if [[ -f "$AGENTE" ]]; then
  launchctl bootout "gui/$(id -u)/ai.whisperfogo.app" 2>/dev/null || true
  rm -f "$AGENTE"
fi
if (( $(sw_vers -productVersion | cut -d. -f1) >= 13 )); then
  ok "Abre junto com o Mac (Ajustes > Geral > Itens de Início)"
elif osascript -e "tell application \"System Events\" to if not (exists login item \"Whisper Fogo\") then make login item at end with properties {path:\"$APP\", hidden:false}" >/dev/null 2>&1; then
  ok "Abre junto com o Mac (Preferências do Sistema > Usuários e Grupos > Itens de Início)"
else
  aviso "Não consegui pôr o Whisper Fogo nos Itens de Início. Para abrir junto com o Mac, adicione o aplicativo lá."
fi

# Ícone fixo no Dock, para achar o programa junto com os outros. O Dock guarda
# o endereço com os espaços escritos como %20, e é por esse formato que a
# checagem passa, senão a mesma entrada entraria de novo a cada instalação.
APP_URL="file://$(printf '%s' "$APP" | sed 's/ /%20/g')/"
if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -qF "$APP_URL"; then
  defaults write com.apple.dock persistent-apps -array-add \
    "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$APP_URL</string><key>_CFURLStringType</key><integer>15</integer></dict></dict></dict>" \
    2>/dev/null && killall Dock 2>/dev/null
fi
ok "Ícone no Dock"

# A Fn é a tecla do Whisper Fogo. O macOS dá a ela uma ação própria (ditado da
# Apple, emojis ou troca de idioma), que dispararia junto com cada ditado: ela
# passa a não fazer nada sozinha, e a escolha anterior fica guardada.
fn_antes="$(defaults read com.apple.HIToolbox AppleFnUsageType 2>/dev/null || echo padrao)"
if [[ "$fn_antes" != "0" ]]; then
  [[ -f "$DADOS/fn_anterior.txt" ]] || echo "$fn_antes" > "$DADOS/fn_anterior.txt"
  defaults write com.apple.HIToolbox AppleFnUsageType -int 0
  ok "Tecla Fn reservada para o Whisper Fogo"
fi

# Sobe agora, para o ícone já aparecer na barra de menus.
open "$APP" 2>/dev/null && ok "Whisper Fogo aberto"

if (( refazer_app )); then
cat <<'FIM'

  Pronto. Antes do primeiro uso, o macOS vai exigir duas permissões:

    Ajustes > Privacidade e Segurança > Microfone ......... marque o Whisper Fogo
    Ajustes > Privacidade e Segurança > Acessibilidade ... marque o Whisper Fogo

  Sem a segunda, o atalho global não funciona. É uma vez só: as atualizações
  seguintes não pedem de novo.
FIM
else
cat <<'FIM'

  Pronto. As permissões de microfone e acessibilidade que você já deu continuam
  valendo.
FIM
fi
cat <<'FIM'

  Como usar:
    Segure a tecla Fn ............. fala e solta, o texto cola sozinho
    Fn + Espaço ................... mãos livres, a Fn de novo encerra
    Ícone na barra de menus ....... abre o painel administrativo

FIM
