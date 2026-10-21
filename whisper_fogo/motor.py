"""Motor de transcrição: o whisper-server, do whisper.cpp, rodando ao lado do
programa num processo próprio.

Uma base só para qualquer computador. No Windows a transcrição vai para a placa
de vídeo pelo Vulkan, que NVIDIA, AMD e Intel suportam; no Mac, pelo Metal. Sem
placa que sirva, o processador assume. O programa conversa com o servidor por
HTTP em 127.0.0.1, numa porta escolhida na hora.

O servidor e o modelo são baixados uma vez para a pasta de dados, com o
conteúdo conferido pelo SHA-256. Download interrompido continua de onde parou.
"""
import atexit
import hashlib
import io
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
import wave
import zipfile
from pathlib import Path

import numpy as np

from caminhos import DADOS

MAC = sys.platform == "darwin"
TAXA = 16000

PASTA = DADOS / "motor"
VERSAO = "motor-whispercpp-1.9.5-r2"
SERVIDOR_DIR = PASTA / VERSAO
# O servidor aparece como Whisper Fogo, igual ao programa. No Mac o Monitor de
# Atividade mostra o processo pelo nome do arquivo; no Windows o nome vem de
# dentro do executável (executavel.carimbar_motor).
SERVIDOR = SERVIDOR_DIR / ("Whisper Fogo" if MAC else "whisper-server.exe")
SERVIDOR_ORIGINAL = "whisper-server"
VAD = SERVIDOR_DIR / "ggml-silero-v6.2.0.bin"

if not MAC:
    PACOTE = "motor-windows-x64.zip"
elif platform.machine() == "arm64":
    PACOTE = "motor-macos-arm64.zip"
else:
    PACOTE = "motor-macos-x64.zip"
PACOTE_URL = f"https://github.com/abajur-ai/whisper-fogo/releases/download/{VERSAO}/{PACOTE}"
PACOTE_SHA = {
    "motor-windows-x64.zip": "31c024bec75a61d48c34f3eff4f8f12df237a663968be1f91e1c8c1c6dbb2273",
    "motor-macos-arm64.zip": "6a8a0b7073502d824c16fb079580b1231b60a0d20bc64dc831d665892aa969c8",
    "motor-macos-x64.zip": "9d178c9f6d6daa053788be31116819e4b2fdfddf5449f34e886a9a13f68fe48b",
}

# O mesmo Whisper large-v3-turbo em duas precisões. Na placa, a cheia (f16), a
# mesma do float16 de antes. No processador, 8 bits, como o int8 de antes: 19 s
# contra 30 s da cheia para 11,5 s de fala, com o mesmo texto.
_HF = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
MODELO = PASTA / "ggml-large-v3-turbo.bin"
MODELO_URL = _HF + MODELO.name
MODELO_SHA = "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"
MODELO_CPU = PASTA / "ggml-large-v3-turbo-q8_0.bin"
MODELO_CPU_URL = _HF + MODELO_CPU.name
MODELO_CPU_SHA = "317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1"

ESPERA_SUBIDA = 300       # segundos para o servidor carregar o modelo
_preparo = threading.RLock()


# ---------------- download ----------------
def _baixar(url, destino, mostrar=False):
    """Baixa para `destino.parcial`, continuando de onde parou. No Mac o curl do
    sistema faz o trabalho, porque usa os certificados do macOS; no Windows o
    Python já lê os certificados do sistema. `mostrar` imprime o andamento,
    para o instalador."""
    parcial = destino.with_name(destino.name + ".parcial")
    if MAC:
        subprocess.run(["curl", "-fL", "-#" if mostrar else "-sS", "--retry", "3", "-C", "-",
                        "-o", str(parcial), url], check=True, timeout=7200)
        return parcial
    inicio = parcial.stat().st_size if parcial.exists() else 0
    cabecalhos = {"User-Agent": "whisper-fogo"}
    if inicio:
        cabecalhos["Range"] = f"bytes={inicio}-"
    with urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=60) as r:
        if inicio and r.status != 206:        # o servidor ignorou o pedido de continuar
            inicio = 0
        total = inicio + int(r.headers.get("Content-Length") or 0)
        feito, aviso = inicio, 0
        with open(parcial, "ab" if inicio else "wb") as f:
            while bloco := r.read(1 << 20):
                f.write(bloco)
                feito += len(bloco)
                if mostrar and total and feito * 10 // total > aviso:
                    aviso = feito * 10 // total
                    print(f"  {aviso * 10}% de {total / 1e9:.2f} GB".replace(".", ","), flush=True)
    return parcial


def _sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _baixar_conferido(url, destino, sha, baixar):
    parcial = baixar(url, destino)
    if sha and _sha256(parcial) != sha:
        parcial.unlink(missing_ok=True)
        raise OSError(f"o arquivo baixado de {url} não confere")
    os.replace(parcial, destino)


def preparar(baixar=_baixar, cpu=None):
    """Garante o servidor e o modelo que esta máquina usa: o da placa, ou o do
    processador quando não há placa (ou quando `cpu` pede). Sem nada a baixar,
    volta na hora."""
    with _preparo:
        PASTA.mkdir(parents=True, exist_ok=True)
        if MAC and (SERVIDOR_DIR / SERVIDOR_ORIGINAL).exists():
            os.replace(SERVIDOR_DIR / SERVIDOR_ORIGINAL, SERVIDOR)
        if not SERVIDOR.exists():
            zip_ = PASTA / PACOTE
            _baixar_conferido(PACOTE_URL, zip_, PACOTE_SHA.get(PACOTE), baixar)
            aberto = Path(tempfile.mkdtemp(dir=PASTA))
            try:
                with zipfile.ZipFile(zip_) as z:
                    z.extractall(aberto)
                if MAC:
                    if (aberto / SERVIDOR_ORIGINAL).exists():
                        os.replace(aberto / SERVIDOR_ORIGINAL, aberto / SERVIDOR.name)
                    os.chmod(aberto / SERVIDOR.name, 0o755)
                shutil.rmtree(SERVIDOR_DIR, ignore_errors=True)
                os.replace(aberto, SERVIDOR_DIR)
            finally:
                shutil.rmtree(aberto, ignore_errors=True)
                zip_.unlink(missing_ok=True)
            # o motor de uma versão anterior do programa não serve mais
            for velho in PASTA.glob("motor-whispercpp-*"):
                if velho.is_dir() and velho.name != VERSAO:
                    shutil.rmtree(velho, ignore_errors=True)
            for marca in PASTA.glob("aquecido-*"):
                if marca.name != f"aquecido-{VERSAO}":
                    marca.unlink(missing_ok=True)
        if not MAC and SERVIDOR.stat().st_size > 1024:     # o autoteste usa um servidor de mentira
            import executavel
            executavel.carimbar_motor(SERVIDOR)
        if cpu is None:
            cpu = placa() is False
        if cpu and not MODELO_CPU.exists():
            _baixar_conferido(MODELO_CPU_URL, MODELO_CPU, MODELO_CPU_SHA, baixar)
        if not cpu and not MODELO.exists():
            _baixar_conferido(MODELO_URL, MODELO, MODELO_SHA, baixar)


def aquecer():
    """Na primeira vez que roda numa placa, o driver de vídeo compila os
    programas do motor, e a primeira transcrição leva dezenas de segundos (45 s
    medidos numa RTX 4050, contra 1,5 s depois). O driver guarda o resultado,
    então basta passar por isso uma vez, aqui, longe de um ditado de verdade.

    Roda dentro do mesmo cadeado do preparo: um ditado que chegue no meio espera
    terminar, em vez de subir um segundo servidor na placa."""
    marca = PASTA / f"aquecido-{VERSAO}"
    with _preparo:
        preparar()
        if marca.exists() or placa() is False:
            return                         # sem placa não há o que compilar
        m = Motor()
        try:
            if m.placa_em_uso:
                # 40 s de ruído com o VAD desligado: duas janelas de 30 s,
                # passando pelo codificador e pelo decodificador
                ruido = np.random.default_rng(0).normal(0, 0.05, TAXA * 40).astype(np.float32)
                m._pedir(_wav(ruido), None, 40, {"vad": "false"})
        finally:
            m.liberar()
        marca.touch()


def preparar_em_segundo_plano():
    """Quem atualiza pelo menu recebe só o código: o motor chega aqui, logo
    depois de o programa abrir, sem esperar o primeiro ditado."""
    def trabalho():
        try:
            aquecer()
        except Exception as e:
            print(f"[motor ainda não preparado, tento no próximo ditado] {e}", file=sys.stderr)
    threading.Thread(target=trabalho, daemon=True).start()


# ---------------- escolha da placa ----------------
def escolher_placa(linhas):
    """Da lista de placas que o Vulkan imprime, o índice da que o motor usa, ou
    False quando não há nenhuma.

    O Vulkan lista também a placa integrada do processador, e às vezes ela vem
    primeiro: num notebook com Intel Iris Xe e RTX 4050, a Intel é a 0. A
    dedicada tem memória própria, que o Vulkan marca como `uma: 0`, e vem antes.
    Só com a integrada, é ela que trabalha."""
    placas = {}
    for linha in linhas:
        m = re.search(r"ggml_vulkan: (\d+) = .*\| uma: (\d)", linha)
        if m:
            placas[int(m.group(1))] = m.group(2) == "0"
    if not placas:
        return False
    dedicadas = [i for i, dedicada in sorted(placas.items()) if dedicada]
    return dedicadas[0] if dedicadas else min(placas)


_placa = None     # ainda não sondada; depois, o índice da placa ou False


def placa():
    """A placa que o motor usa nesta máquina, sondada uma vez por abertura do
    programa. No Windows o servidor, chamado sem modelo, carrega as bibliotecas
    de placa, imprime a lista do Vulkan e sai, em 1 s. Sem Vulkan na máquina, a
    biblioteca de placa nem carrega e a lista vem vazia. No Mac, o Apple Silicon
    tem Metal, e o pacote do Mac Intel é só de processador."""
    global _placa
    if _placa is None:
        if MAC:
            _placa = 0 if PACOTE.endswith("arm64.zip") else False
        else:
            try:
                saida = subprocess.run(
                    [str(SERVIDOR), "-m", str(PASTA / "sonda-sem-modelo.bin")], cwd=str(SERVIDOR_DIR),
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
                    creationflags=0x08000000).stdout                # CREATE_NO_WINDOW
                _placa = escolher_placa(saida.decode("utf-8", "replace").splitlines())
            except (OSError, subprocess.TimeoutExpired) as e:
                print(f"[motor] a sonda de placa falhou, seguindo no processador: {e}", file=sys.stderr)
                _placa = False
    return _placa


# ---------------- comunicação ----------------
def _wav(audio):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    return buffer.getvalue()


def _formulario(campos, wav):
    fronteira = uuid.uuid4().hex
    partes = [f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n'
              f'{valor}\r\n'.encode("utf-8") for nome, valor in campos.items()]
    partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="file"; '
                  f'filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + wav + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={fronteira}"


def juntar(texto):
    """O servidor devolve um trecho por linha, e o corte entre trechos às vezes
    cai no meio da palavra ("aba" + "ixo"). Cada trecho já traz o próprio
    espaço inicial quando começa palavra nova, então colar sem separador
    reconstrói a frase."""
    return " ".join(texto.replace("\n", "").split())


# Pedido local nunca passa por proxy: o proxy da rede da empresa não alcança o
# 127.0.0.1 desta máquina.
_direto = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _aberta(porta):
    try:
        socket.create_connection(("127.0.0.1", porta), timeout=0.5).close()
        return True
    except OSError:
        return False


_job = None


def _prender_ao_programa(processo):
    """Windows: o servidor entra num Job Object que o sistema fecha junto com
    este programa, mesmo se ele for encerrado à força. Sem isso o servidor
    ficaria órfão segurando a memória da placa."""
    global _job
    if MAC:
        return                          # no Mac, ver encerrar_orfaos()
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    if _job is None:
        class Basico(ctypes.Structure):
            _fields_ = [("a", ctypes.c_int64), ("b", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                        ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                        ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

        class Estendido(ctypes.Structure):
            _fields_ = [("basico", Basico), ("io", ctypes.c_uint64 * 6), ("m", ctypes.c_size_t * 4)]

        info = Estendido()
        info.basico.LimitFlags = 0x2000                    # KILL_ON_JOB_CLOSE
        job = k32.CreateJobObjectW(None, None)
        if not job or not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            return
        _job = job
    k32.AssignProcessToJobObject(_job, int(processo._handle))


class Motor:
    """Um whisper-server com o modelo carregado. Criar sobe o processo;
    encerrar() devolve a memória da placa."""

    def __init__(self):
        preparar()
        self.processo = None
        self.porta = None
        self.cpu = placa() is False
        self.placa_em_uso = False
        self.uso = threading.Lock()      # liberar espera a transcrição em curso
        _vivos.add(self)
        self._subir()

    def _subir(self):
        """Sobe o servidor e espera o modelo carregar. Se a placa falhar ao
        carregar, sobe de novo no processador."""
        while True:
            linhas, motivo = self._tentar()
            if motivo is None:
                return
            if self.cpu:
                raise RuntimeError("o motor não subiu: " + " | ".join(linhas[-5:]))
            print("[motor] a placa não carregou o modelo, seguindo no processador:\n  "
                  + "\n  ".join(linhas[-8:]), file=sys.stderr)
            self.cpu = True

    def _tentar(self):
        if self.cpu:
            preparar(cpu=True)            # a placa falhou: o modelo do processador pode faltar
        self.porta = _porta_livre()
        # Na placa, 4 threads bastam e mais delas só disputam o processador
        # (medido: 0,95 s com 4 contra 1,0 s com 8). Sem placa, elas fazem a conta.
        threads = min(8, os.cpu_count() or 4) if self.cpu else 4
        args = [str(SERVIDOR), "-m", str(MODELO_CPU if self.cpu else MODELO), "-l", "pt", "-bs", "5",
                "--vad", "-vm", str(VAD), "-t", str(threads),
                "--host", "127.0.0.1", "--port", str(self.porta)]
        if self.cpu:
            args.append("-ng")
        elif placa():
            args += ["-dev", str(placa())]
        self.processo = subprocess.Popen(
            args, cwd=str(SERVIDOR_DIR), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=0 if MAC else 0x08000000)         # CREATE_NO_WINDOW
        _prender_ao_programa(self.processo)

        linhas = []

        def ler(processo):
            # o servidor fala o tempo todo: a saída é lida até o fim, senão o
            # tubo enche e ele trava. Só a subida interessa.
            for bruta in processo.stdout:
                if len(linhas) < 400:
                    linhas.append(bruta.decode("utf-8", "replace").rstrip())
        threading.Thread(target=ler, args=(self.processo,), daemon=True).start()

        # A porta só abre depois de o modelo carregar: porta aberta é servidor
        # pronto. A linha que ele imprime ao ficar pronto não serve de sinal,
        # porque sai pela saída padrão, que fica retida sem terminal.
        limite = time.time() + ESPERA_SUBIDA
        while not _aberta(self.porta):
            time.sleep(0.1)
            if self.processo.poll() is not None or time.time() > limite:
                self.encerrar()
                return linhas, "falhou"
        usado = next((l.split("using ")[1].removesuffix(" backend") for l in linhas
                      if "whisper_backend_init_gpu: using" in l), None)
        if not self.cpu and not usado:
            # a placa não iniciou e o servidor ficou no processador com o modelo
            # da placa, devagar: melhor subir de vez no modo do processador
            self.encerrar()
            return linhas, "falhou"
        nome = next((l.split(" = ", 1)[1].split(" | ")[0] for l in linhas
                     if f"ggml_vulkan: {placa() or 0} = " in l), None)
        self.placa_em_uso = not self.cpu
        print(f"[motor] {f'placa {usado}' if self.placa_em_uso else 'processador'}"
              f"{f' ({nome})' if nome and self.placa_em_uso else ''}", file=sys.stderr)
        return linhas, None

    def _pedir(self, wav, vocabulario, segundos, extra=None):
        campos = {"response_format": "json", "temperature": "0.0", **(extra or {})}
        if vocabulario:
            # o vocabulário vale em toda janela de 30 s da fala, não só na primeira
            campos.update(prompt=vocabulario, carry_initial_prompt="true")
        corpo, tipo = _formulario(campos, wav)
        pedido = urllib.request.Request(f"http://127.0.0.1:{self.porta}/inference", data=corpo,
                                        headers={"Content-Type": tipo})
        with _direto.open(pedido, timeout=60 + segundos * 20) as r:
            dados = json.load(r)
        if "error" in dados:
            raise RuntimeError(dados["error"])
        return juntar(dados.get("text", ""))

    def transcrever(self, audio, vocabulario=None):
        """Texto da fala em português. Se o servidor cair no meio (driver da
        placa atualizado, memória da placa esgotada), ele sobe de novo e tenta
        outra vez; na terceira, já no processador."""
        wav, segundos = _wav(audio), len(audio) / TAXA
        with self.uso:
            for tentativa in range(3):
                try:
                    return self._pedir(wav, vocabulario, segundos)
                except Exception as e:
                    if tentativa == 2:
                        raise
                    print(f"[motor reiniciado] {e}", file=sys.stderr)
                    self.encerrar()
                    self.cpu = self.cpu or tentativa == 1
                    self._subir()

    def liberar(self):
        """Devolve a memória da placa. Uma transcrição em curso termina antes."""
        with self.uso:
            self.encerrar()
        _vivos.discard(self)

    def encerrar(self):
        processo, self.processo = self.processo, None
        if processo and processo.poll() is None:
            processo.kill()
            try:
                processo.wait(10)
            except subprocess.TimeoutExpired:
                pass


_vivos = set()


def encerrar_todos():
    """O servidor sai junto com o programa."""
    for m in list(_vivos):
        m.encerrar()


def encerrar_orfaos():
    """No Mac não há Job Object: se o programa for encerrado à força, o servidor
    fica para trás segurando memória. O programa é de instância única, então ao
    abrir qualquer servidor desta pasta é sobra da execução anterior."""
    if MAC:
        subprocess.run(["pkill", "-f", str(PASTA / "motor-whispercpp")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


atexit.register(encerrar_todos)


def _autoteste():
    """Partes que não precisam do servidor: texto, escolha de placa, formulário,
    áudio e download com conferência, numa pasta temporária."""
    assert juntar(" Eu não gostei da linha ficar aba\nixo das abas.\n Quero acima.\n") == \
        "Eu não gostei da linha ficar abaixo das abas. Quero acima."
    assert juntar(" o \n VS Code\n") == "o VS Code"
    assert juntar("") == ""

    notebook = ["ggml_vulkan: Found 2 Vulkan devices:",
                "ggml_vulkan: 0 = Intel(R) Iris(R) Xe Graphics (Intel Corporation) | uma: 1 | fp16: 1",
                "ggml_vulkan: 1 = NVIDIA GeForce RTX 4050 Laptop GPU (NVIDIA) | uma: 0 | fp16: 1"]
    assert escolher_placa(notebook) == 1, "a dedicada vem antes da integrada"
    assert escolher_placa(notebook[:2]) == 0, "só a integrada: é ela que trabalha"
    assert escolher_placa(["ggml_vulkan: 0 = AMD Radeon RX 7600 | uma: 0 | fp16: 1"]) == 0
    assert escolher_placa(["error: failed to initialize whisper context"]) is False, "sem Vulkan"

    audio = np.sin(np.linspace(0, 400, TAXA)).astype(np.float32)
    wav = _wav(audio)
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (TAXA, 1, TAXA)
    corpo, tipo = _formulario({"prompt": "Abajur, Claude Code."}, wav)
    fronteira = tipo.split("boundary=")[1]
    assert corpo.count(f"--{fronteira}".encode()) == 3 and corpo.endswith(f"--{fronteira}--\r\n".encode())
    assert "Abajur, Claude Code.".encode() in corpo and wav in corpo

    global PASTA, SERVIDOR_DIR, SERVIDOR, VAD, MODELO, MODELO_CPU, MODELO_SHA, MODELO_CPU_SHA, _placa
    salvo = PASTA, SERVIDOR_DIR, SERVIDOR, VAD, MODELO, MODELO_CPU, MODELO_SHA, MODELO_CPU_SHA, _placa
    sha_pacote = PACOTE_SHA[PACOTE]
    with tempfile.TemporaryDirectory() as pasta:
        fonte = Path(pasta) / "fonte"
        fonte.mkdir()
        pacote = fonte / PACOTE
        with zipfile.ZipFile(pacote, "w") as z:
            z.writestr(SERVIDOR.name, "binário")
            z.writestr(VAD.name, "vad")
        (fonte / "f16.bin").write_bytes(b"pesos" * 1000)
        (fonte / "q8.bin").write_bytes(b"oito" * 1000)
        PASTA = Path(pasta) / "motor"
        (PASTA / "motor-whispercpp-0.0.1").mkdir(parents=True)       # motor de versão anterior
        (PASTA / "aquecido-motor-whispercpp-0.0.1").touch()
        SERVIDOR_DIR = PASTA / VERSAO
        SERVIDOR, VAD = SERVIDOR_DIR / SERVIDOR.name, SERVIDOR_DIR / VAD.name
        MODELO, MODELO_CPU = PASTA / MODELO.name, PASTA / MODELO_CPU.name
        origem = {PACOTE_URL: pacote, MODELO_URL: fonte / "f16.bin", MODELO_CPU_URL: fonte / "q8.bin"}
        pedidos = []

        def copia(url, destino):
            pedidos.append(url)
            parcial = destino.with_name(destino.name + ".parcial")
            shutil.copy(origem[url], parcial)
            return parcial

        MODELO_SHA, MODELO_CPU_SHA = _sha256(fonte / "f16.bin"), _sha256(fonte / "q8.bin")
        PACOTE_SHA[PACOTE] = _sha256(pacote)
        try:
            _placa = 1                                       # máquina com placa
            preparar(copia)
            assert SERVIDOR.read_text("utf-8") == "binário" and VAD.exists()
            assert pedidos == [PACOTE_URL, MODELO_URL], "com placa, só o modelo da placa"
            assert not (PASTA / "motor-whispercpp-0.0.1").exists(), "o motor anterior sai"
            assert not (PASTA / "aquecido-motor-whispercpp-0.0.1").exists()
            preparar(copia)
            assert len(pedidos) == 2, "com tudo no lugar, nada é baixado de novo"
            assert not list(PASTA.glob("*.parcial")) and not list(PASTA.glob("*.zip"))

            preparar(copia, cpu=True)                        # a placa falhou
            assert pedidos[2:] == [MODELO_CPU_URL] and MODELO_CPU.read_bytes() == b"oito" * 1000

            MODELO_CPU.unlink()
            _placa = False                                   # máquina sem placa
            MODELO_CPU_SHA = "0" * 64
            try:
                preparar(copia)
                raise AssertionError("aceitou modelo que não confere")
            except OSError:
                pass
            assert not MODELO_CPU.exists() and not list(PASTA.glob("*.parcial"))
        finally:
            PASTA, SERVIDOR_DIR, SERVIDOR, VAD, MODELO, MODELO_CPU, MODELO_SHA, MODELO_CPU_SHA, _placa = salvo
            PACOTE_SHA[PACOTE] = sha_pacote
    print("motor: autoteste ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--preparar"]:
        # usado pelo instalador: baixa o que faltar, mostrando o andamento
        sys.stdout.reconfigure(encoding="utf-8")
        preparar(lambda url, destino: _baixar(url, destino, mostrar=True))
        if placa() is False:
            print("  Sem placa de vídeo que o motor use: a transcrição roda no processador.")
        else:
            print("  Preparando a placa de vídeo (só na primeira vez, pode levar um minuto)...", flush=True)
            aquecer()
        print("motor pronto")
    elif len(sys.argv) > 1:
        # motor.py arquivo.wav [...]: transcreve com o motor de verdade e mede
        sys.stdout.reconfigure(encoding="utf-8")
        t = time.perf_counter()
        m = Motor()
        print(f"carga {time.perf_counter() - t:.2f}s")
        for arquivo in sys.argv[1:]:
            with wave.open(arquivo) as w:
                dados = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            t = time.perf_counter()
            texto = m.transcrever(dados)
            print(f"{Path(arquivo).name}: {len(dados) / TAXA:.1f}s em {time.perf_counter() - t:.2f}s")
            print(f"  {texto}")
        m.encerrar()
    else:
        _autoteste()
