"""Configurações do painel: as teclas de atalho do ditado, com regravação.

Só no Windows: no macOS as teclas são as do sistema (Fn).

Regravar funciona assim: a pessoa clica em Regravar, aperta as teclas e vê a
combinação aparecer; confirma com o mouse. Enquanto grava, o painel escuta o
teclado inteiro e segura as teclas: nem o ditado dispara, nem outro programa
recebe o que foi apertado.
"""
import ctypes
import ctypes.wintypes as wt
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
import atalhos
import tema

OCIOSA = 20           # s sem tecla nenhuma e a gravação se cancela: o teclado nunca fica preso
DESCRICOES = {"segurar": "Segure para gravar; soltar encerra e cola o texto.",
              "maos_livres": "Aperte uma vez para gravar sem precisar segurar.",
              "encerrar": "Com o mãos livres gravando, encerra e cola o texto."}

_LRESULT = ctypes.c_ssize_t
_HOOKPROC = ctypes.WINFUNCTYPE(_LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
_user32 = ctypes.windll.user32
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _HOOKPROC, wt.HINSTANCE, wt.DWORD]
_user32.SetWindowsHookExW.restype = ctypes.c_void_p
_user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wt.WPARAM, wt.LPARAM]
_user32.CallNextHookEx.restype = _LRESULT
_user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(wt.ULONG))]


class Gravador:
    """Escuta o teclado do sistema enquanto uma combinação é gravada.

    O hook de teclado mais novo é chamado primeiro, e este é instalado depois
    do do ditado: engolindo tudo aqui, o ditado nem vê as teclas. Cada tecla
    nova apertada vai para `teclas`, que a tela lê.
    """

    def __init__(self):
        self.teclas = queue.Queue()
        self._baixo = set()
        self._thread_id = None
        self._proc = _HOOKPROC(self._callback)

    def _callback(self, ncode, wparam, lparam):
        if ncode == 0:
            vk = ctypes.cast(lparam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents.vkCode
            if wparam in (0x0100, 0x0104):
                if vk not in self._baixo:
                    self._baixo.add(vk)
                    self.teclas.put(vk)
            elif wparam in (0x0101, 0x0105):
                self._baixo.discard(vk)
            return 1                                 # ninguém mais recebe a tecla
        return _user32.CallNextHookEx(None, ncode, wparam, lparam)

    def iniciar(self):
        pronto = threading.Event()

        def rodar():
            self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
            gancho = _user32.SetWindowsHookExW(13, self._proc, None, 0)   # WH_KEYBOARD_LL
            pronto.set()
            msg = wt.MSG()
            while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
            if gancho:
                _user32.UnhookWindowsHookEx(gancho)

        threading.Thread(target=rodar, daemon=True).start()
        pronto.wait(2)

    def parar(self):
        if self._thread_id:
            _user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)    # WM_QUIT
            self._thread_id = None


def abrir(pai, ao_fechar=None):
    """Abre as configurações como camada por cima do painel, com um × para
    voltar. Devolve a camada."""
    corpo = tkfont.Font(family="Segoe UI", size=11)
    negrito = tkfont.Font(family="Segoe UI", size=11, weight="bold")
    miudo = tkfont.Font(family="Segoe UI", size=9)
    titulo_fonte = tkfont.Font(family="Segoe UI", size=12, weight="bold")

    def botao(pai_, texto, comando, fonte=miudo, **kw):
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 4)
        return tema.botao(pai_, texto, comando, fonte, **kw)

    config = atalhos.carregar()
    gravando = {"acao": None, "teclas": [], "gravador": None, "ultima": 0.0}
    linhas = {}

    def esc():
        cancelar() if gravando["acao"] else fechar()

    def fechar():
        cancelar()
        tema.fechar_camada(janela)
        if ao_fechar:
            ao_fechar()

    janela = tema.abrir_camada(pai, lambda: esc())

    cabeca = tk.Frame(janela, bg=tema.FUNDO)
    cabeca.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(cabeca, text="Configurações", bg=tema.FUNDO, fg=tema.TEXTO,
             font=titulo_fonte).pack(side="left")
    botao(cabeca, "×", lambda: fechar(), fonte=titulo_fonte, cor=tema.PAINEL,
          acesa=tema.VERMELHO, padx=10, pady=0).pack(side="right")

    corpo_tela = tk.Frame(janela, bg=tema.FUNDO)
    corpo_tela.pack(fill="both", expand=True, padx=14, pady=(14, 6))
    tk.Label(corpo_tela, text="Teclas de atalho", bg=tema.FUNDO, fg=tema.TEXTO, font=negrito,
             anchor="w").pack(fill="x")
    tk.Label(corpo_tela, text="Clique em Regravar, aperte as teclas da combinação e confirme "
                              "com o mouse. Enquanto grava, o teclado fica reservado para a gravação.",
             bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w", justify="left",
             wraplength=640).pack(fill="x", pady=(2, 12))

    grade = tk.Frame(corpo_tela, bg=tema.FUNDO)
    grade.pack(fill="x")
    grade.columnconfigure(1, weight=1)
    for n, acao in enumerate(atalhos.ACOES):
        rotulos = tk.Frame(grade, bg=tema.FUNDO)
        rotulos.grid(row=n, column=0, sticky="w", pady=8)
        tk.Label(rotulos, text=atalhos.NOMES[acao], bg=tema.FUNDO, fg=tema.TEXTO, font=corpo,
                 anchor="w").pack(fill="x")
        tk.Label(rotulos, text=DESCRICOES[acao], bg=tema.FUNDO, fg=tema.APAGADO, font=miudo,
                 anchor="w").pack(fill="x")
        valor = tk.Label(grade, text="", bg=tema.PAINEL, fg=tema.TEXTO, font=negrito, anchor="w",
                         padx=12, pady=6, highlightthickness=1, highlightbackground=tema.PAINEL)
        valor.grid(row=n, column=1, sticky="ew", padx=(18, 10))
        acoes = tk.Frame(grade, bg=tema.FUNDO)
        acoes.grid(row=n, column=2, sticky="e")
        linhas[acao] = {
            "valor": valor,
            "regravar": botao(acoes, "Regravar", lambda a=acao: comecar(a), cor=tema.PAINEL,
                              acesa=tema.DESTAQUE),
            "confirmar": botao(acoes, "Confirmar", lambda: confirmar()),
            "limpar": botao(acoes, "Limpar", lambda: limpar(), cor=tema.PAINEL, acesa=tema.DESTAQUE),
            "cancelar": botao(acoes, "Cancelar", lambda: cancelar(), cor=tema.PAINEL,
                              acesa=tema.VERMELHO),
        }
        valor.bind("<Button-1>", lambda _e, a=acao: comecar(a))
        valor.configure(cursor="hand2")

    rodape_acoes = tk.Frame(corpo_tela, bg=tema.FUNDO)
    rodape_acoes.pack(fill="x", pady=(18, 0))
    restaurar_btn = botao(rodape_acoes, "Restaurar padrão", lambda: restaurar(), cor=tema.PAINEL,
                          acesa=tema.DESTAQUE)
    restaurar_btn.pack(side="left")

    rodape = tk.Label(janela, text="", bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w")
    rodape.pack(fill="x", padx=14, pady=(0, 12))

    def avisar(mensagem, erro=False):
        rodape.config(text=mensagem, fg=tema.VERMELHO_CLARO if erro else tema.DESTAQUE)
        if not erro:
            janela.after(4000, lambda: rodape.winfo_exists() and rodape.cget("text") == mensagem
                         and rodape.config(text=""))

    def desenhar():
        for acao, linha in linhas.items():
            em_gravacao = gravando["acao"] == acao
            if em_gravacao:
                teclas = gravando["teclas"]
                texto = atalhos.descrever(teclas) if teclas else "Aperte as teclas…"
                linha["valor"].config(text=texto, fg=tema.TEXTO if teclas else tema.APAGADO,
                                      highlightbackground=tema.DESTAQUE)
            else:
                linha["valor"].config(text=atalhos.descrever(config[acao]), fg=tema.TEXTO,
                                      highlightbackground=tema.PAINEL)
            for nome in ("regravar", "confirmar", "limpar", "cancelar"):
                linha[nome].pack_forget()
            if em_gravacao:
                linha["confirmar"].config(state="normal" if gravando["teclas"] else "disabled",
                                          bg=tema.DESTAQUE if gravando["teclas"] else tema.PAINEL)
                for nome in ("cancelar", "limpar", "confirmar"):
                    linha[nome].pack(side="right", padx=(6, 0))
            else:
                linha["regravar"].config(state="disabled" if gravando["acao"] else "normal")
                linha["regravar"].pack(side="right")
        restaurar_btn.config(state="disabled" if gravando["acao"] else "normal")

    def comecar(acao):
        if gravando["acao"]:
            return
        gravando.update(acao=acao, teclas=[], gravador=Gravador(), ultima=time.monotonic())
        gravando["gravador"].iniciar()
        rodape.config(text="")
        desenhar()
        janela.after(30, escutar)

    def escutar():
        """Lê as teclas que o gravador pegou e mostra na hora."""
        if not gravando["acao"] or not janela.winfo_exists():
            return
        mudou = False
        while True:
            try:
                vk = gravando["gravador"].teclas.get_nowait()
            except queue.Empty:
                break
            gravando["ultima"] = time.monotonic()
            if vk not in gravando["teclas"]:
                gravando["teclas"].append(vk)
                mudou = True
        if mudou:
            gravando["teclas"] = atalhos.ordenar(gravando["teclas"])
            desenhar()
        if time.monotonic() - gravando["ultima"] > OCIOSA:
            cancelar()
            avisar(f"Gravação cancelada depois de {OCIOSA} s sem nenhuma tecla.", erro=True)
            return
        janela.after(30, escutar)

    def parar_gravador():
        if gravando["gravador"]:
            gravando["gravador"].parar()
        gravando.update(acao=None, teclas=[], gravador=None)

    def limpar():
        gravando["teclas"] = []
        gravando["ultima"] = time.monotonic()
        desenhar()

    def cancelar():
        if gravando["acao"]:
            parar_gravador()
            if janela.winfo_exists():
                desenhar()

    def confirmar():
        acao, teclas = gravando["acao"], list(gravando["teclas"])
        if not acao or not teclas:
            return
        novo = {**config, acao: teclas}
        try:
            gravado = atalhos.gravar(novo)
        except ValueError as e:
            avisar(str(e), erro=True)            # segue gravando: dá para limpar e tentar de novo
            return
        parar_gravador()
        config.update(gravado)
        desenhar()
        avisar(f"“{atalhos.NOMES[acao]}” agora é {atalhos.descrever(teclas)}. Já vale na próxima transcrição.")

    def restaurar():
        config.update(atalhos.gravar({a: list(atalhos.PADRAO[a]) for a in atalhos.ACOES}))
        desenhar()
        avisar("Teclas de volta ao padrão.")

    desenhar()
    tema.mostrar_camada(janela)         # entra na tela já pronta
    return janela


if __name__ == "__main__":
    atalhos._demo()
