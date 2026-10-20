"""Grafias aprendidas: ver, corrigir, criar e apagar o que o programa aprendeu.

Cada grafia certa aparece com todas as formas que o reconhecimento escreve e
levam a ela, e cada forma com o seu status. A edição salva sozinha ao sair do
campo ou apertar Enter, e o ditado seguinte já usa o dicionário novo, porque o
corretor lê o arquivo a cada ditado.
"""
import sys
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
import aprendizado
import tema

INTERVALO = 1000      # ms entre uma olhada e outra no arquivo, para o que o ditado aprende entrar sozinho
LOTE = 200            # a lista carrega de 200 em 200 conforme a rolagem desce, igual ao histórico
ATIVA = tema.DESTAQUE
AGUARDANDO = "#B9B6B0"
LEGENDA = ("Ativa: corrige toda transcrição. Aguardando: palavra comum corrigida uma vez; "
           "vira ativa na segunda correção igual ou quando você ativar.")


def situacao(item):
    """(status, cor, detalhe) de uma forma, do jeito que a tela mostra."""
    vezes = item.get("vezes", 0)
    desde = (item.get("criado") or "")[:10]
    if item.get("origem") == "manual":
        detalhe = f"criada por você · {desde}"
    else:
        detalhe = f"{vezes} correç{'ão' if vezes == 1 else 'ões'} · {desde}"
    if item.get("ativo"):
        return "ativa", ATIVA, detalhe
    return "aguardando", AGUARDANDO, detalhe


def titulo_do_grupo(certo, formas):
    """Uma linha da lista: a grafia certa, as formas que levam a ela e, se for
    o caso, quantas ainda aguardam."""
    nomes = ", ".join(f for f, _ in formas)
    esperando = sum(1 for _, item in formas if not item.get("ativo"))
    if esperando == len(formas):
        sufixo = "  ·  aguardando"
    elif esperando:
        sufixo = f"  ·  {esperando} aguardando"
    else:
        sufixo = ""
    return f"{certo}  ←  {nomes}{sufixo}"


def abrir(pai, ao_fechar=None):
    """Abre as grafias como camada por cima do painel, do tamanho dele, com um
    × para voltar ao histórico. Devolve a camada."""
    corpo = tkfont.Font(family="Segoe UI", size=11)
    miudo = tkfont.Font(family="Segoe UI", size=9)
    botao_fonte = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    titulo_fonte = tkfont.Font(family="Segoe UI", size=12, weight="bold")

    def botao(pai_, texto, comando, fonte=miudo, **kw):
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 4)
        return tema.botao(pai_, texto, comando, fonte, **kw)

    def esc():
        sair_apagar() if apagando[0] else fechar()

    def fechar():
        salvar()
        tema.fechar_camada(janela)
        if ao_fechar:
            ao_fechar()

    janela = tema.abrir_camada(pai, lambda: esc())

    cabeca = tk.Frame(janela, bg=tema.FUNDO)
    cabeca.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(cabeca, text="Dicionário", bg=tema.FUNDO, fg=tema.TEXTO,
             font=titulo_fonte).pack(side="left")
    botao(cabeca, "×", lambda: fechar(), fonte=titulo_fonte, cor=tema.PAINEL,
          acesa=tema.VERMELHO, padx=10, pady=0).pack(side="right")

    grupos = []               # o que a lista mostra, na mesma ordem
    atual = {"certo": None, "formas": []}   # a grafia aberta, como está gravada
    linhas = []               # as formas no editor: {"quadro", "campo", ...}
    apagando = [False]
    marcadas = set()          # grafias marcadas no modo de apagar
    lido = [None]             # data do arquivo da última leitura

    # ---------------------------------------------------------------- topo
    topo = tk.Frame(janela, bg=tema.FUNDO)
    topo.pack(fill="x", padx=14, pady=(12, 6))
    nova_btn = botao(topo, "Nova grafia", lambda: nova())
    nova_btn.pack(side="left", padx=(0, 4))
    apagar_modo_btn = botao(topo, "Apagar grafias", lambda: entrar_apagar(),
                            cor=tema.VERMELHO, acesa=tema.VERMELHO_CLARO)
    apagar_modo_btn.pack(side="left", padx=(0, 4))
    cancelar_btn = botao(topo, "Cancelar", lambda: sair_apagar(), cor=tema.PAINEL, acesa=tema.DESTAQUE)
    apagar_sel_btn = botao(topo, "", lambda: confirmar_selecionadas(),
                           cor=tema.VERMELHO, acesa=tema.VERMELHO_CLARO)
    contador = tk.Label(topo, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=corpo)
    contador.pack(side="left", padx=(10, 0))

    meio = tk.Frame(janela, bg=tema.FUNDO)
    meio.pack(fill="both", expand=True, padx=14, pady=6)

    # ---------------------------------------------------------------- lista
    coluna = tk.Frame(meio, bg=tema.FUNDO)
    coluna.pack(side="left", fill="y", padx=(0, 14))
    todas_lbl = tk.Label(coluna, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=miudo,
                         anchor="w", cursor="hand2")
    todas_lbl.bind("<Button-1>", lambda *_: marcar_todas())
    caixa_lista = tk.Frame(coluna, bg=tema.PAINEL)
    caixa_lista.pack(fill="both", expand=True)
    barra = tema.BarraDeRolagem(caixa_lista)
    barra.pack(side="right", fill="y", padx=(0, 3), pady=3)
    lista = tk.Listbox(caixa_lista, width=42, height=1, font=miudo, bg=tema.PAINEL, fg=tema.TEXTO,
                       selectbackground=tema.DESTAQUE, selectforeground=tema.TINTA,
                       highlightthickness=0, borderwidth=0, activestyle="none", exportselection=False)
    lista.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=3)
    # A barra recebe a posição da rolagem, e a lista aproveita o mesmo aviso
    # para carregar o próximo lote quando a rolagem chega perto do fim.
    barra.comando = lista.yview
    lista.configure(yscrollcommand=lambda primeiro, ultimo: (barra.set(primeiro, ultimo),
                                                             perto_do_fim(float(ultimo))))
    carregadas = [LOTE]       # quantas grafias já estão na lista

    # ---------------------------------------------------------------- editor
    direita = tk.Frame(meio, bg=tema.FUNDO)
    direita.pack(side="left", fill="both", expand=True)
    tk.Label(direita, text=LEGENDA, bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w",
             justify="left", wraplength=520).pack(fill="x", pady=(0, 10))
    vazio = tk.Label(direita, text="Escolha uma grafia na lista ou crie uma nova.",
                     bg=tema.FUNDO, fg=tema.APAGADO, font=corpo, anchor="w")
    editor = tk.Frame(direita, bg=tema.FUNDO)

    def campo(pai_):
        return tk.Entry(pai_, font=corpo, bg=tema.PAINEL, fg=tema.TEXTO, insertbackground=tema.TEXTO,
                        relief="flat", highlightthickness=1, highlightbackground=tema.PAINEL,
                        highlightcolor=tema.DESTAQUE)

    tk.Label(editor, text="Grafia correta", bg=tema.FUNDO, fg=tema.APAGADO, font=miudo,
             anchor="w").pack(fill="x")
    certo_campo = campo(editor)
    certo_campo.pack(fill="x", ipady=4, pady=(2, 14))
    tk.Label(editor, text="Formas que o reconhecimento escreve e viram essa grafia",
             bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w").pack(fill="x")
    formas_quadro = tk.Frame(editor, bg=tema.FUNDO)
    formas_quadro.pack(fill="x", pady=(2, 6))
    acoes = tk.Frame(editor, bg=tema.FUNDO)
    acoes.pack(fill="x")
    botao(acoes, "+ Adicionar forma", lambda: adicionar_forma(), cor=tema.PAINEL,
          acesa=tema.DESTAQUE).pack(side="left")
    botao(acoes, "Apagar esta grafia", lambda: confirmar_esta(),
          cor=tema.VERMELHO, acesa=tema.VERMELHO_CLARO).pack(side="right")

    rodape = tk.Label(janela, text="", bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w")
    rodape.pack(fill="x", padx=14, pady=(0, 12))

    def avisar(mensagem, erro=False):
        rodape.config(text=mensagem, fg=tema.VERMELHO_CLARO if erro else ATIVA)
        if not erro:
            janela.after(3000, lambda: rodape.winfo_exists() and rodape.cget("text") == mensagem
                         and rodape.config(text=""))

    # ------------------------------------------------------------- dados
    def dados():
        return aprendizado._ler()

    def marcar_lido():
        try:
            lido[0] = aprendizado.ARQUIVO.stat().st_mtime_ns
        except OSError:
            lido[0] = None

    # ------------------------------------------------------------- lista
    def desenhar_lista(selecionar=None):
        """Remonta a lista e o contador. `selecionar` é a grafia que fica
        marcada; sem ele, segue a que já estava."""
        if selecionar is None:
            sel = lista.curselection()
            selecionar = grupos[sel[0]][0] if sel and sel[0] < len(grupos) else atual["certo"]
        grupos[:] = aprendizado.grupos()
        marcar_lido()
        formas = sum(len(f) for _, f in grupos)
        esperando = sum(1 for _, f in grupos for _, it in f if not it.get("ativo"))
        contador.config(text=f"{len(grupos)} grafia{'s' if len(grupos) != 1 else ''}, "
                             f"{formas} forma{'s' if formas != 1 else ''}: "
                             f"{formas - esperando} ativa{'s' if formas - esperando != 1 else ''}, "
                             f"{esperando} aguardando")
        marcadas.intersection_update(c for c, _ in grupos)
        alvo = next((i for i, (c, _) in enumerate(grupos) if c == selecionar), None)
        if alvo is not None and alvo >= carregadas[0]:
            carregadas[0] = alvo + 1           # a escolhida sempre está carregada
        rolagem = lista.yview()[0]
        lista.delete(0, "end")
        lista.insert("end", *[linha_da_lista(c, f) for c, f in grupos[:carregadas[0]]])
        lista.yview_moveto(rolagem)
        if alvo is not None:
            lista.selection_set(alvo)
            lista.selection_anchor(alvo)
            lista.activate(alvo)               # as setas partem da grafia aberta
            lista.see(alvo)
        if apagando[0]:
            tudo = bool(grupos) and all(c in marcadas for c, _ in grupos)
            todas_lbl.config(text=("☑" if tudo else "☐") + f"  Selecionar todas ({len(grupos)})")
            apagar_sel_btn.config(text=f"Apagar selecionadas ({len(marcadas)})",
                                  state="normal" if marcadas else "disabled",
                                  bg=tema.VERMELHO if marcadas else tema.PAINEL)

    def linha_da_lista(certo, formas_):
        rotulo = titulo_do_grupo(certo, formas_)
        if apagando[0]:
            rotulo = ("☑ " if certo in marcadas else "☐ ") + rotulo
        largura_desenhada[0] = lista.winfo_width()
        cabe = largura_desenhada[0] - 12
        return tema.encurtar(miudo, rotulo, cabe) if cabe >= 60 else rotulo

    carregando = [False]

    def perto_do_fim(ultimo):
        """Rolagem passou de 90% do que está carregado: o próximo lote entra
        no fim da lista, sem mexer no que já está nela."""
        if ultimo < 0.9 or carregando[0] or carregadas[0] >= len(grupos):
            return
        carregando[0] = True

        def mais():
            proximas = grupos[carregadas[0]:carregadas[0] + LOTE]
            carregadas[0] += len(proximas)
            if proximas:
                lista.insert("end", *[linha_da_lista(c, f) for c, f in proximas])
            carregando[0] = False
        janela.after_idle(mais)

    espera = [None]

    largura_desenhada = [0]

    def redimensionou(*_):
        """Arrastando a borda da janela, só redesenha quando o arraste para, e
        só se a largura da lista mudou de verdade."""
        if espera[0]:
            janela.after_cancel(espera[0])
        espera[0] = janela.after(80, refazer_largura)

    def refazer_largura():
        espera[0] = None
        if lista.winfo_width() != largura_desenhada[0]:
            desenhar_lista()

    lista.bind("<Configure>", redimensionou)

    def clicou_na_lista(evento):
        i = lista.nearest(evento.y)
        caixa = lista.bbox(i)
        if not caixa or not caixa[1] <= evento.y <= caixa[1] + caixa[3] or i >= min(len(grupos), lista.size()):
            return
        certo = grupos[i][0]
        if apagando[0]:
            marcadas.symmetric_difference_update({certo})
            desenhar_lista(certo)
        if certo != atual["certo"]:
            abrir_grafia(certo)

    def escolheu_com_teclado(*_):
        sel = lista.curselection()
        if sel and sel[0] < len(grupos) and grupos[sel[0]][0] != atual["certo"]:
            abrir_grafia(grupos[sel[0]][0])

    lista.bind("<ButtonRelease-1>", clicou_na_lista)
    lista.bind("<<ListboxSelect>>", escolheu_com_teclado)

    # ------------------------------------------------------------- editor
    def mostrar_editor(sim):
        if sim:
            vazio.pack_forget()
            editor.pack(fill="both", expand=True)
        else:
            editor.pack_forget()
            vazio.pack(fill="x")

    def linha_forma(texto=""):
        quadro = tk.Frame(formas_quadro, bg=tema.FUNDO)
        quadro.pack(fill="x", pady=2)
        entrada = campo(quadro)
        entrada.configure(width=20)
        entrada.insert(0, texto)
        entrada.pack(side="left", ipady=3)
        status = tk.Label(quadro, text="", bg=tema.FUNDO, font=miudo, width=11, anchor="w")
        status.pack(side="left", padx=(10, 0))
        detalhe = tk.Label(quadro, text="", bg=tema.FUNDO, fg=tema.APAGADO, font=miudo, anchor="w")
        detalhe.pack(side="left", padx=(4, 0))
        linha = {"quadro": quadro, "campo": entrada, "status": status, "detalhe": detalhe}
        linha["remover"] = botao(quadro, "×", lambda: remover_forma(linha), fonte=botao_fonte,
                                 cor=tema.PAINEL, acesa=tema.VERMELHO, padx=8, pady=0)
        linha["remover"].pack(side="right")
        linha["ativar"] = botao(quadro, "Ativar", lambda: ativar_forma(linha), cor=tema.PAINEL,
                                acesa=tema.DESTAQUE)
        entrada.bind("<Return>", lambda *_: salvar())
        entrada.bind("<FocusOut>", lambda *_: salvar())
        linhas.append(linha)
        return linha

    def atualizar_status():
        """Status e detalhe de cada forma, lidos do arquivo, sem mexer no foco."""
        gravado = dados()
        for linha in linhas:
            item = gravado.get(linha["campo"].get().strip())
            if item and item.get("certo") == atual["certo"]:
                status, cor, detalhe = situacao(item)
                linha["status"].config(text=status, fg=cor)
                linha["detalhe"].config(text=detalhe)
                if status == "aguardando":
                    linha["ativar"].pack(side="right", padx=(0, 6), after=linha["remover"])
                else:
                    linha["ativar"].pack_forget()
            else:
                linha["status"].config(text="")
                linha["detalhe"].config(text="")
                linha["ativar"].pack_forget()

    def montar_editor(certo, formas):
        velhas = list(linhas)
        linhas.clear()                  # antes de destruir: o campo que sai avisa que perdeu o foco
        atual["montando"] = True
        for linha in velhas:
            linha["quadro"].destroy()
        atual["montando"] = False
        atual["certo"], atual["formas"] = certo, list(formas)
        certo_campo.delete(0, "end")
        certo_campo.insert(0, certo or "")
        for forma in formas or [""]:
            linha_forma(forma)
        certo_campo.bind("<Return>", lambda *_: salvar())
        certo_campo.bind("<FocusOut>", lambda *_: salvar())
        mostrar_editor(True)
        atualizar_status()

    def fechar_editor():
        """Esvazia o editor e o esconde: uma grafia apagada não pode continuar
        nos campos, senão a próxima gravação automática a traria de volta."""
        velhas = list(linhas)
        linhas.clear()
        atual["montando"] = True
        for linha in velhas:
            linha["quadro"].destroy()
        certo_campo.delete(0, "end")
        atual["montando"] = False
        atual["certo"], atual["formas"] = None, []
        mostrar_editor(False)

    def abrir_grafia(certo):
        salvar()
        for c, formas in grupos:
            if c == certo:
                montar_editor(c, [f for f, _ in formas])
                desenhar_lista(c)
                return

    def nova():
        salvar()
        lista.selection_clear(0, "end")
        montar_editor(None, [])
        certo_campo.focus_set()

    def adicionar_forma():
        linha = linha_forma()
        linha["campo"].focus_set()

    def remover_forma(linha):
        linhas.remove(linha)
        atual["montando"] = True
        linha["quadro"].destroy()
        atual["montando"] = False
        salvar()
        if not linhas and atual["certo"] is not None:
            adicionar_forma()

    def ativar_forma(linha):
        salvar()
        forma = linha["campo"].get().strip()
        aprendizado.ativar(forma)
        atualizar_status()
        desenhar_lista(atual["certo"])
        avisar(f"“{forma}” agora é ativa: a próxima transcrição já corrige.")

    def salvar(*_):
        """Grava o que está no editor, se mudou. Erro de preenchimento vira aviso
        no rodapé e nada é gravado."""
        if atual.get("montando") or not janela.winfo_exists() or not editor.winfo_ismapped():
            return
        certo = certo_campo.get().strip()
        formas = list(dict.fromkeys(t for t in (l["campo"].get().strip() for l in linhas) if t))
        antes_certo, antes_formas = atual["certo"], atual["formas"]
        if (certo or None) == antes_certo and formas == antes_formas:
            return
        if antes_certo is None and not formas:
            if certo:
                avisar("Acrescente ao menos uma forma que vira essa grafia.", erro=True)
            return
        if not formas:                               # tirou a última forma: a grafia sai
            aprendizado.editar_grupo(antes_formas, [], antes_certo)
            avisar(f"Grafia “{antes_certo}” apagada.")
            fechar_editor()
            desenhar_lista("")
            return
        try:
            movidas = aprendizado.editar_grupo(antes_formas, formas, certo)
        except ValueError as e:
            avisar(str(e), erro=True)
            return
        atual["certo"], atual["formas"] = certo, formas
        desenhar_lista(certo)
        gravadas = next((f for c, f in grupos if c == certo), [])
        if {f for f, _ in gravadas} != set(formas):
            # Escreveu uma grafia que já existia: as duas viraram uma só.
            montar_editor(certo, [f for f, _ in gravadas])
        else:
            atualizar_status()
        if movidas:
            avisar("Salvo. " + "; ".join(f"“{f}” saiu de “{c}”" for f, c in movidas) + ".")
        else:
            avisar("Salvo.")

    # ------------------------------------------------------------- apagar
    def entrar_apagar():
        salvar()
        apagando[0] = True
        marcadas.clear()
        nova_btn.pack_forget()
        apagar_modo_btn.pack_forget()
        cancelar_btn.pack(side="left", padx=(0, 4), before=contador)
        apagar_sel_btn.pack(side="left", padx=(0, 4), before=contador)
        todas_lbl.pack(fill="x", pady=(0, 6), before=caixa_lista)
        desenhar_lista()

    def sair_apagar():
        apagando[0] = False
        marcadas.clear()
        cancelar_btn.pack_forget()
        apagar_sel_btn.pack_forget()
        todas_lbl.pack_forget()
        nova_btn.pack(side="left", padx=(0, 4), before=contador)
        apagar_modo_btn.pack(side="left", padx=(0, 4), before=contador)
        desenhar_lista()

    def marcar_todas():
        if grupos and all(c in marcadas for c, _ in grupos):
            marcadas.clear()
        else:
            marcadas.update(c for c, _ in grupos)
        desenhar_lista()

    def apagar(certos):
        formas = aprendizado.apagar_grupos(certos)
        if atual["certo"] in certos:
            fechar_editor()
        if apagando[0]:
            sair_apagar()
        desenhar_lista("")
        n = len(certos)
        avisar(f"{n} grafia{'s' if n != 1 else ''} apagada{'s' if n != 1 else ''} "
               f"({formas} forma{'s' if formas != 1 else ''}).")

    def confirmar_selecionadas():
        escolhidas = [c for c, _ in grupos if c in marcadas]
        if escolhidas:
            n = len(escolhidas)
            tema.confirmar(janela, "Apagar grafias",
                           f"Apagar {n} grafia{'s' if n != 1 else ''} do dicionário?",
                           "As próximas transcrições deixam de corrigir essas formas.", "Apagar",
                           lambda: apagar(escolhidas), corpo, miudo, botao_fonte)

    def confirmar_esta():
        certo = atual["certo"]
        if certo is None:                            # grafia nova ainda não gravada
            fechar_editor()
            return
        tema.confirmar(janela, "Apagar grafia", f"Apagar a grafia “{certo}”?",
                       "As próximas transcrições deixam de corrigir as formas dela.", "Apagar",
                       lambda: apagar([certo]), corpo, miudo, botao_fonte)

    # ------------------------------------------------------------- vigia
    def observar():
        """O ditado aprende sozinho enquanto a janela está aberta: a lista e os
        status acompanham, sem mexer no que está sendo digitado."""
        if not janela.winfo_exists():
            return
        try:
            agora = aprendizado.ARQUIVO.stat().st_mtime_ns
        except OSError:
            agora = None
        if agora != lido[0]:
            desenhar_lista()
            if atual["certo"] is not None:
                atualizar_status()
        janela.after(INTERVALO, observar)

    # Tudo montado com a camada escondida: a lista já cortada na largura certa
    # e a primeira grafia aberta. Só então a camada entra na tela.
    janela.update_idletasks()
    desenhar_lista()
    if grupos:
        abrir_grafia(grupos[0][0])
    else:
        mostrar_editor(False)
    tema.mostrar_camada(janela)
    lista.focus_set()
    janela.after(INTERVALO, observar)
    return janela


def _demo():
    """Autoteste das regras de dicionário que a tela usa, em arquivo temporário:
    o dicionário de verdade nunca é tocado por teste."""
    import json
    import tempfile
    verdadeiro = aprendizado.ARQUIVO
    with tempfile.TemporaryDirectory() as pasta:
        aprendizado.ARQUIVO = Path(pasta) / "aprendido.json"
        aprendizado._gravar({
            "Kubernets": {"certo": "Kubernetes", "vezes": 3, "ativo": True, "criado": "20/08/2026 10:00",
                        "origem": "nome próprio", "promovido": "20/08/2026 10:00"},
            "sessão": {"certo": "seção", "vezes": 1, "ativo": False, "criado": "21/08/2026 10:00",
                       "origem": "palavra comum"},
        })
        assert [c for c, _ in aprendizado.grupos()] == ["Kubernetes", "seção"]

        # N formas para uma grafia, criada à mão: entra ativa e vale no carregar()
        assert aprendizado.editar_grupo([], ["Antropic", "Antropica", " ", "Antropic"], "Anthropic") == []
        assert aprendizado.carregar()["Antropica"] == "Anthropic"
        formas = dict(next(f for c, f in aprendizado.grupos() if c == "Anthropic"))
        assert set(formas) == {"Antropic", "Antropica"} and formas["Antropic"]["origem"] == "manual"

        # editar a grafia certa leva todas as formas junto
        aprendizado.editar_grupo(["Kubernets"], ["Kubernets", "kubernetes"], "Kubernetes K8s")
        assert aprendizado.carregar()["Kubernets"] == "Kubernetes K8s"
        assert aprendizado._ler()["Kubernets"]["vezes"] == 3, "trocar a grafia não zera a contagem"

        # forma que não mudou mantém o status de aguardando
        aprendizado.editar_grupo(["sessão"], ["sessão", "secção"], "seção")
        assert aprendizado._ler()["sessão"]["ativo"] is False
        assert aprendizado._ler()["secção"]["ativo"] is True
        assert "sessão" not in aprendizado.carregar(), "aguardando não corrige ditado"
        aprendizado.ativar("sessão")
        assert aprendizado.carregar()["sessão"] == "seção"

        # forma que estava em outra grafia muda de grafia e avisa de onde saiu
        assert aprendizado.editar_grupo([], ["kubernetes"], "Kubernetes") == [("kubernetes", "Kubernetes K8s")]

        # tirar uma forma, e a grafia certa entre as erradas é recusada
        aprendizado.editar_grupo(["Antropic", "Antropica"], ["Antropic"], "Anthropic")
        assert "Antropica" not in aprendizado._ler()
        for errado in (lambda: aprendizado.editar_grupo([], ["x"], "  "),
                       lambda: aprendizado.editar_grupo([], ["Anthropic"], "Anthropic")):
            try:
                errado()
                raise AssertionError("aceitou grafia inválida")
            except ValueError:
                pass

        # apagar em massa
        assert aprendizado.apagar_grupos(["Anthropic", "seção"]) == 3
        assert [c for c, _ in aprendizado.grupos()] == ["Kubernetes", "Kubernetes K8s"]
        assert aprendizado.apagar_grupos([c for c, _ in aprendizado.grupos()]) == 2
        assert aprendizado.grupos() == [] and json.loads(aprendizado.ARQUIVO.read_text("utf-8")) == {}
        assert not aprendizado.ARQUIVO.with_name("aprendido.json.tmp").exists()

        assert titulo_do_grupo("A", [("b", {"ativo": True}), ("c", {"ativo": False})]) == \
            "A  ←  b, c  ·  1 aguardando"
        assert situacao({"ativo": False, "vezes": 1, "criado": "21/08/2026 10:00"})[0] == "aguardando"
    aprendizado.ARQUIVO = verdadeiro
    print("grafias.py: autoteste ok")


if __name__ == "__main__":
    _demo()
