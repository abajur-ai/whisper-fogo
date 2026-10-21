"""Prova que a gravação só termina quando você manda, por mais longa que seja.

Cada gravação arma um corte de segurança (uma hora), e o corte da gravação
anterior é cancelado quando a seguinte começa. Também prova que o ícone da
bandeja segue o estado real em fala longa.

Roda sem microfone e sem GPU: o InputStream é falso e o modelo nunca é chamado.
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import voz


class StreamFalso:
    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


def preparar():
    voz.beep = lambda *a: None                # teste silencioso
    # Só o InputStream é falso: o _terminate do sounddevice fica o verdadeiro,
    # para o PortAudio encerrar e o processo do teste sair limpo.
    voz.sd.InputStream = lambda **kw: StreamFalso()
    app = voz.WhisperFogo()
    threading.Thread(target=app.executor_comandos, daemon=True).start()
    return app


def teste_timer_antigo_nao_derruba_o_ditado_seguinte():
    app = preparar()
    voz.MAX_SEGUNDOS = 0.5                    # ditado curto, teto curto
    app.iniciar()
    app.parar()
    voz.MAX_SEGUNDOS = 60                     # o próximo ditado tem teto folgado
    app.iniciar()
    time.sleep(1.5)                           # bem além do teto do ditado anterior
    assert app.gravando, "o timer do ditado anterior derrubou a gravação seguinte"
    app.parar()


def teste_corte_de_seguranca_ainda_funciona():
    app = preparar()
    voz.MAX_SEGUNDOS = 0.5
    app.teclado = type("T", (), {"estado": "TRAVADO"})()
    app.iniciar()
    time.sleep(1.5)
    assert not app.gravando, "o corte de segurança parou de agir"
    assert app.teclado.estado == "IDLE", "o atalho ficaria travado depois do corte"


def teste_audio_nao_some_quando_o_proximo_ditado_comeca():
    app = preparar()
    voz.MAX_SEGUNDOS = 60
    app.iniciar()
    app.blocos = ["áudio do primeiro ditado"]
    app.parar()
    app.iniciar()                             # zera self.blocos
    blocos = app.fila.get_nowait()
    assert blocos == ["áudio do primeiro ditado"], "o ditado anterior foi perdido"
    app.parar()


class BandejaFalsa:
    icon = None
    title = ""


def teste_icone_segue_o_estado_real_em_gravacao_longa():
    app = preparar()
    voz.MAX_SEGUNDOS = 60
    app.tray = BandejaFalsa()
    liberado = threading.Event()
    app.modelo = type("M", (), {"liberar": lambda self: liberado.set()})()   # modelo na GPU
    app.iniciar()
    assert app.tray.title.endswith("(gravando)")
    app.ultimo_uso = time.time() - voz.OCIOSO_MIN * 60 - 1   # fala já passou dos 10 min
    app.liberar_se_ocioso()                   # a olhada do vigia no meio da fala
    assert app.modelo is not None, "o vigia descarregou o modelo no meio da gravação"
    assert app.tray.title.endswith("(gravando)"), "o ícone ficou cinza no meio da gravação"

    app.parar()
    assert app.tray.title.endswith("(processando)")
    app.liberar_se_ocioso()                   # transcrevendo também não é ocioso
    assert app.tray.title.endswith("(processando)")

    app.processar = lambda *a: None           # transcrição falsa, sem GPU
    threading.Thread(target=app.trabalhador, daemon=True).start()
    app.fila.join()
    time.sleep(0.05)
    assert app.tray.title.endswith("(carregado)")
    app.liberar_se_ocioso()                   # relógio recomeça no ditado entregue
    assert app.tray.title.endswith("(carregado)")

    app.ultimo_uso = time.time() - voz.OCIOSO_MIN * 60 - 1   # agora sim, 10 min parado
    app.liberar_se_ocioso()
    assert app.modelo is None and app.tray.title.endswith("(ocioso)")
    assert liberado.wait(2), "o motor não saiu da placa"


if __name__ == "__main__":
    teste_timer_antigo_nao_derruba_o_ditado_seguinte()
    teste_corte_de_seguranca_ainda_funciona()
    teste_audio_nao_some_quando_o_proximo_ditado_comeca()
    teste_icone_segue_o_estado_real_em_gravacao_longa()
    print("teste_corte: 4/4 ok")
