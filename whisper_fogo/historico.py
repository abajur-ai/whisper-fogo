"""Painel administrativo e histórico de transcrições: nada do que foi falado se perde.

Toda transcrição entra no jsonl ANTES de ir para a área de transferência. Se não
houver campo de texto focado, a colagem cai no vazio, mas o texto continua aqui
para ser copiado depois. É o que o Wispr Flow faz e é o motivo de quem usa
confiar nele.

A janela abre em processo separado de propósito: o pystray ocupa a thread
principal do ditado, e um Tk lá dentro derruba o app inteiro se travar. Aqui, o
pior caso é a janela morrer sozinha, com o ditado intacto.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from caminhos import CODIGO, DADOS, MAC
ARQUIVO = DADOS / "historico.jsonl"
LOTE = 200            # a lista cresce com o uso: carrega de 200 em 200 conforme a rolagem desce
PREVIA = 160          # teto grosseiro da prévia: quem corta de verdade é a medida em pixel
RESPIRO = 12          # px que o título nunca invade, para não encostar na barra de rolagem
INTERVALO = 1000      # ms entre uma olhada e outra no arquivo, para o ditado novo entrar sozinho
MUTEX = "WhisperFogo_instancia_unica"   # o mesmo que o voz.py cria ao subir
PARTIDA = 30          # s que o programa tem para subir antes de a janela desistir dele


def programa_rodando():
    """O mutex existe enquanto o processo do ditado estiver vivo, e some com ele.
    No macOS a mesma pergunta é feita ao arquivo de trava, que guarda o PID."""
    if MAC:
        try:
            os.kill(int((DADOS / "instancia.lock").read_text()), 0)
            return True
        except Exception:
            return False
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenMutexW(0x00100000, False, MUTEX)   # SYNCHRONIZE: só para saber se existe
    if h:
        k32.CloseHandle(h)
    return bool(h)


def ligar_programa():
    """Painel não existe sem o programa: quem abre a janela pelo atalho do
    teclado sobe o ditado junto. O voz.py continua vivo se a janela fechar."""
    if MAC:
        python = Path(sys.executable)
    else:
        import executavel
        python = executavel.garantir()
    subprocess.Popen([str(python), str(CODIGO / "voz.py")], cwd=str(CODIGO))


def registrar(texto):
    """Append puro: não lê, não reescreve, não trava o ditado se o disco engasgar."""
    linha = json.dumps({"quando": time.strftime("%d/%m/%Y %H:%M"),
                        "texto": texto}, ensure_ascii=False)
    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def carregar():
    if not ARQUIVO.exists():
        return []
    itens = []
    for linha in ARQUIVO.read_text(encoding="utf-8").splitlines():
        try:
            itens.append(json.loads(linha))
        except ValueError:
            pass      # linha truncada por queda no meio da escrita: ignora e segue
    return itens[::-1]


def numero(n):
    return f"{n:,}".replace(",", ".")


def transcricoes(n):
    return f"{numero(n)} transcrição" if n == 1 else f"{numero(n)} transcrições"


def apagar(selecionados):
    """Tira do arquivo os ditados escolhidos e devolve quantos saíram.

    O programa do ditado pode acrescentar uma linha a qualquer momento, então a
    regravação vai para um arquivo ao lado e só substitui o original se ele não
    cresceu no meio do caminho; se cresceu, refaz com o conteúdo novo. Cada
    ditado é reconhecido por data e texto, contados: dois ditados idênticos no
    mesmo minuto são indistinguíveis, e escolher um apaga exatamente um.
    Linha ilegível nunca é apagada.
    """
    if not ARQUIVO.exists():
        return 0
    temporario = ARQUIVO.with_name(ARQUIVO.name + ".tmp")
    for _ in range(20):
        alvo = Counter((it["quando"], it["texto"]) for it in selecionados)
        bruto = ARQUIVO.read_bytes()
        manter, removidos = [], 0
        for linha in bruto.decode("utf-8", "replace").splitlines(keepends=True):
            try:
                d = json.loads(linha)
                chave = (d["quando"], d["texto"])
            except (ValueError, KeyError, TypeError):
                manter.append(linha)
                continue
            if alvo[chave] > 0:
                alvo[chave] -= 1
                removidos += 1
            else:
                manter.append(linha)
        temporario.write_bytes("".join(manter).encode("utf-8"))
        try:
            if ARQUIVO.stat().st_size == len(bruto):
                os.replace(temporario, ARQUIVO)
                return removidos
        except PermissionError:
            pass      # o ditado estava gravando naquele instante: tenta de novo
        time.sleep(0.05)
    temporario.unlink(missing_ok=True)
    raise OSError("o histórico estava em uso e não pôde ser regravado")


def ler_novos(posicao):
    """Lê só o que foi acrescentado desde a última leitura.

    Devolve (ditados novos, nova posição, se o arquivo recomeçou). A posição é
    em bytes e não em linha porque só ela é barata de retomar, e acentuação
    ocupa mais de um byte. Linha ainda sem quebra fica para a rodada seguinte:
    é escrita em andamento, não linha corrompida.
    """
    if not ARQUIVO.exists():
        return [], 0, posicao > 0
    tamanho = ARQUIVO.stat().st_size
    recomecou = tamanho < posicao         # histórico limpo ou arquivo trocado
    inicio = 0 if recomecou else posicao
    if tamanho == inicio:
        return [], inicio, recomecou
    with open(ARQUIVO, "rb") as f:
        f.seek(inicio)
        bruto = f.read()
    if b"\n" not in bruto:
        return [], inicio, recomecou
    completo = bruto.rsplit(b"\n", 1)[0] + b"\n"
    novos = []
    for linha in completo.decode("utf-8", "replace").splitlines():
        try:
            novos.append(json.loads(linha))
        except ValueError:
            pass
    return novos, inicio + len(completo), recomecou


def rotular(item):
    """Uma linha da lista: quando, e o começo do que foi dito. Quem corta no
    tamanho da coluna é tema.encurtar."""
    return f"  {item['quando']}  {' '.join(item['texto'].split())[:PREVIA]}"


def ligar_log():
    """O painel roda sem console: erro, e até queda do interpretador, vão para o
    painel.log em vez de sumir."""
    if sys.stderr is None or not sys.stderr.isatty():
        try:
            import faulthandler
            log = open(DADOS / "painel.log", "a", encoding="utf-8", buffering=1)
            sys.stderr = sys.stdout = log
            faulthandler.enable(log)
            print(f"\n=== painel aberto {time.strftime('%d/%m/%Y %H:%M')} ===", file=log)
        except Exception:
            pass


def main():
    import tkinter as tk
    from tkinter import font as tkfont
    ligar_log()
    sys.path.insert(0, str(BASE))
    from clip import escrever
    import tema

    todos = carregar()
    posicao = [ARQUIVO.stat().st_size if ARQUIVO.exists() else 0]
    raiz = tk.Tk()
    raiz.title("Whisper Fogo: painel administrativo")
    raiz.geometry("980x600")
    raiz.minsize(820, 440)        # a tela de grafias abre por cima e precisa disso
    icone = CODIGO / "fogo.ico"
    if icone.exists():
        try:
            # o `default` vale para a janela e a barra de tarefas, e existe só no
            # Windows. No macOS a janela já nasce com o ícone do aplicativo.
            raiz.iconbitmap(default=str(icone))
        except tk.TclError:
            pass
    tema.aplicar(raiz)                        # fundo e barra de título na cor da marca
    tema.barra_de_titulo(raiz, "Whisper Fogo: painel administrativo")

    corpo = tkfont.Font(family="Segoe UI", size=11)
    miudo = tkfont.Font(family="Segoe UI", size=9)
    botao_fonte = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    VERMELHO, VERMELHO_CLARO = tema.VERMELHO, tema.VERMELHO_CLARO
    DICA = "Enter ou duplo clique também copia. Esc fecha."

    def botao(pai, texto_, comando, fonte=botao_fonte, **kw):
        return tema.botao(pai, texto_, comando, fonte, **kw)

    # Estado da lista: quantos já carregaram e, no modo de limpeza, os marcados.
    limpando = [False]
    marcados = set()          # id() dos ditados: a lista é recarregada inteira ao apagar
    na_tela = []              # os ditados já carregados na lista, na mesma ordem dela

    topo = tk.Frame(raiz, bg=tema.FUNDO)
    topo.pack(fill="x", padx=14, pady=(12, 6))
    contador = tk.Label(topo, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=corpo)
    contador.pack(side="left", padx=(10, 0))
    limpar_btn = botao(topo, "Limpar histórico", lambda: entrar_limpeza(), cor=VERMELHO,
                       acesa=VERMELHO_CLARO, fonte=miudo, padx=12, pady=4)
    limpar_btn.pack(side="left", padx=(0, 4), before=contador)
    apagar_btn = botao(topo, "", lambda: confirmar(), cor=VERMELHO, acesa=VERMELHO_CLARO,
                       fonte=miudo, padx=12, pady=4)
    cancelar_btn = botao(topo, "Cancelar", lambda: sair_limpeza(), cor=tema.PAINEL,
                         acesa=tema.DESTAQUE, fonte=miudo, padx=12, pady=4)
    janela_grafias = [None]

    def abrir_grafias():
        """As grafias abrem por cima do histórico, dentro desta mesma janela."""
        if janela_grafias[0] and janela_grafias[0].winfo_exists():
            return
        import grafias
        janela_grafias[0] = grafias.abrir(raiz, ao_fechar=lista.focus_set)

    camada_config = [None]

    def abrir_configuracoes():
        """As configurações abrem por cima do histórico, dentro desta mesma janela."""
        if camada_config[0] and camada_config[0].winfo_exists():
            return
        import configuracoes
        camada_config[0] = configuracoes.abrir(raiz, ao_fechar=lista.focus_set)

    # Engrenagem e Dicionário formam um bloco com a largura exata do "Copiar
    # transcrição", logo abaixo: as bordas dos dois alinham. A largura do bloco
    # é acertada quando o botão de copiar existe (mais abaixo).
    dupla = tk.Frame(topo, bg=tema.FUNDO)
    dupla.pack(side="right")
    dupla.pack_propagate(False)
    engrenagem_fonte = tkfont.Font(family="Segoe UI Symbol", size=10)
    if not MAC:                               # no macOS as teclas são as do sistema (Fn)
        botao(dupla, "⚙", abrir_configuracoes, cor=tema.PAINEL, acesa=tema.DESTAQUE,
              fonte=engrenagem_fonte, padx=10, pady=0).pack(side="left", fill="y")
    dicionario_btn = botao(dupla, "Dicionário", abrir_grafias, cor=tema.PAINEL, acesa=tema.DESTAQUE,
                           fonte=miudo, padx=0, pady=4)
    dicionario_btn.pack(side="left", fill="both", expand=True, padx=(0 if MAC else 4, 0))

    meio = tk.Frame(raiz, bg=tema.FUNDO)
    meio.pack(fill="both", expand=True, padx=14, pady=6)

    # A lista e a barra moram no mesmo painel, e não lado a lado soltos: assim a
    # barra fica dentro da caixa escura, como no site, em vez de boiar no fundo.
    coluna = tk.Frame(meio, bg=tema.FUNDO)
    coluna.pack(side="left", fill="y", padx=(0, 10))
    todos_lbl = tk.Label(coluna, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=miudo,
                         anchor="w", cursor="hand2")
    todos_lbl.bind("<Button-1>", lambda *_: marcar_todos())
    esquerda = tk.Frame(coluna, bg=tema.PAINEL)
    esquerda.pack(fill="both", expand=True)
    barra_lista = tema.BarraDeRolagem(esquerda)
    barra_lista.pack(side="right", fill="y", padx=(0, 3), pady=3)
    # Altura 1 nos dois campos que esticam: com a altura padrão do Tk eles pedem
    # mais espaço do que a janela tem, e o rodapé fica espremido para fora.
    lista = tk.Listbox(esquerda, width=44, height=1, font=miudo, bg=tema.PAINEL, fg=tema.TEXTO,
                       selectbackground=tema.DESTAQUE, selectforeground=tema.TINTA,
                       highlightthickness=0, borderwidth=0, activestyle="none")
    lista.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=3)
    # A barra recebe a posição da rolagem, e a lista aproveita o mesmo aviso
    # para carregar o próximo lote quando a rolagem chega perto do fim.
    barra_lista.comando = lista.yview
    lista.configure(yscrollcommand=lambda primeiro, ultimo: (barra_lista.set(primeiro, ultimo),
                                                             perto_do_fim(float(ultimo))))

    # Painel da transcrição aberta: cabeçalho com a data e o botão de copiar,
    # texto embaixo. O botão mora aqui, e não no rodapé, porque é a ação daquela
    # transcrição que está na tela.
    direita = tk.Frame(meio, bg=tema.FUNDO)
    direita.pack(side="left", fill="both", expand=True)

    cabecalho = tk.Frame(direita, bg=tema.FUNDO)
    cabecalho.pack(fill="x", pady=(0, 6))
    carimbo = tk.Label(cabecalho, text="", bg=tema.FUNDO, fg=tema.APAGADO, font=miudo)
    carimbo.pack(side="left")
    # O botão mora num quadro de tamanho fixo: o "Copiado" do clique não encolhe
    # o botão, e a dupla do topo usa a mesma largura.
    copiar_quadro = tk.Frame(cabecalho, bg=tema.FUNDO)
    copiar_quadro.pack(side="right")
    copiar_quadro.pack_propagate(False)
    copiar_btn = botao(copiar_quadro, "Copiar transcrição", lambda: copiar())
    copiar_btn.pack(fill="both", expand=True)
    largura_copiar = copiar_btn.winfo_reqwidth()
    copiar_quadro.configure(width=largura_copiar, height=copiar_btn.winfo_reqheight())
    dupla.configure(width=largura_copiar, height=dicionario_btn.winfo_reqheight())

    painel = tk.Frame(direita, bg=tema.PAINEL)
    painel.pack(fill="both", expand=True)
    barra_texto = tema.BarraDeRolagem(painel)
    barra_texto.pack(side="right", fill="y", padx=(0, 3), pady=3)
    texto = tk.Text(painel, wrap="word", height=1, font=corpo, bg=tema.PAINEL, fg=tema.TEXTO,
                    insertbackground=tema.TEXTO, highlightthickness=0, borderwidth=0,
                    padx=12, pady=10)
    texto.pack(side="left", fill="both", expand=True)
    barra_texto.ligar(texto)

    rodape = tk.Label(raiz, text=DICA, bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w")
    rodape.pack(fill="x", padx=14, pady=(0, 12))

    def avisar(mensagem):
        rodape.config(text=mensagem, fg=tema.DESTAQUE)
        raiz.after(2500, lambda: rodape.config(text=DICA, fg=tema.APAGADO))

    def atualizar_topo():
        """Contagem do histórico inteiro e, no modo de limpeza, o total marcado.
        Quantos estão carregados na lista não importa: rolar carrega o resto."""
        contador.config(text=f"{transcricoes(len(todos))} no total")
        if limpando[0]:
            tudo = bool(todos) and all(id(it) in marcados for it in todos)
            todos_lbl.config(text=("☑" if tudo else "☐") +
                             f"  Selecionar todas ({numero(len(todos))})")
            n = len(marcados)
            apagar_btn.config(text=f"Apagar selecionados ({numero(n)})",
                              state="normal" if n else "disabled",
                              bg=VERMELHO if n else tema.PAINEL)

    cortados = {}             # (título, largura) -> título cortado: marcar e desmarcar não remede

    caixinha = max(miudo.measure("☐ "), miudo.measure("☑ "))

    def linha(it):
        """O título de um ditado no tamanho que cabe de verdade na lista. No
        modo de limpeza o corte desconta a caixinha e não depende dela, então
        marcar e desmarcar reaproveita o corte já feito."""
        rotulo, prefixo, cabe = rotular(it), "", largura_usada[0]
        if limpando[0]:
            rotulo, prefixo = rotulo.lstrip(), "☑ " if id(it) in marcados else "☐ "
            cabe -= caixinha
        if cabe < 60:
            return prefixo + rotulo
        chave = (rotulo, cabe)
        if chave not in cortados:
            if len(cortados) > 50000:
                cortados.clear()
            cortados[chave] = tema.encurtar(miudo, rotulo, cabe)
        return prefixo + cortados[chave]

    def apontar(i, rolar=True):
        """Seleciona a linha i e põe nela o ponto de partida das setas.

        As setas do teclado andam a partir do item ativo da lista, não da
        seleção, e o Tk empurra o ativo para o fim quando as linhas entram de
        uma vez numa lista vazia. Seleção e ativo andam sempre juntos, então a
        seta parte do ditado que está aberto e anda de um em um.
        """
        lista.selection_clear(0, "end")
        lista.selection_set(i)
        lista.selection_anchor(i)
        lista.activate(i)
        if rolar:
            lista.see(i)

    def desenhar(manter=None, quantos=None):
        """Remonta a lista com o que já estava carregado (ou `quantos`), sem
        perder a rolagem. `manter` é o ditado que segue selecionado."""
        atualizar_topo()
        carregados = todos[:max(quantos or len(na_tela), LOTE)]
        na_tela[:] = carregados
        rolagem = lista.yview()[0]
        lista.delete(0, "end")
        lista.insert("end", *[linha(it) for it in carregados])
        lista.yview_moveto(rolagem)
        if manter is not None and any(it is manter for it in carregados):
            apontar(next(i for i, it in enumerate(carregados) if it is manter))
        else:
            lista.activate(0)

    carregando = [False]

    def perto_do_fim(ultimo):
        """Rolagem passou de 90% do que está carregado: o próximo lote entra
        no fim da lista, sem mexer no que já está nela."""
        if ultimo < 0.9 or carregando[0] or len(na_tela) >= len(todos):
            return
        carregando[0] = True

        def mais():
            proximos = todos[len(na_tela):len(na_tela) + LOTE]
            na_tela.extend(proximos)
            if proximos:
                lista.insert("end", *[linha(it) for it in proximos])
            carregando[0] = False
        raiz.after_idle(mais)

    def selecionado():
        sel = lista.curselection()
        return na_tela[sel[0]] if sel and sel[0] < len(na_tela) else None

    largura_usada = [0]

    espera = [None]

    def preencher(*_):
        """Reescreve os títulos quando a largura muda: a medida em pixel só
        existe depois de o Tk desenhar a lista. Arrastando a borda da janela,
        só redesenha quando o arraste para."""
        if espera[0]:
            raiz.after_cancel(espera[0])
        espera[0] = raiz.after(80 if largura_usada[0] else 1, refazer_largura)

    def refazer_largura():
        espera[0] = None
        cabe = lista.winfo_width() - RESPIRO
        if cabe == largura_usada[0] or cabe < 60:
            return
        largura_usada[0] = cabe
        desenhar(selecionado())

    lista.bind("<Configure>", preencher)

    def mostrar(it=None):
        it = it or selecionado()
        if not it:
            return
        carimbo.config(text=f"{it['quando']}  ·  {len(it['texto'])} caracteres")
        texto.delete("1.0", "end")
        texto.insert("1.0", it["texto"])

    def limpar_leitura():
        texto.delete("1.0", "end")
        carimbo.config(text="")

    def marcar(evento):
        """Só o clique do mouse marca: navegar com as setas no modo de limpeza
        não pode ir marcando ditado pelo caminho."""
        if not limpando[0]:
            return
        i = lista.nearest(evento.y)
        caixa = lista.bbox(i)
        if not caixa or not caixa[1] <= evento.y <= caixa[1] + caixa[3] or i >= len(na_tela):
            return                            # clique no vazio abaixo do último
        it = na_tela[i]
        marcados.symmetric_difference_update({id(it)})
        atualizar_topo()
        lista.delete(i)                       # só a linha clicada: a lista pode ter milhares
        lista.insert(i, linha(it))
        apontar(i, rolar=False)
        mostrar(it)

    def copiar(*_):
        it = selecionado()
        if not it:
            return
        escrever(it["texto"])
        copiar_btn.config(text="Copiado")
        avisar("Copiado. Cole com Ctrl+V onde quiser.")
        raiz.after(2500, lambda: copiar_btn.config(text="Copiar transcrição"))

    def abrir_primeiro():
        """Volta ao topo com só o primeiro lote carregado e o mais recente aberto."""
        na_tela.clear()
        lista.yview_moveto(0)
        desenhar()
        lista.yview_moveto(0)
        if na_tela:
            apontar(0)
            mostrar(na_tela[0])
        else:
            limpar_leitura()

    # ---------- limpeza ----------
    def entrar_limpeza():
        limpando[0] = True
        marcados.clear()
        limpar_btn.pack_forget()
        cancelar_btn.pack(side="left", padx=(0, 4), before=contador)
        apagar_btn.pack(side="left", padx=(0, 4), before=contador)
        todos_lbl.pack(fill="x", pady=(0, 6), before=esquerda)
        desenhar(selecionado())

    def sair_limpeza():
        limpando[0] = False
        marcados.clear()
        apagar_btn.pack_forget()
        cancelar_btn.pack_forget()
        todos_lbl.pack_forget()
        limpar_btn.pack(side="left", padx=(0, 4), before=contador)
        desenhar(selecionado())

    def marcar_todos():
        if todos and all(id(it) in marcados for it in todos):
            marcados.difference_update(id(it) for it in todos)
        else:
            marcados.update(id(it) for it in todos)
        desenhar(selecionado())

    def confirmar():
        """Apagar não tem volta: um clique errado no botão vermelho não pode bastar."""
        escolhidos = [it for it in todos if id(it) in marcados]
        if escolhidos:
            tema.confirmar(raiz, "Apagar transcrições",
                           f"Apagar {transcricoes(len(escolhidos))} do histórico?",
                           "Depois de apagadas, elas não voltam.", "Apagar",
                           lambda: executar(escolhidos), corpo, miudo, botao_fonte)

    def executar(escolhidos):
        try:
            removidos = apagar(escolhidos)
        except OSError as e:
            avisar(f"Não deu para apagar agora: {e}. Tente de novo.")
            return
        recarregar()
        sair_limpeza()
        abrir_primeiro()
        avisar(f"{transcricoes(removidos)} apagada{'s' if removidos != 1 else ''}.")

    def recarregar():
        todos[:] = carregar()
        posicao[0] = ARQUIVO.stat().st_size if ARQUIVO.exists() else 0
        marcados.clear()

    def observar():
        """Ditado novo entra sozinho, sem fechar e abrir a janela.

        Quem grava é o processo do ditado, então aqui a janela vigia o arquivo.
        Um stat por segundo não custa nada e não depende de aviso entre
        processos, que se perderia justamente quando um dos dois caísse.

        Na mesma olhada, a janela confere o programa: se ele saiu, ela sai junto.
        """
        if programa_rodando():
            visto[0] = True
        elif visto[0] or time.monotonic() > prazo:
            raiz.destroy()
            return
        novos, posicao[0], recomecou = ler_novos(posicao[0])
        if recomecou:                       # histórico trocado por fora: recomeça a lista
            recarregar()
            if limpando[0]:
                sair_limpeza()
            abrir_primeiro()
        elif novos:
            atual = selecionado()
            # Quem está no ditado mais recente segue nele, que é a razão de a
            # janela estar aberta. Quem foi ler algo antigo não perde o lugar.
            acompanhando = atual is None or (na_tela and atual is na_tela[0])
            for it in reversed(novos):      # do mais antigo para o mais novo
                todos.insert(0, it)
            if acompanhando and not limpando[0]:
                abrir_primeiro()
            else:
                desenhar(atual, quantos=len(na_tela) + len(novos))
        raiz.after(INTERVALO, observar)

    lista.bind("<<ListboxSelect>>", lambda *_: mostrar())
    lista.bind("<ButtonRelease-1>", marcar)
    lista.bind("<Double-Button-1>", copiar)
    # Com uma camada aberta por cima (grafias, confirmação), Enter e Esc são dela.
    raiz.bind("<Return>", lambda *_: None if tema.camada_aberta() else copiar())
    raiz.bind("<Escape>", lambda *_: tema.esc_na_camada() or
              (sair_limpeza() if limpando[0] else raiz.destroy()))

    raiz.update_idletasks()
    abrir_primeiro()
    lista.focus_set()
    visto = [programa_rodando()]
    if not visto[0]:
        ligar_programa()
    prazo = time.monotonic() + PARTIDA
    raiz.after(INTERVALO, observar)
    raiz.mainloop()


def _demo():
    """Autoteste da leitura incremental, em arquivo temporário: o histórico de
    verdade nunca é tocado por teste."""
    import tempfile
    global ARQUIVO
    verdadeiro = ARQUIVO
    with tempfile.TemporaryDirectory() as pasta:
        ARQUIVO = Path(pasta) / "historico.jsonl"

        novos, posicao, recomecou = ler_novos(0)
        assert (novos, posicao, recomecou) == ([], 0, False)   # arquivo nem existe

        registrar("Primeiro ditado, com acentuação.")
        novos, posicao, recomecou = ler_novos(0)
        assert len(novos) == 1 and novos[0]["texto"].endswith("acentuação.")
        assert posicao == ARQUIVO.stat().st_size and not recomecou

        novos, posicao2, _ = ler_novos(posicao)                # nada mudou
        assert novos == [] and posicao2 == posicao

        registrar("Segundo ditado.")
        novos, posicao, _ = ler_novos(posicao)                 # só o que chegou depois
        assert len(novos) == 1 and novos[0]["texto"] == "Segundo ditado."

        with open(ARQUIVO, "a", encoding="utf-8") as f:        # escrita pela metade
            f.write('{"quando": "14/08/2026 22:00", "texto": "cortad')
        novos, parcial, _ = ler_novos(posicao)
        assert novos == [] and parcial == posicao, "linha sem quebra não pode ser consumida"

        with open(ARQUIVO, "a", encoding="utf-8") as f:        # o resto chega depois
            f.write('o no meio"}\n')
        novos, posicao, _ = ler_novos(parcial)
        assert len(novos) == 1 and novos[0]["texto"] == "cortado no meio"

        ARQUIVO.write_text("", encoding="utf-8")               # histórico limpo
        novos, posicao, recomecou = ler_novos(posicao)
        assert recomecou and novos == [] and posicao == 0

        assert rotular({"quando": "14/08/2026 22:00", "texto": "a  b\n c"}) == "  14/08/2026 22:00  a b c"
        # ditado antigo com campo a mais no jsonl continua aparecendo igual aos outros
        assert rotular({"quando": "x", "texto": "y", "revisado": True}) == "  x  y"

        assert transcricoes(1) == "1 transcrição" and transcricoes(2854) == "2.854 transcrições"

        # apagar: só os escolhidos, um de cada gêmeo, linha ilegível intacta,
        # quebra de linha do Windows preservada
        for t in ("A", "B", "B", "C"):
            registrar(t)
        with open(ARQUIVO, "a", encoding="utf-8") as f:
            f.write("linha ilegível\n")
        itens = carregar()
        bruto = ARQUIVO.read_bytes()
        um_b = next(i for i in itens if i["texto"] == "B")
        a = next(i for i in itens if i["texto"] == "A")
        assert apagar([a, um_b]) == 2
        restam = [i["texto"] for i in carregar()][::-1]
        assert restam == ["B", "C"], restam                    # um B saiu, o outro ficou
        assert b"linha ileg\xc3\xadvel" in ARQUIVO.read_bytes()
        assert (b"\r\n" in bruto) == (b"\r\n" in ARQUIVO.read_bytes())
        assert apagar([{"quando": "x", "texto": "não existe"}]) == 0
        assert apagar(carregar()) == 2 and carregar() == []    # selecionar todos
        assert not ARQUIVO.with_name(ARQUIVO.name + ".tmp").exists()

        # um ditado que chega no meio da regravação não se perde
        registrar("velho")
        chamadas = [0]

        class Espiao(type(ARQUIVO)):                           # o ditado chega logo após a leitura
            def read_bytes(self):
                dados = super().read_bytes()
                chamadas[0] += 1
                if chamadas[0] == 1:
                    registrar("chegou no meio")
                return dados
        real, ARQUIVO = ARQUIVO, Espiao(ARQUIVO)
        removidos = apagar([{"quando": time.strftime("%d/%m/%Y %H:%M"), "texto": "velho"}])
        ARQUIVO = real
        assert removidos == 1 and chamadas[0] == 2, (removidos, chamadas)
        assert [i["texto"] for i in carregar()] == ["chegou no meio"]
    ARQUIVO = verdadeiro
    print("historico.py: autoteste ok")


if __name__ == "__main__":
    _demo() if "--teste" in sys.argv else main()
