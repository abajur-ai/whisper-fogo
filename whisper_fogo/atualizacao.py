"""Atualização pelo GitHub: a versão mais nova é a da última release publicada
em abajur-ai/whisper-fogo.

A versão instalada não é escrita no código. Ela fica em versao_instalada.json,
gravado por quem instala ou atualiza; sem esse registro, qualquer release
publicada conta como mais nova. Atualizar troca só o código: histórico,
dicionário, atalhos e ambiente Python da pessoa ficam onde estão, e o código
substituído vai para versao_anterior/.
"""
import fnmatch
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from caminhos import CODIGO, DADOS
REPOSITORIO = "abajur-ai/whisper-fogo"
API = f"https://api.github.com/repos/{REPOSITORIO}/releases/latest"
REGISTRO = DADOS / "versao_instalada.json"
ANTERIOR = "versao_anterior"
ENTRADA = "voz.py"        # o arquivo que marca a pasta do programa dentro do pacote
# O que é da pessoa ou da máquina, e nunca vem da release.
PRESERVAR = {"historico.jsonl", "aprendido.json", "atalhos.json", "dicionario.json",
             "versao_instalada.json", "voz.log", "instancia.lock", ".venv", "__pycache__", ANTERIOR}
PRESERVAR_PADROES = ("falha-*.wav", "*.tmp")
# O que é só do repositório e não faz parte do programa instalado.
SO_DO_REPOSITORIO = ("README*", "LICENSE*", "docs", ".*")


def instalada():
    try:
        return json.loads(REGISTRO.read_text(encoding="utf-8"))["versao"]
    except Exception:
        return None


def numeros(versao):
    """v1.10.2 -> (1, 10, 2): compara número a número, não como texto."""
    return tuple(int(n) for n in re.findall(r"\d+", versao or ""))


def mais_nova(publicada, atual):
    return atual is None or numeros(publicada) > numeros(atual)


def ultima_publicada(tempo_limite=10):
    """A última release: {"versao", "notas", "pacote", "pagina"}, ou None se o
    repositório ainda não publicou nenhuma. Falha de rede sobe como OSError."""
    pedido = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": "whisper-fogo"})
    try:
        with urllib.request.urlopen(pedido, timeout=tempo_limite) as resposta:
            dados = json.load(resposta)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return {"versao": dados["tag_name"], "notas": dados.get("body") or "",
            "pacote": dados["zipball_url"], "pagina": dados["html_url"]}


def _preservado(relativo):
    primeiro = relativo.parts[0]
    if primeiro in PRESERVAR or any(fnmatch.fnmatch(relativo.name, p) for p in PRESERVAR_PADROES):
        return True
    return any(fnmatch.fnmatch(primeiro, p) for p in SO_DO_REPOSITORIO)


def _baixar(url, destino):
    pedido = urllib.request.Request(url, headers={"User-Agent": "whisper-fogo"})
    with urllib.request.urlopen(pedido, timeout=120) as resposta, open(destino, "wb") as f:
        shutil.copyfileobj(resposta, f)


def _uv():
    achado = shutil.which("uv")
    if achado:
        return achado
    padrao = Path.home() / ".local" / "bin" / "uv.exe"
    if padrao.exists():
        return str(padrao)
    raise OSError("o instalador de dependências (uv) não foi encontrado")


def _instalar_dependencias(requisitos, destino):
    python = destino / ".venv" / "Scripts" / "python.exe"
    subprocess.run([_uv(), "pip", "install", "--python", str(python), "-r", str(requisitos)],
                   check=True, capture_output=True, timeout=900,
                   creationflags=0x08000000)              # CREATE_NO_WINDOW: sem janela preta


def aplicar(publicada, destino=CODIGO, baixar=_baixar):
    """Baixa o código da versão publicada, troca o do programa e registra a
    versão. As dependências são instaladas antes da troca: se falharem, o
    programa continua exatamente como estava."""
    destino = Path(destino)
    with tempfile.TemporaryDirectory() as pasta:
        pacote = Path(pasta) / "pacote.zip"
        baixar(publicada["pacote"], pacote)
        with zipfile.ZipFile(pacote) as z:
            z.extractall(Path(pasta) / "aberto")
        entradas = list((Path(pasta) / "aberto").rglob(ENTRADA))
        if not entradas:
            raise ValueError("o pacote publicado não contém o programa")
        raiz = min(entradas, key=lambda p: len(p.parts)).parent
        arquivos = [p.relative_to(raiz) for p in raiz.rglob("*")
                    if p.is_file() and not _preservado(p.relative_to(raiz))]

        requisitos = raiz / "requirements.txt"
        if requisitos.exists():
            _instalar_dependencias(requisitos, destino)

        anterior = destino / ANTERIOR
        shutil.rmtree(anterior, ignore_errors=True)
        for relativo in arquivos:
            if (destino / relativo).exists():
                (anterior / relativo).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destino / relativo, anterior / relativo)
        for relativo in arquivos:
            (destino / relativo).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raiz / relativo, destino / relativo)

    (destino / REGISTRO.name).write_text(
        json.dumps({"versao": publicada["versao"], "instalada_em": time.strftime("%d/%m/%Y %H:%M")},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return len(arquivos)


def _demo():
    """Autoteste em pasta temporária, com um pacote no formato do GitHub
    (uma pasta raiz dentro do zip). Nada da instalação de verdade é tocado."""
    global REGISTRO
    assert numeros("v1.10.2") == (1, 10, 2) and numeros("1.2") == (1, 2)
    assert mais_nova("v1.10.0", "v1.9.9") and not mais_nova("v1.2.0", "v1.2.0")
    assert mais_nova("v1.0.0", None), "sem registro, qualquer release é mais nova"
    assert not mais_nova("v1.2.0", "v1.10.0")

    with tempfile.TemporaryDirectory() as pasta:
        programa = Path(pasta) / "instalado"
        (programa / ".venv").mkdir(parents=True)
        (programa / "voz.py").write_text("antigo", encoding="utf-8")
        (programa / "tema.py").write_text("antigo", encoding="utf-8")
        (programa / "historico.jsonl").write_text("minhas transcrições", encoding="utf-8")
        (programa / "falha-1.wav").write_text("audio", encoding="utf-8")

        fonte = Path(pasta) / "abajur-ai-whisper-fogo-abc123"
        (fonte / "docs").mkdir(parents=True)
        (fonte / "voz.py").write_text("novo", encoding="utf-8")
        (fonte / "novo_modulo.py").write_text("novo", encoding="utf-8")
        (fonte / "historico.jsonl").write_text("NÃO PODE ENTRAR", encoding="utf-8")
        (fonte / "README.md").write_text("só do repositório", encoding="utf-8")
        (fonte / "docs" / "img.svg").write_text("<svg/>", encoding="utf-8")
        zipado = Path(pasta) / "release.zip"
        with zipfile.ZipFile(zipado, "w") as z:
            for p in fonte.rglob("*"):
                z.write(p, p.relative_to(fonte.parent))

        REGISTRO = programa / "versao_instalada.json"
        copia = lambda url, destino: shutil.copy(zipado, destino)
        n = aplicar({"versao": "v1.0.0", "pacote": "x"}, programa, baixar=copia)
        assert n == 2, n                                         # voz.py e novo_modulo.py
        assert (programa / "voz.py").read_text("utf-8") == "novo"
        assert (programa / "novo_modulo.py").exists()
        assert (programa / "tema.py").read_text("utf-8") == "antigo", "o que a release não traz fica"
        assert (programa / "historico.jsonl").read_text("utf-8") == "minhas transcrições"
        assert (programa / "falha-1.wav").exists() and not (programa / "README.md").exists()
        assert (programa / ANTERIOR / "voz.py").read_text("utf-8") == "antigo"
        assert instalada() == "v1.0.0"

        vazio = Path(pasta) / "vazio.zip"
        with zipfile.ZipFile(vazio, "w") as z:
            z.writestr("pasta/LEIA.txt", "sem programa")
        try:
            aplicar({"versao": "v9", "pacote": "x"}, programa, baixar=lambda u, d: shutil.copy(vazio, d))
            raise AssertionError("aplicou pacote sem o programa")
        except ValueError:
            pass
        assert instalada() == "v1.0.0" and (programa / "voz.py").read_text("utf-8") == "novo"
    REGISTRO = DADOS / "versao_instalada.json"
    print("atualizacao.py: autoteste ok")


if __name__ == "__main__":
    _demo()
