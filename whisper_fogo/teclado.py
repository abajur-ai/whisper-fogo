"""Atalho global de teclado, por sistema operacional.

O comportamento copiado do Wispr Flow, e que o `RegisterHotKey` do Windows não
alcança: reagir a modificador sozinho, sem tecla comum junto, e reagir à soltura
da tecla. Por isso é hook de baixo nível no Windows e escuta global no macOS.

No Windows as três combinações (segurar, mãos livres e encerrar) vêm do
atalhos.json e podem ser regravadas pelo painel, com o programa aberto. O padrão
é o do Wispr Flow: Ctrl+Shift para segurar e Ctrl+Shift+Espaço para mãos livres.

No macOS as teclas são as que o Wispr Flow usa lá: a Fn no lugar do par de
modificadores. A leitura do teclado depende da permissão de Acessibilidade, e a
escuta só nasce depois que ela está valendo. Ver a seção do README.
"""
import sys
import threading
import time

MAC = sys.platform == "darwin"

SEGURAR_MS = 250        # tempo com a combinação de segurar parada antes de virar gravação

if not MAC:
    import ctypes
    import ctypes.wintypes as wt

    import atalhos

    user32 = ctypes.windll.user32

    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wt.WPARAM, wt.LPARAM]
    user32.CallNextHookEx.restype = LRESULT


    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                    ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(wt.ULONG))]


    class Teclado:
        """Reproduz o comportamento do Wispr Flow, que o RegisterHotKey não alcança:
        ele precisa reagir a modificadores sozinhos e à soltura de tecla. As três
        combinações vêm do atalhos.json e podem mudar com o programa aberto.

        IDLE    -> segura SEGURAR por SEGURAR_MS .............. grava enquanto segurar
                -> completa MÃOS LIVRES ....................... grava de mãos livres
        PTT     -> soltou uma tecla de SEGURAR ................ encerra e cola
                -> completou MÃOS LIVRES no meio .............. vira mãos livres
        TRAVADO -> completou ENCERRAR ......................... encerra e cola

        Tecla comum que completa uma combinação é engolida (senão o Espaço do mãos
        livres entraria no campo), junto com a repetição e a soltura dela.
        Modificador nunca é engolido.
        """

        def __init__(self, app, config=None):
            self.app = app
            self.baixo = set()
            self.engolidas = set()
            self.estado = "IDLE"
            self.cancelado = False       # outra tecla entrou: era atalho comum
            self.timer = None
            self.configurar(config or atalhos.carregar())
            self.proc = HOOKPROC(self._callback)

        def configurar(self, config):
            # Uma tupla trocada de uma vez: o hook nunca lê metade da configuração nova.
            self.combos = (frozenset(config["segurar"]), frozenset(config["maos_livres"]),
                           frozenset(config["encerrar"]))

        # o callback do hook tem orçamento de milissegundos: só mexe em flag e sai.
        def _callback(self, ncode, wparam, lparam):
            if ncode == 0:
                info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = info.vkCode
                if wparam in (0x0100, 0x0104):      # WM_KEYDOWN / WM_SYSKEYDOWN
                    if vk in self.baixo:
                        if vk in self.engolidas:
                            return 1                # repetição de tecla engolida
                    else:
                        self.baixo.add(vk)
                        if self._descer(vk):
                            self.engolidas.add(vk)
                            return 1
                elif wparam in (0x0101, 0x0105):    # WM_KEYUP / WM_SYSKEYUP
                    self.baixo.discard(vk)
                    self._subir(vk)
                    if vk in self.engolidas:
                        self.engolidas.discard(vk)
                        return 1
            return user32.CallNextHookEx(None, ncode, wparam, lparam)

        def _descer(self, vk):
            """Devolve True quando a tecla deve ser engolida."""
            segurar, maos, encerrar = self.combos
            comum = vk not in atalhos.MODIFICADORES
            if self.estado == "TRAVADO":
                if vk in encerrar and encerrar <= self.baixo:
                    self._parar()
                    self.estado = "ENCERRANDO"
                    return comum
                return False
            if self.estado in ("IDLE", "ARMADO", "PTT") and vk in maos and maos <= self.baixo:
                self._cancelar_timer()
                if self.estado != "PTT":
                    self.app.fila_cmd.put("iniciar")
                self.estado = "TRAVADO"
                return comum
            if self.estado == "IDLE" and vk in segurar and segurar <= self.baixo:
                self.estado = "ARMADO"
                self.cancelado = False
                self.timer = threading.Timer(SEGURAR_MS / 1000, self._virar_ptt)
                self.timer.start()
                return comum
            if self.estado == "ARMADO" and vk not in segurar and vk not in maos:
                self.cancelado = True               # combinação + outra coisa: atalho normal
                self._cancelar_timer()
                self.estado = "IGNORANDO"
            return False

        def _subir(self, vk):
            segurar, maos, encerrar = self.combos
            if self.estado == "PTT" and vk in segurar:
                self._parar()
                self.estado = "IDLE"
            elif self.estado in ("ARMADO", "IGNORANDO", "ENCERRANDO") and vk in segurar | maos | encerrar:
                self._cancelar_timer()
                self.estado = "IDLE"

        def _virar_ptt(self):
            if self.estado == "ARMADO" and not self.cancelado and self.combos[0] <= self.baixo:
                self.estado = "PTT"
                self.app.fila_cmd.put("iniciar")

        def _parar(self):
            self.app.fila_cmd.put("parar")

        def _cancelar_timer(self):
            if self.timer:
                self.timer.cancel()
                self.timer = None

        def rodar(self):
            h = user32.SetWindowsHookExW(13, self.proc, None, 0)  # WH_KEYBOARD_LL
            if not h:
                print("[erro] hook de teclado recusado", file=sys.stderr)
                return
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))


else:
    # --------------------------------------------------------------- macOS
    def esperar_confianca(intervalo=2.0):
        """Só devolve o controle quando o macOS liberar a leitura do teclado.

        Ler tecla fora da própria janela depende da permissão de Acessibilidade,
        e o sistema responde conforme o estado do momento: marcar a caixa em
        Ajustes muda a resposta na hora, sem precisar abrir o programa de novo.
        A primeira consulta pede a permissão pela janela do próprio macOS, que
        já leva ao painel certo.
        """
        try:
            from ApplicationServices import (AXIsProcessTrusted,
                                             AXIsProcessTrustedWithOptions,
                                             kAXTrustedCheckOptionPrompt)
        except ImportError:
            return

        if AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}):
            return

        print("[o atalho global espera a permissão de Acessibilidade em Ajustes "
              "do Sistema, Privacidade e Segurança]", file=sys.stderr)
        while not AXIsProcessTrusted():
            time.sleep(intervalo)
        print("[permissão de Acessibilidade concedida, atalho no ar]", file=sys.stderr)

    # Teclas do Wispr Flow no macOS, lidas da configuração dele: a Fn sozinha
    # grava enquanto segura e a Fn com espaço grava de mãos livres. São os
    # códigos do sistema.
    ESPACO = 49
    MASCARA_FN = 0x800000

    class Teclado:
        """Mesma máquina de estados, ouvindo o teclado pelo Quartz.

        A Fn não chega como tecla comum: ela vira um sinalizador no evento de
        mudança de modificadores, e é por isso que a escuta acontece nesse nível
        em vez de na camada de teclas.

            IDLE    -> segura Fn por SEGURAR_MS ......... grava enquanto segurar
                    -> Fn + Espaço ..................... grava de mãos livres
            PTT     -> soltou Fn ....................... encerra e cola
                    -> apertou Espaço no meio .......... vira mãos livres
            TRAVADO -> Fn de novo ...................... encerra e cola
        """

        def __init__(self, app, config=None):
            self.app = app
            self.estado = "IDLE"
            self.timer = None
            self.fn_baixa = False
            self.ja_viu_fn = False

        def configurar(self, config):
            """No macOS as teclas são as do sistema (Fn): não há o que trocar."""

        def _evento(self, proxy, tipo, evento, refcon):
            from Quartz import (CGEventGetFlags, CGEventGetIntegerValueField,
                                kCGEventFlagsChanged, kCGKeyboardEventKeycode)
            try:
                flags = CGEventGetFlags(evento)
                if tipo == kCGEventFlagsChanged:
                    fn = bool(flags & MASCARA_FN)
                    if fn and not self.fn_baixa:
                        self.fn_baixa = True
                        if not self.ja_viu_fn:      # confirma a escuta, uma vez
                            self.ja_viu_fn = True
                            print("[tecla Fn reconhecida]", file=sys.stderr)
                        self._fn_desceu()
                    elif not fn and self.fn_baixa:
                        self.fn_baixa = False
                        self._fn_subiu()
                elif self.fn_baixa and CGEventGetIntegerValueField(
                        evento, kCGKeyboardEventKeycode) == ESPACO:
                    self._espaco()
            except Exception as e:
                print(f"[teclado] {type(e).__name__}: {e}", file=sys.stderr)
            return evento

        def _fn_desceu(self):
            if self.estado == "TRAVADO":
                self._parar()
                self.estado = "ENCERRANDO"
            elif self.estado == "IDLE":
                self.estado = "ARMADO"
                self.timer = threading.Timer(SEGURAR_MS / 1000, self._virar_ptt)
                self.timer.start()

        def _fn_subiu(self):
            if self.estado == "PTT":
                self._parar()
                self.estado = "IDLE"
            elif self.estado in ("ARMADO", "ENCERRANDO"):
                self._cancelar_timer()
                self.estado = "IDLE"

        def _espaco(self):
            if self.estado in ("ARMADO", "PTT"):
                self._cancelar_timer()
                if self.estado == "ARMADO":
                    self.app.fila_cmd.put("iniciar")
                self.estado = "TRAVADO"

        def _virar_ptt(self):
            if self.estado == "ARMADO" and self.fn_baixa:
                self.estado = "PTT"
                self.app.fila_cmd.put("iniciar")

        def _parar(self):
            self.app.fila_cmd.put("parar")

        def _cancelar_timer(self):
            if self.timer:
                self.timer.cancel()
                self.timer = None

        def rodar(self):
            from Quartz import (CFMachPortCreateRunLoopSource, CFRunLoopAddSource,
                                CFRunLoopGetCurrent, CFRunLoopRun, CGEventMaskBit,
                                CGEventTapCreate, CGEventTapEnable, kCFRunLoopCommonModes,
                                kCGEventFlagsChanged, kCGEventKeyDown,
                                kCGHeadInsertEventTap, kCGSessionEventTap,
                                kCGEventTapOptionListenOnly)
            # a escuta nasce depois da liberação, senão ela sobe surda
            esperar_confianca()
            tap = CGEventTapCreate(
                kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionListenOnly,
                CGEventMaskBit(kCGEventFlagsChanged) | CGEventMaskBit(kCGEventKeyDown),
                self._evento, None)
            if not tap:
                print("[erro] não consegui ouvir o teclado", file=sys.stderr)
                return
            fonte = CFMachPortCreateRunLoopSource(None, tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), fonte, kCFRunLoopCommonModes)
            CGEventTapEnable(tap, True)
            CFRunLoopRun()
