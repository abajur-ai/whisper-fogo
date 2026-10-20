"""Teclas de atalho do ditado: o padrão, o arquivo onde a pessoa grava as dela e
o nome de cada tecla do jeito que aparece na tela.

Três ações, cada uma uma combinação de teclas (códigos de tecla do Windows):
segurar para ditar, ditar de mãos livres e encerrar o mãos livres. O programa
do ditado relê o arquivo quando ele muda, então a combinação nova vale na hora.
"""
import ctypes
import json
import os
import time
from pathlib import Path

from caminhos import DADOS
ARQUIVO = DADOS / "atalhos.json"

ACOES = ("segurar", "maos_livres", "encerrar")
NOMES = {"segurar": "Ditar enquanto segura",
         "maos_livres": "Ditar de mãos livres",
         "encerrar": "Encerrar mãos livres"}
# Os do Wispr Flow no Windows, lidos do splitKeybinds dele: Ctrl esquerdo + Shift
# esquerdo para segurar, os dois mais Espaço para mãos livres.
PADRAO = {"segurar": [0xA2, 0xA0], "maos_livres": [0xA2, 0xA0, 0x20], "encerrar": [0xA2, 0xA0]}

# Tecla que só modifica outra. Ela nunca é engolida pelo ditado: engolir Ctrl ou
# Shift deixaria os outros programas achando que a tecla continua apertada.
MODIFICADORES = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}
_ORDEM = [0xA2, 0xA3, 0x11, 0xA0, 0xA1, 0x10, 0xA4, 0xA5, 0x12, 0x5B, 0x5C]

_NOMES_TECLAS = {
    0xA2: "Ctrl", 0xA3: "Ctrl direito", 0x11: "Ctrl", 0xA0: "Shift", 0xA1: "Shift direito",
    0x10: "Shift", 0xA4: "Alt", 0xA5: "AltGr", 0x12: "Alt", 0x5B: "Windows", 0x5C: "Windows direito",
    0x20: "Espaço", 0x0D: "Enter", 0x09: "Tab", 0x1B: "Esc", 0x08: "Backspace", 0x2E: "Delete",
    0x2D: "Insert", 0x24: "Home", 0x23: "End", 0x21: "Page Up", 0x22: "Page Down",
    0x25: "Seta esquerda", 0x26: "Seta para cima", 0x27: "Seta direita", 0x28: "Seta para baixo",
    0x14: "Caps Lock", 0x2C: "Print Screen", 0x13: "Pause", 0x91: "Scroll Lock", 0x5D: "Menu",
}


def nome_tecla(vk):
    if vk in _NOMES_TECLAS:
        return _NOMES_TECLAS[vk]
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x60 <= vk <= 0x69:
        return f"Num {vk - 0x60}"
    try:                                        # o nome que o próprio Windows dá
        buf = ctypes.create_unicode_buffer(64)
        codigo = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        if codigo and ctypes.windll.user32.GetKeyNameTextW(codigo << 16, buf, 64):
            return buf.value
    except Exception:
        pass
    return f"Tecla {vk}"


def ordenar(teclas):
    """Modificadores primeiro, na ordem de costume (Ctrl, Shift, Alt, Windows),
    depois as outras na ordem em que foram apertadas. Sem repetição."""
    unicas = list(dict.fromkeys(teclas))
    mods = sorted((t for t in unicas if t in MODIFICADORES), key=_ORDEM.index)
    return mods + [t for t in unicas if t not in MODIFICADORES]


def descrever(teclas, junta=" + "):
    return junta.join(nome_tecla(t) for t in ordenar(teclas))


def validar(config):
    """Recusa combinação que o teclado não consegue distinguir. Erro em
    português, do jeito que aparece no rodapé da tela."""
    for acao in ACOES:
        if not config.get(acao):
            raise ValueError(f"Grave ao menos uma tecla para “{NOMES[acao]}”.")
        if len(set(config[acao])) > 4:
            raise ValueError(f"“{NOMES[acao]}” aceita no máximo 4 teclas.")
    segurar, maos = set(config["segurar"]), set(config["maos_livres"])
    if maos <= segurar:
        # Mãos livres contido no segurar dispara antes: o segurar nunca chegaria.
        raise ValueError(f"“{NOMES['maos_livres']}” não pode ser igual a "
                         f"“{NOMES['segurar']}” nem estar contido nele.")


def carregar():
    """A combinação de cada ação. Arquivo ausente, ilegível ou com combinação
    inválida cai no padrão, para o ditado nunca ficar sem atalho."""
    try:
        lido = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        config = {a: [int(t) for t in lido.get(a, PADRAO[a])] for a in ACOES}
        validar(config)
        return config
    except Exception:
        return {a: list(PADRAO[a]) for a in ACOES}


def gravar(config):
    """Valida e grava num arquivo ao lado, trocando de uma vez: o ditado relê o
    arquivo sozinho e nunca pode ver a gravação pela metade."""
    config = {a: ordenar(config[a]) for a in ACOES}
    validar(config)
    temporario = ARQUIVO.with_name(ARQUIVO.name + ".tmp")
    temporario.write_text(json.dumps(config, indent=2), encoding="utf-8")
    for _ in range(20):
        try:
            os.replace(temporario, ARQUIVO)
            return config
        except PermissionError:
            time.sleep(0.05)
    os.replace(temporario, ARQUIVO)
    return config


def _demo():
    import tempfile
    global ARQUIVO
    verdadeiro = ARQUIVO
    with tempfile.TemporaryDirectory() as pasta:
        ARQUIVO = Path(pasta) / "atalhos.json"
        assert carregar() == PADRAO                                  # sem arquivo: padrão
        assert descrever(PADRAO["maos_livres"]) == "Ctrl + Shift + Espaço"
        assert descrever([0x20, 0xA0, 0xA2], "+") == "Ctrl+Shift+Espaço"   # modificador primeiro
        assert nome_tecla(0x7C) == "F13" and nome_tecla(0x41) == "A" and nome_tecla(0x65) == "Num 5"

        novo = {"segurar": [0x7D], "maos_livres": [0x7C], "encerrar": [0x7C]}
        assert gravar(novo) == novo and carregar() == novo
        for errado in ({**novo, "encerrar": []},
                       {**novo, "maos_livres": [0x7D]},                      # igual ao segurar
                       {"segurar": [0xA2, 0xA0, 0xA4], "maos_livres": [0xA2, 0xA0], "encerrar": [0xA2]},
                       {**novo, "segurar": [0x41, 0x42, 0x43, 0x44, 0x45]}):
            try:
                gravar(errado)
                raise AssertionError(f"aceitou {errado}")
            except ValueError:
                pass
        assert carregar() == novo, "gravação recusada não pode mexer no arquivo"
        ARQUIVO.write_text("{quebrado", encoding="utf-8")
        assert carregar() == PADRAO                                  # ilegível: padrão
        assert not ARQUIVO.with_name("atalhos.json.tmp").exists()
    ARQUIVO = verdadeiro
    print("atalhos.py: autoteste ok")


if __name__ == "__main__":
    _demo()
