"""Whisper Fogo: transcrição de voz grátis, offline e especialista em português.
Um produto da Abajur (abajur.ai).

Fica na bandeja sem consumir GPU. O modelo carrega no primeiro uso e se
descarrega sozinho depois de OCIOSO_MIN minutos, devolvendo a VRAM.

Ctrl+Shift+Espaço       grava, transcreve, corrige grafia, cola no cursor.
                        (as teclas podem ser regravadas pelo painel)

Toda transcrição fica salva no historico.jsonl antes de ir para a área de
transferência. Clicar no ícone da bandeja abre o painel administrativo, para
recuperar o que não colou.
"""
import os
import queue
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

MAC = sys.platform == "darwin"
if not MAC:
    import ctypes
    import winsound

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from caminhos import DADOS

# Interpretador que abre as janelas auxiliares em processo próprio: no Windows a
# variante sem console, no macOS o mesmo que já está executando este programa.
PYTHON_JANELA = Path(sys.executable) if MAC else BASE / ".venv" / "Scripts" / "pythonw.exe"


def beep(frequencia, ms):
    """Sinal sonoro de início, fim e erro. É o retorno que diz que o microfone
    abriu sem você precisar olhar para a bandeja."""
    try:
        if MAC:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            winsound.Beep(frequencia, ms)
    except Exception:
        pass


def ligar_log():
    """Roda por pythonw, sem console: sem isso todo erro morre em silêncio e não
    há como saber por que o ditado parou de responder. Só no main, senão quem
    importar o módulo perde a própria saída."""
    if sys.stderr is None or not sys.stderr.isatty():
        try:
            log = open(DADOS / "voz.log", "a", encoding="utf-8", buffering=1)
            sys.stderr = sys.stdout = log
            print(f"\n=== Whisper Fogo iniciado {time.strftime('%d/%m/%Y %H:%M')} ===")
        except Exception:
            pass

# As DLLs de CUDA moram dentro do venv. PATH do processo, não do Windows.
_bins = [str(p) for _s in ("cublas", "cudnn", "cuda_nvrtc")
         if (p := BASE / ".venv" / "Lib" / "site-packages" / "nvidia" / _s / "bin").is_dir()]
os.environ["PATH"] = os.pathsep.join(_bins + [os.environ["PATH"]])

import numpy as np
import sounddevice as sd

import aprendizado
import atalhos
import atualizacao
import observador
from clip import colar, escrever as clipboard_escrever, ler as clipboard_ler
from corrigir import corrigir
from historico import registrar
from teclado import Teclado

# ---------------- configuração ----------------
MODELO = "large-v3-turbo"
COMPUTE = "float16"
OCIOSO_MIN = 10           # minutos sem uso até liberar a VRAM
TAXA = 16000              # o Whisper trabalha em 16 kHz mono
# Trava de segurança contra microfone esquecido aberto, e não limite de uso:
# quem está em fluxo fala meia hora seguida. Uma hora de áudio ocupa 230 MB de
# RAM em float32, que qualquer máquina aguenta.
MAX_SEGUNDOS = 3600


def hotwords():
    """Termos que o reconhecedor deve esperar ouvir: o seu vocabulário de
    trabalho, nomes de produto, siglas da sua área.

    Sai de duas fontes, e as duas mudam sem reiniciar o programa: a lista
    `hotwords` do `dicionario.json`, que você escreve, e as grafias que o
    programa aprendeu sozinho vendo você corrigir no campo.

    Os termos vão separados por vírgula e com ponto no fim. O reconhecedor imita
    o estilo do que recebe antes da fala: uma fila de palavras soltas, sem
    pontuação, faz a transcrição sair sem vírgula nenhuma.
    """
    import json
    try:
        d = json.loads((DADOS / "dicionario.json").read_text(encoding="utf-8"))
        minhas = d.get("hotwords") or []
    except Exception:
        minhas = []
    termos = list(dict.fromkeys(list(minhas) + list(aprendizado.carregar().values())))
    return ", ".join(termos) + "." if termos else None


if not MAC:
    kernel32 = ctypes.windll.kernel32


# ---------------- bandeja ----------------
# A chama é o ícone da marca, mas a bandeja precisa dizer o estado num quadrado
# de 16 px. Solução: a chama apagada (cinza) quando o modelo não está na GPU, acesa
# quando está, mais um ponto de cor no canto durante gravação e processamento.
CORES = {"ocioso": None, "carregado": None,
         "gravando": (220, 60, 60, 255), "processando": (230, 170, 40, 255)}
_cache_icone = {}


def _icone(estado):
    from PIL import Image, ImageDraw, ImageEnhance
    if estado in _cache_icone:
        return _cache_icone[estado]
    L = 64
    try:
        base = Image.open(BASE / "fogo.png").convert("RGBA").resize((L, L), Image.LANCZOS)
    except Exception:
        # ponytail: sem a arte, o app continua de pé com o círculo de antes.
        base = Image.new("RGBA", (L, L), (0, 0, 0, 0))
        ImageDraw.Draw(base).ellipse([8, 8, L - 8, L - 8], fill=(200, 80, 60, 255))
    if MAC:
        # Na barra de menus do macOS a chama vai branca, no mesmo tom dos ícones
        # que o sistema desenha ao lado.
        silhueta = Image.new("RGBA", base.size, (255, 255, 255, 255))
        silhueta.putalpha(base.getchannel("A"))
        base = silhueta
    elif estado == "ocioso":                     # brasa apagada: modelo fora da GPU
        base = ImageEnhance.Color(base).enhance(0.0)
        base.putalpha(base.getchannel("A").point(lambda a: int(a * 0.55)))
    if (cor := CORES.get(estado)):
        d = ImageDraw.Draw(base)
        r = L // 4
        d.ellipse([L - r - 2, L - r - 2, L - 2, L - 2], fill=cor,
                  outline=(20, 20, 20, 230), width=2)
    _cache_icone[estado] = base
    return base


class WhisperFogo:
    def __init__(self):
        self.modelo = None
        self.gravando = False
        self.blocos = []
        self.stream = None
        self.ultimo_uso = time.time()
        self.tray = None
        self.fila = queue.Queue()       # áudio pronto -> transcrição
        self.fila_cmd = queue.Queue()   # hook de teclado -> abrir/fechar microfone
        self.lock = threading.Lock()
        self.lock_icone = threading.Lock()
        self.timer_corte = None
        self.teclado = None       # preenchido no main, para o corte destravar o atalho
        self.janela = None        # processo da janela de histórico
        self.atualizacao = None   # a release mais nova que a instalada, quando houver
        # Sinaliza ao observador do ditado anterior que a fala recomeçou: é o
        # "next_dictation_started" do Wispr, que encerra a janela de 60 s.
        self.parar_observacao = threading.Event()

    def executor_comandos(self):
        """Tira do hook de teclado tudo que demora (abrir microfone, parar stream)."""
        while True:
            acao = self.fila_cmd.get()
            try:
                if acao == "iniciar" and not self.gravando:
                    self.iniciar()
                elif acao == "parar" and self.gravando:
                    self.parar()
            except Exception as e:
                print(f"[erro de comando] {e}", file=sys.stderr)

    # ---------- estado visual ----------
    def estado_atual(self):
        """O ícone é lido do estado real, nunca passado por quem chama. Três
        threads mexem nele (teclado, transcrição e vigia da GPU), e cada uma só
        enxerga o próprio pedaço: se cada uma pintasse o seu nome, a última a
        pintar venceria, mesmo com uma gravação em curso."""
        if self.gravando:
            return "gravando"
        if self.fila.unfinished_tasks:       # ditado na fila ou sendo transcrito
            return "processando"
        return "carregado" if self.modelo else "ocioso"

    def estado(self):
        if self.tray:
            with self.lock_icone:            # quem pinta por último lê o estado mais novo
                nome = self.estado_atual()
                self.tray.icon = _icone(nome)
                self.tray.title = f"Whisper Fogo ({nome})"
            if MAC:
                threading.Timer(0.3, self._manter_cor).start()

    def _manter_cor(self):
        """Impede o macOS de repintar a chama de preto ou branco.

        Todo ícone da barra de menus é tratado como desenho de sistema por
        padrão, e o sistema o pinta conforme o fundo. Aqui a cor é a da marca, e
        é ela que precisa chegar à tela. A imagem só existe depois que a barra a
        recebe, então a marca é tentada por alguns segundos em vez de uma vez.
        """
        for _ in range(20):
            imagem = getattr(self.tray, "_icon_image", None)
            if imagem is None and getattr(self.tray, "_status_item", None):
                imagem = self.tray._status_item.button().image()
            if imagem is not None:
                try:
                    imagem.setTemplate_(False)
                except Exception:
                    pass
                return
            time.sleep(0.5)

    def liberar_gpu(self):
        self.modelo = None
        self.estado()

    # ---------- modelo ----------
    def carregar(self):
        with self.lock:
            if self.modelo is None:
                from faster_whisper import WhisperModel
                # Placa NVIDIA quando existir; senão CPU em int8, que é o que
                # roda num Mac ou numa máquina sem GPU. Mais lento, mas o
                # programa funciona.
                try:
                    self.modelo = WhisperModel(MODELO, device="cuda", compute_type=COMPUTE)
                except Exception as e:
                    print(f"[sem GPU, indo de CPU] {e}", file=sys.stderr)
                    self.modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
            self.ultimo_uso = time.time()
            return self.modelo

    def vigia_ocioso(self):
        """Devolve a VRAM quando você para de ditar. Gravando ou transcrevendo
        não é ocioso, por mais longa que seja a fala: o modelo fica na GPU e o
        relógio dos 10 minutos só corre depois do último ditado entregue."""
        while True:
            time.sleep(30)
            self.liberar_se_ocioso()

    def liberar_se_ocioso(self):
        with self.lock:
            if self.estado_atual() != "carregado":
                return
            if time.time() - self.ultimo_uso > OCIOSO_MIN * 60:
                self.modelo = None
                import gc
                gc.collect()
                self.estado()

    # ---------- gravação ----------
    def iniciar(self):
        self.blocos = []
        self.parar_observacao.set()          # encerra a observação do ditado anterior

        def captura(dados, frames, tempo, status):
            if self.gravando:
                self.blocos.append(dados.copy())

        # O PortAudio enumera os dispositivos uma vez, ao subir. Sem reinicializar,
        # trocar de microfone (tirar a webcam USB e voltar para o do notebook) só
        # valeria depois de reiniciar o app. Aqui ele relê a cada acionamento e
        # sempre usa o microfone que estiver como padrão no sistema naquele momento.
        try:
            sd._terminate()
            sd._initialize()
            self.stream = sd.InputStream(samplerate=TAXA, channels=1, dtype="float32",
                                         callback=captura, blocksize=1600)
            self.stream.start()
        except Exception as e:
            print(f"[erro de microfone] {e}", file=sys.stderr)
            beep(300, 250)
            self.stream = None
            return

        self.gravando = True
        self.estado()
        beep(880, 80)
        # o timer do ditado anterior tem que morrer aqui: armado, ele encerraria
        # esta gravação no meio da fala
        self._cancelar_corte()
        self.timer_corte = threading.Timer(MAX_SEGUNDOS, self._corte_seguranca)
        self.timer_corte.start()

    def _cancelar_corte(self):
        if self.timer_corte:
            self.timer_corte.cancel()
            self.timer_corte = None

    def _corte_seguranca(self):
        if self.gravando:
            print(f"[corte de segurança: {MAX_SEGUNDOS}s de gravação]", file=sys.stderr)
            # Pela fila, para que só uma thread mexa no microfone. Direto daqui,
            # o corte competia com o hook de teclado pelo mesmo stream.
            self.fila_cmd.put("parar")
            if self.teclado:
                self.teclado.estado = "IDLE"   # senão o próximo atalho só destrava

    def parar(self):
        self.gravando = False
        self._cancelar_corte()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        beep(660, 80)
        # O áudio vai junto na fila: se você acionar o próximo ditado antes de
        # este ser transcrito, o iniciar() zera self.blocos e o ditado sumiria.
        self.fila.put(self.blocos)
        self.blocos = []
        self.estado()

    # ---------- processamento ----------
    def trabalhador(self):
        while True:
            blocos = self.fila.get()
            try:
                self.processar(blocos)
            except Exception as e:
                print(f"[erro] {e}", file=sys.stderr)
                beep(300, 250)
            finally:
                self.ultimo_uso = time.time()
                self.fila.task_done()
                self.estado()

    def processar(self, blocos):
        if not blocos:
            return
        audio = np.concatenate(blocos, axis=0).flatten()
        if len(audio) < TAXA * 0.4:      # menos de 0,4 s: acionamento sem querer
            return

        t0 = time.perf_counter()
        try:
            m = self.carregar()
            # As grafias aprendidas entram como hotword, igual ao "primed
            # dictionary context" do Wispr: melhor o ASR já acertar do que
            # depender da substituição depois.
            segs, _ = m.transcribe(
                audio, language="pt", beam_size=5, vad_filter=True,
                hotwords=hotwords(),
                # Alimentar o próprio texto de volta faz o Whisper entrar em loop
                # de repetição em fala longa, e aí a transcrição nunca termina. É
                # por isso que o padrão do faster-whisper é desligado.
                condition_on_previous_text=False)
            texto = corrigir(" ".join(s.text.strip() for s in segs))
        except Exception:
            self._salvar_audio(audio)    # falhou a transcrição, o áudio não se perde
            raise
        print(f"[{time.perf_counter() - t0:.2f}s para {len(audio) / TAXA:.1f}s de áudio]",
              file=sys.stderr)
        if not texto:
            return

        # Registra ANTES de colar: se não houver campo focado, a colagem cai no
        # vazio, mas o ditado continua recuperável pela janela de histórico.
        try:
            registrar(texto)
        except Exception as e:
            print(f"[histórico não gravou] {e}", file=sys.stderr)

        antigo = clipboard_ler()
        clipboard_escrever(texto)
        time.sleep(0.05)
        colar()
        if antigo is not None:
            # Texto longo demora a entrar no campo de destino; devolver a área de
            # transferência cedo demais colava pela metade.
            threading.Timer(2.5, lambda: clipboard_escrever(antigo)).start()
        self.observar_correcao(texto)

    # ---------- aprendizado pela correção no campo ----------
    def observar_correcao(self, colado):
        """Fica 60 s olhando o campo. Se você corrigir uma palavra ali, vira
        regra de grafia. Espelha o Auto-add to Dictionary do Wispr Flow."""
        self.parar_observacao = threading.Event()
        observador.observar_em_thread(colado, lambda final, motivo:
                                      self._aprender(colado, final, motivo),
                                      self.parar_observacao)

    def _aprender(self, colado, final, motivo):
        try:
            pares = aprendizado.extrair_pares(colado, final)
            novos = aprendizado.registrar(pares)
            if pares:
                print(f"[correção observada: {len(pares)} palavra(s), fim por {motivo}]",
                      file=sys.stderr)
            if novos:
                print(f"[aprendido: {novos}]", file=sys.stderr)
                subprocess.Popen([str(PYTHON_JANELA), str(BASE / "aviso.py")]
                                 + [f"{v}>{n}" for v, n in novos])
        except Exception as e:
            print(f"[aprendizado falhou] {e}", file=sys.stderr)

    def _salvar_audio(self, audio):
        caminho = DADOS / f"falha-{time.strftime('%Y%m%d-%H%M%S')}.wav"
        with wave.open(str(caminho), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(TAXA)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        print(f"[áudio guardado em {caminho.name}]", file=sys.stderr)

    def vigia_atalhos(self):
        """As teclas regravadas no painel valem sem reiniciar: o arquivo é
        conferido a cada segundo e, se mudou, o teclado e o menu acompanham."""
        lido = None
        while True:
            try:
                agora = atalhos.ARQUIVO.stat().st_mtime_ns
            except OSError:
                agora = None
            if agora != lido:
                lido = agora
                if self.teclado:
                    self.teclado.configurar(atalhos.carregar())
                if self.tray:
                    try:
                        self.tray.update_menu()
                    except Exception:
                        pass
            time.sleep(1)

    # ---------- atualização ----------
    def avisar(self, mensagem):
        """Aviso do sistema, saindo do ícone da bandeja."""
        try:
            self.tray.notify(mensagem, "Whisper Fogo")
        except Exception as e:
            print(f"[aviso não saiu] {e}", file=sys.stderr)

    def vigia_atualizacao(self):
        """Confere a versão publicada um pouco depois de abrir, com a máquina já
        de pé e a rede ligada. O programa abre junto com o sistema, então isso
        acontece a cada vez que a máquina reinicia."""
        time.sleep(20)
        self.verificar_atualizacao(manual=False)

    def verificar_atualizacao(self, manual=True):
        try:
            publicada = atualizacao.ultima_publicada()
        except Exception as e:
            print(f"[verificação de atualização falhou] {e}", file=sys.stderr)
            if manual:
                self.avisar("Não deu para verificar agora. Confira a conexão e tente de novo.")
            return
        atual = atualizacao.instalada()
        if publicada and atualizacao.mais_nova(publicada["versao"], atual):
            self.atualizacao = publicada
            self.tray.update_menu()
            self.avisar(f"A versão {publicada['versao']} está disponível. Clique com o botão "
                        f"direito no ícone e escolha “Atualizar para a versão {publicada['versao']}”.")
        elif manual and not publicada:
            self.avisar("Ainda não há versão publicada.")
        elif manual:
            self.avisar(f"Você já está na versão mais recente ({atual}).")

    def atualizar(self):
        """Só com o programa parado: uma transcrição em curso não é interrompida.
        No macOS o programa é um aplicativo assinado, que não se altera depois de
        instalado: lá a atualização abre a página da versão para baixar."""
        publicada = self.atualizacao
        if not publicada:
            return
        if MAC:
            import webbrowser
            webbrowser.open(publicada["pagina"])
            return
        if self.gravando or self.fila.unfinished_tasks:
            self.avisar("Termine a transcrição em curso e tente atualizar de novo.")
            return
        self.avisar(f"Baixando a versão {publicada['versao']}. O programa reinicia sozinho no fim.")

        def trabalho():
            try:
                atualizacao.aplicar(publicada)
            except Exception as e:
                print(f"[atualização falhou] {e}", file=sys.stderr)
                self.avisar(f"Não deu para atualizar ({e}). O programa segue na versão atual.")
                return
            print(f"[atualizado para {publicada['versao']}]", file=sys.stderr)
            reiniciar(self)
        threading.Thread(target=trabalho, daemon=True).start()

    def abrir_historico(self):
        if self.janela and self.janela.poll() is None:
            return                       # já está aberta, não empilha janela
        self.janela = subprocess.Popen([str(PYTHON_JANELA), str(BASE / "historico.py")])



_mutex = None
if not MAC:
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]


def instancia_unica():
    """Segunda instância perde a disputa pelo atalho global e fica muda, sem
    avisar. Melhor sair na hora do que virar defeito silencioso."""
    global _mutex
    if not MAC:
        _mutex = kernel32.CreateMutexW(None, False, "WhisperFogo_instancia_unica")
        return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    # macOS: arquivo de trava com o PID dentro. Se o processo antigo morreu sem
    # limpar, o arquivo fica órfão e a checagem de PID libera a vez.
    trava = DADOS / "instancia.lock"
    try:
        os.kill(int(trava.read_text()), 0)          # não mata, só pergunta se está vivo
        return False
    except Exception:
        pass
    try:
        trava.write_text(str(os.getpid()))
    except Exception:
        pass
    return True


def reiniciar(app):
    """Abre a versão nova e fecha esta. O mutex é solto antes, senão a nova
    instância acharia esta ainda rodando e sairia."""
    if _mutex:
        kernel32.CloseHandle(_mutex)
    pythonw = BASE / ".venv" / "Scripts" / "pythonw.exe"
    subprocess.Popen([str(pythonw), str(BASE / "voz.py")], cwd=str(BASE),
                     creationflags=0x00000008 | 0x00000200)   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    app.tray.stop()


def iniciar_com_o_sistema():
    """O Whisper Fogo abre junto com o Windows, sempre. A entrada é refeita a
    cada abertura, então mudar a pasta do programa não quebra o início
    automático. Quem desligar pelo Gerenciador de Tarefas continua desligado:
    essa escolha o Windows guarda em outro lugar e não é tocada aqui. No macOS
    quem cuida disso é o agente que o instalador registra."""
    if MAC:
        return
    import winreg
    pythonw = BASE / ".venv" / "Scripts" / "pythonw.exe"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE) as chave:
            winreg.SetValueEx(chave, "Whisper Fogo", 0, winreg.REG_SZ,
                              f'"{pythonw}" "{BASE / "voz.py"}"')
    except OSError as e:
        print(f"[início automático não registrado] {e}", file=sys.stderr)


def main():
    import pystray
    ligar_log()
    if not instancia_unica():
        print("Whisper Fogo já está rodando.", file=sys.stderr)
        return
    iniciar_com_o_sistema()
    app = WhisperFogo()
    app.teclado = Teclado(app)
    threading.Thread(target=app.trabalhador, daemon=True).start()
    threading.Thread(target=app.executor_comandos, daemon=True).start()
    threading.Thread(target=app.vigia_ocioso, daemon=True).start()
    threading.Thread(target=app.teclado.rodar, daemon=True).start()
    threading.Thread(target=app.vigia_atalhos, daemon=True).start()
    threading.Thread(target=app.vigia_atualizacao, daemon=True).start()

    # O menu lê as teclas na hora de montar: o que foi regravado no painel aparece
    # aqui. No macOS as teclas são as do sistema.
    if MAC:
        tecla = lambda acao: "Fn+Espaço" if acao == "maos_livres" else "Fn"
    else:
        tecla = lambda acao: atalhos.descrever(atalhos.carregar()[acao], "+")
    from corrigir import recarregar
    menu = pystray.Menu(
        pystray.MenuItem("Painel administrativo", lambda: app.abrir_historico(),
                         default=True),
        pystray.MenuItem(lambda _: f"Segurar {tecla('segurar')}: ditar enquanto segura",
                         None, enabled=False),
        pystray.MenuItem(lambda _: f"{tecla('maos_livres')}: ditar de mãos livres",
                         None, enabled=False),
        pystray.MenuItem(lambda _: f"Encerrar mãos livres: {tecla('encerrar')}",
                         None, enabled=False),
        pystray.MenuItem("Recarregar dicionário", lambda: recarregar()),
        pystray.MenuItem("Liberar a memória agora" if MAC else "Liberar a GPU agora",
                         lambda: app.liberar_gpu()),
        pystray.MenuItem("Verificar atualização",
                         lambda: threading.Thread(target=app.verificar_atualizacao, daemon=True).start()),
        pystray.MenuItem(lambda _: f"Atualizar para a versão {app.atualizacao['versao']}"
                         if app.atualizacao else "", lambda: app.atualizar(),
                         visible=lambda _: app.atualizacao is not None),
        pystray.MenuItem("Sair", lambda ic: ic.stop()),
    )
    app.tray = pystray.Icon("Whisper Fogo", _icone("ocioso"),
                            "Whisper Fogo (ocioso)", menu)

    def preparar(icone):
        # o ícone entra na barra a partir daqui, e é o que faz o desenho ser
        # instalado no lugar dele; o ajuste do tom vem logo depois
        icone.visible = True
        app.estado()

    app.tray.run(setup=preparar)


if __name__ == "__main__":
    main()
