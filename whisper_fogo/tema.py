"""Aparência das janelas do Whisper Fogo: cor de marca, barra de título e barra
de rolagem.

Mora fora do historico.py porque o Tk não entrega nada disso pronto no Windows:
a barra de título nativa só muda de cor pelo DWM, o Scrollbar clássico não faz
canto arredondado e o ttk simplesmente ignora cor no tema nativo. As duas coisas
são desenhadas aqui e reaproveitadas por qualquer janela do programa.

A referência visual é a barra de rolagem fina de site: trilho na cor do painel,
polegar arredondado e um respiro entre os dois, que em CSS sai de um
`border: 2px solid` na cor do trilho.
"""
import sys
import tkinter as tk

MAC = sys.platform == "darwin"

# Visual dos produtos da Abajur: base preta e o laranja da marca no destaque.
DESTAQUE = "#FB5B04"       # laranja da Abajur
DESTAQUE_CLARO = "#FF7A2E" # o mesmo laranja, aceso sob o mouse
TINTA = "#0D0C0B"          # texto sobre o laranja: o branco não dá contraste nele
FUNDO = "#0D0E0D"          # o preto da página de produtos do site
PAINEL = "#191918"         # caixas sobre o fundo: lista, texto, campos
TEXTO = "#EDEDEB"
APAGADO = "#8D8B87"
BRANCO = "#FFFFFF"


def pintar_titulo(janela, fundo=DESTAQUE, texto=TINTA, borda=DESTAQUE):
    """Pinta a barra de título nativa na cor da marca.

    Windows 11 (build 22000 ou mais novo). Em versão antiga, no macOS ou no
    Linux o DWM não existe e a janela fica com a barra padrão do sistema, que é
    exatamente o que se quer como degradação.
    """
    import ctypes

    janela.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(janela.winfo_id()) or janela.winfo_id()

    def colorref(hexa):
        r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
        return ctypes.c_int(b << 16 | g << 8 | r)   # o COLORREF do Windows é 0x00BBGGRR

    # 20 = modo escuro desligado (ícones de minimizar, maximizar e fechar escuros,
    # que é o que contrasta com o laranja), 34 = borda, 35 = fundo, 36 = título.
    for atributo, valor in ((20, 0), (34, borda), (35, fundo), (36, texto)):
        v = ctypes.c_int(valor) if isinstance(valor, int) else colorref(valor)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(v), 4)


FECHAR_ACESO = "#C42B1C"   # o vermelho do fechar do próprio Windows


def barra_de_titulo(janela, titulo, altura=32):
    """Barra de título própria, laranja, com o título em branco e sem o ícone do
    programa (que continua na barra de tarefas e nos atalhos). No macOS ela é
    desenhada inteira pelo programa (ver `_barra_mac`).

    A barra nativa é recolhida (WM_NCCALCSIZE) e esta é desenhada no lugar. Arrastar e redimensionar pela borda de cima são entregues ao próprio
    Windows (WM_NCLBUTTONDOWN), e por isso o encaixe nas laterais e o duplo
    clique para maximizar continuam como em qualquer janela.
    """
    if MAC:
        return _barra_mac(janela, titulo)
    import ctypes
    import ctypes.wintypes as wt
    from tkinter import font as tkfont

    user32, comctl32 = ctypes.windll.user32, ctypes.windll.comctl32
    LRESULT = ctypes.c_ssize_t
    SUBCLASSPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM,
                                      ctypes.c_size_t, ctypes.c_size_t)
    comctl32.SetWindowSubclass.argtypes = [wt.HWND, SUBCLASSPROC, ctypes.c_size_t, ctypes.c_size_t]
    comctl32.DefSubclassProc.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    comctl32.DefSubclassProc.restype = LRESULT
    user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", wt.RECT * 3), ("lppos", ctypes.c_void_p)]

    janela.update_idletasks()
    hwnd = user32.GetParent(janela.winfo_id()) or janela.winfo_id()

    def recolher(h, msg, wparam, lparam, _id, _ref):
        if msg == 0x0083 and wparam:                       # WM_NCCALCSIZE
            params = ctypes.cast(lparam, ctypes.POINTER(NCCALCSIZE_PARAMS)).contents
            topo = params.rgrc[0].top
            resultado = comctl32.DefSubclassProc(h, msg, wparam, lparam)
            # Maximizada, a janela passa da tela pela espessura da borda: o
            # conteúdo desce essa espessura para não ficar cortado em cima.
            borda = (user32.GetSystemMetrics(33) + user32.GetSystemMetrics(92)) if user32.IsZoomed(h) else 0
            params.rgrc[0].top = topo + borda
            return resultado
        return comctl32.DefSubclassProc(h, msg, wparam, lparam)

    janela._recolher_barra = SUBCLASSPROC(recolher)        # referência viva enquanto a janela existir
    comctl32.SetWindowSubclass(hwnd, janela._recolher_barra, 1, 0)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)

    normal = tkfont.Font(family="Segoe UI", size=10)
    simbolos = tkfont.Font(family="Segoe MDL2 Assets", size=9)
    barra = tk.Frame(janela, bg=DESTAQUE, height=altura)
    barra.pack(side="top", fill="x")
    barra.pack_propagate(False)
    rotulo = tk.Label(barra, text=titulo, bg=DESTAQUE, fg=BRANCO, font=normal, anchor="w")
    rotulo.pack(side="left", fill="y", padx=(12, 0))

    def arrastar(_e, alvo=2):                              # 2 = HTCAPTION, 12 = HTTOP
        user32.ReleaseCapture()
        user32.SendMessageW(hwnd, 0x00A1, alvo, 0)        # WM_NCLBUTTONDOWN

    def alternar_maximizada(*_):
        janela.state("normal" if janela.state() == "zoomed" else "zoomed")
        desenhar_maximizar()

    for w in (barra, rotulo):
        w.bind("<ButtonPress-1>", arrastar)
        w.bind("<Double-Button-1>", alternar_maximizada)

    def botao_da_barra(simbolo, acao, aceso):
        caixa = tk.Frame(barra, bg=DESTAQUE, width=46, height=altura)
        caixa.pack(side="right")
        caixa.pack_propagate(False)
        rotulo_ = tk.Label(caixa, text=simbolo, bg=DESTAQUE, fg=BRANCO, font=simbolos)
        rotulo_.pack(fill="both", expand=True)
        rotulo_.bind("<Enter>", lambda *_: rotulo_.config(bg=aceso))
        rotulo_.bind("<Leave>", lambda *_: rotulo_.config(bg=DESTAQUE))
        rotulo_.bind("<ButtonRelease-1>", lambda *_: acao())
        return rotulo_

    botao_da_barra("", janela.destroy, FECHAR_ACESO)
    maximizar = botao_da_barra("", alternar_maximizada, DESTAQUE_CLARO)
    botao_da_barra("", janela.iconify, DESTAQUE_CLARO)

    def desenhar_maximizar(*_):
        maximizar.config(text="" if janela.state() == "zoomed" else "")

    janela.bind("<Configure>", desenhar_maximizar, add="+")

    # A borda de cima sumiu com a barra nativa: uma faixa fina no topo da barra
    # devolve o redimensionar por cima.
    faixa = tk.Frame(barra, bg=DESTAQUE, height=4, cursor="sb_v_double_arrow")
    faixa.place(x=0, y=0, relwidth=1)
    faixa.bind("<ButtonPress-1>", lambda e: None if janela.state() == "zoomed" else arrastar(e, 12))
    janela.altura_barra = altura
    return barra


def _barra_mac(raiz, titulo, altura=28):
    """A barra que o macOS desenha tem cor fixa e não acompanha o tema da
    janela, então lá ela é substituída por esta, com os mesmos controles no
    mesmo lugar: fechar e minimizar à esquerda, arrastar pela faixa."""
    raiz.overrideredirect(True)
    barra = tk.Frame(raiz, bg=DESTAQUE, height=altura)
    barra.pack(side="top", fill="x")
    barra.pack_propagate(False)
    controles = tk.Frame(barra, bg=DESTAQUE)
    controles.pack(side="left", padx=(10, 0))

    def botao_redondo(cor, acao):
        alvo = tk.Canvas(controles, width=14, height=14, bg=DESTAQUE,
                         highlightthickness=0, cursor="hand2")
        alvo.create_oval(2, 2, 12, 12, fill=cor, outline="")
        alvo.pack(side="left", padx=3)
        alvo.bind("<Button-1>", lambda _: acao())

    botao_redondo("#ff5f57", raiz.destroy)
    botao_redondo("#febc2e", lambda: raiz.wm_iconify())
    rotulo = tk.Label(barra, text=titulo, bg=DESTAQUE, fg=BRANCO, font=("Helvetica", 12))
    rotulo.pack(side="left", expand=True)

    posicao = {}

    def pegar(evento):
        posicao.update(x=evento.x_root, y=evento.y_root, jx=raiz.winfo_x(), jy=raiz.winfo_y())

    def mover(evento):
        if posicao:
            raiz.geometry(f"+{posicao['jx'] + evento.x_root - posicao['x']}"
                          f"+{posicao['jy'] + evento.y_root - posicao['y']}")

    for alvo in (barra, rotulo):
        alvo.bind("<Button-1>", pegar)
        alvo.bind("<B1-Motion>", mover)
    raiz.altura_barra = altura
    return barra


def aplicar(janela):
    """Cor de marca na janela inteira. Silencioso quando o sistema não suporta,
    porque aparência quebrada nunca pode derrubar o histórico de ditados."""
    janela.configure(bg=FUNDO)
    try:
        pintar_titulo(janela)
    except Exception:
        pass


class BarraDeRolagem(tk.Canvas):
    """Barra de rolagem fina e arredondada, desenhada à mão.

    Fala o mesmo protocolo do Scrollbar do Tk: recebe `set(primeiro, último)` do
    widget rolado e devolve `("moveto", fração)` ou `("scroll", n, "units")`, o
    que a deixa intercambiável com a barra nativa.
    """

    LARGURA = 14        # os 10px do CSS mais o respiro dos dois lados
    RESPIRO = 3         # o `border: 2px solid` de lá: descola o polegar do trilho
    ALTURA_MINIMA = 34  # numa lista longa o polegar encolheria até sumir

    def __init__(self, pai, trilho=PAINEL, polegar=DESTAQUE, aceso=DESTAQUE_CLARO, **kw):
        super().__init__(pai, width=self.LARGURA, highlightthickness=0,
                         borderwidth=0, bg=trilho, takefocus=0, **kw)
        self.cor_polegar, self.cor_acesa = polegar, aceso
        self.comando = None
        self.primeiro, self.ultimo = 0.0, 1.0
        self.sob_o_mouse = False
        self.agarre = None
        self.bind("<Configure>", lambda *_: self._desenhar())
        self.bind("<Button-1>", self._clicar)
        self.bind("<B1-Motion>", self._arrastar)
        self.bind("<ButtonRelease-1>", lambda *_: setattr(self, "agarre", None))
        self.bind("<Enter>", lambda *_: self._realce(True))
        self.bind("<Leave>", lambda *_: self._realce(False))
        self.bind("<MouseWheel>", self._roda)

    def ligar(self, alvo):
        """Liga a barra ao widget nos dois sentidos, de uma vez só."""
        self.comando = alvo.yview
        alvo.configure(yscrollcommand=self.set)
        return alvo

    # ------------------------------------------------------------- protocolo
    def set(self, primeiro, ultimo):
        self.primeiro, self.ultimo = float(primeiro), float(ultimo)
        self._desenhar()

    def get(self):
        return self.primeiro, self.ultimo

    # ---------------------------------------------------------------- desenho
    def _altura(self):
        """Altura real, com a pedida como reserva enquanto o Tk não calculou a
        geometria (acontece antes da janela aparecer, e no autoteste)."""
        altura = self.winfo_height()
        return altura if altura > 1 else self.winfo_reqheight()

    def _faixa(self):
        """Topo e base do polegar em pixel, já com o mínimo aplicado."""
        altura = self._altura()
        y0, y1 = self.primeiro * altura, self.ultimo * altura
        if y1 - y0 < self.ALTURA_MINIMA:
            meio = self.ALTURA_MINIMA / 2
            centro = min(max((y0 + y1) / 2, meio), max(altura - meio, meio))
            y0, y1 = centro - meio, centro + meio
        return y0, y1

    def _desenhar(self):
        self.delete("all")
        if self.ultimo - self.primeiro >= 1.0:
            return      # nada a rolar: some o polegar, o trilho segue reservado
        y0, y1 = self._faixa()
        x0, x1 = self.RESPIRO, self.LARGURA - self.RESPIRO
        cor = self.cor_acesa if self.sob_o_mouse else self.cor_polegar
        raio = (x1 - x0) / 2
        self.create_oval(x0, y0, x1, y0 + 2 * raio, fill=cor, outline=cor)
        self.create_oval(x0, y1 - 2 * raio, x1, y1, fill=cor, outline=cor)
        self.create_rectangle(x0, y0 + raio, x1, y1 - raio, fill=cor, outline=cor)

    def _realce(self, ligado):
        self.sob_o_mouse = ligado
        self._desenhar()

    # ------------------------------------------------------------- interação
    def _clicar(self, evento):
        y0, y1 = self._faixa()
        if y0 <= evento.y <= y1:
            self.agarre = evento.y - y0        # pegou o polegar onde clicou
        else:
            self.agarre = (y1 - y0) / 2        # clicou no trilho: pula para lá
            self._mover(evento.y)

    def _arrastar(self, evento):
        if self.agarre is not None:
            self._mover(evento.y)

    def _mover(self, y):
        if not self.comando:
            return
        altura = max(self._altura(), 1)
        janela = self.ultimo - self.primeiro
        fracao = (y - self.agarre) / altura
        self.comando("moveto", min(max(fracao, 0.0), max(1.0 - janela, 0.0)))

    def _roda(self, evento):
        if self.comando:
            self.comando("scroll", -int(evento.delta / 40) or (-1 if evento.delta > 0 else 1),
                         "units")


VERMELHO = "#dc2f26"       # ação que apaga: chama atenção de propósito
VERMELHO_CLARO = "#ef4a41"


_LARANJAS = (DESTAQUE, DESTAQUE_CLARO)


def botao(pai, texto, comando, fonte, cor=DESTAQUE, acesa=DESTAQUE_CLARO, padx=16, pady=6):
    """Botão chapado na cor da marca, o mesmo em todas as janelas do programa.
    Sobre o laranja o texto é escuro; sobre o resto, claro.

    O botão do Tk no macOS é desenhado pelo próprio sistema e não aceita cor de
    fundo, então lá ele é montado sobre um rótulo, que aceita a cor e responde a
    clique e à passagem do mouse do mesmo jeito.
    """
    if MAC:
        return _botao_mac(pai, texto, comando, fonte, cor, acesa, padx, pady)
    return tk.Button(pai, text=texto, font=fonte, bg=cor, fg=TINTA if cor in _LARANJAS else BRANCO,
                     activebackground=acesa,
                     activeforeground=TINTA if acesa in _LARANJAS else BRANCO,
                     disabledforeground=APAGADO, relief="flat", borderwidth=0,
                     padx=padx, pady=pady, cursor="hand2", command=comando)


# ------------------------------------------------------------------ camadas
# O painel é uma janela só. Tela secundária e confirmação abrem como camada por
# cima dela, do tamanho dela, e não como janela nova do sistema. A camada cobre
# o que está embaixo, então o clique não atravessa, e o Esc fecha a de cima.
_camadas = []         # [(quadro, ao_esc)], da mais antiga para a de cima
VEU = "#141517"       # fundo atrás do cartão de confirmação


FORA = -30000        # x da camada enquanto é montada: fora da janela, mas com o tamanho dela


def abrir_camada(janela, ao_esc, cor=FUNDO):
    """A camada nasce fora da área visível, já do tamanho do painel, e só
    entra na tela pronta, por `mostrar_camada`. Montada à vista, o Tk desenharia
    cada pedaço conforme ele chega, e a tela piscaria até estabilizar."""
    topo = janela.winfo_toplevel()
    barra = getattr(topo, "altura_barra", 0)      # a barra de título própria fica sempre à vista
    quadro = tk.Frame(topo, bg=cor)
    quadro.place(x=FORA, y=barra, relwidth=1, relheight=1, height=-barra)
    quadro.lift()
    quadro.foco_anterior = janela.focus_get()
    _camadas.append((quadro, ao_esc))
    return quadro


def mostrar_camada(quadro):
    """Resolve toda a geometria pendente com a camada ainda escondida e a traz
    para a tela de uma vez, já no estado final."""
    quadro.update_idletasks()
    quadro.place_configure(x=0)
    quadro.lift()


def fechar_camada(quadro):
    """Fecha a camada e devolve o teclado a quem estava com ele antes dela:
    sem isso o foco fica num botão que deixou de existir e Esc e setas param."""
    _camadas[:] = [(q, f) for q, f in _camadas if q is not quadro and q.winfo_exists()]
    if quadro.winfo_exists():
        anterior = getattr(quadro, "foco_anterior", None)
        topo = quadro.winfo_toplevel()
        quadro.destroy()
        if anterior is not None and anterior.winfo_exists():
            anterior.focus_set()
        else:
            topo.focus_set()


def camada_aberta():
    _camadas[:] = [(q, f) for q, f in _camadas if q.winfo_exists()]
    return bool(_camadas)


def esc_na_camada():
    """Esc vai para a camada de cima. Devolve False se não há camada aberta."""
    if not camada_aberta():
        return False
    _camadas[-1][1]()
    return True


def _botao_mac(pai, texto, comando, fonte, cor, acesa, padx, pady):
    alvo = tk.Label(pai, text=texto, font=fonte, bg=cor, padx=padx, pady=pady, cursor="hand2",
                    fg=TINTA if cor in _LARANJAS else BRANCO, disabledforeground=APAGADO)
    ativo = lambda: str(alvo.cget("state")) != "disabled"
    alvo.bind("<Button-1>", lambda _: ativo() and comando())
    alvo.bind("<Enter>", lambda _: ativo() and alvo.config(bg=acesa))
    alvo.bind("<Leave>", lambda _: alvo.config(bg=cor))
    alvo.invoke = comando
    return alvo


def confirmar(pai, titulo, pergunta, detalhe, rotulo, ao_confirmar, corpo, miudo, fonte_botao):
    """Confirmação dentro do painel, no visual do programa, para ação que não
    tem volta. O foco nasce no Cancelar: um Enter sem querer não apaga nada."""
    fechar = lambda: fechar_camada(veu)
    veu = abrir_camada(pai, lambda: fechar(), cor=VEU)
    cartao = tk.Frame(veu, bg=FUNDO, highlightthickness=1, highlightbackground=DESTAQUE)
    cartao.place(relx=0.5, rely=0.42, anchor="center")
    tk.Label(cartao, text=titulo, bg=FUNDO, fg=TEXTO, font=fonte_botao,
             anchor="w").pack(fill="x", padx=24, pady=(18, 8))
    tk.Label(cartao, text=pergunta, bg=FUNDO, fg=TEXTO, font=corpo, anchor="w").pack(fill="x", padx=24)
    tk.Label(cartao, text=detalhe, bg=FUNDO, fg=APAGADO, font=miudo, anchor="w").pack(fill="x", padx=24)
    botoes = tk.Frame(cartao, bg=FUNDO)
    botoes.pack(padx=24, pady=(18, 20), fill="x")
    botao(botoes, rotulo, lambda: (fechar(), ao_confirmar()), fonte_botao,
          cor=VERMELHO, acesa=VERMELHO_CLARO).pack(side="right")
    nao = botao(botoes, "Cancelar", fechar, fonte_botao, cor=PAINEL, acesa=DESTAQUE)
    nao.pack(side="right", padx=(0, 8))
    mostrar_camada(veu)
    nao.focus_set()
    return veu


def encurtar(fonte, texto, limite):
    """Corta o texto e assina com reticências, medindo em pixel.

    Contar caractere erraria feio: no Segoe UI um "i" e um "M" não têm a mesma
    largura, e o corte por contagem é justamente o que fazia o título encostar
    na barra de rolagem.
    """
    if limite <= 0:
        return texto
    # Chute pela soma das larguras de cada letra (medidas uma vez por fonte) e
    # confirmação com a medida real. A soma erra por poucos pixels de ajuste
    # entre letras, então perto do limite quem decide é a medida real. Com
    # milhares de títulos na lista, é a diferença entre redesenhar na hora e
    # travar por segundos: duas medidas por título em vez de oito.
    letras = _LETRAS.setdefault(str(fonte), {})

    def soma(s):
        total = 0
        for c in s:
            if c not in letras:
                letras[c] = fonte.measure(c)
            total += letras[c]
        return total

    estimada = soma(texto)
    if estimada <= limite - _FOLGA or (estimada <= limite + _FOLGA and fonte.measure(texto) <= limite):
        return texto

    def cabe(n):
        return fonte.measure(texto[:n].rstrip() + "…") <= limite

    corte, acumulado, reticencias = 0, 0, soma("…")
    while corte < len(texto) and acumulado + letras[texto[corte]] + reticencias <= limite:
        acumulado += letras[texto[corte]]
        corte += 1
    while corte > 0 and not cabe(corte):
        corte -= 1
    while corte < len(texto) and cabe(corte + 1):
        corte += 1
    return texto[:corte].rstrip() + "…"


_LETRAS = {}      # largura de cada letra, por fonte
_FOLGA = 12       # px de erro que a soma por letra pode ter contra a medida real


def _demo():
    from tkinter import font as tkfont
    raiz = tk.Tk()
    raiz.withdraw()
    f = tkfont.Font(family="Segoe UI", size=9)

    largo = f.measure("Whisper Fogo histórico")
    assert encurtar(f, "Whisper Fogo histórico", largo + 50) == "Whisper Fogo histórico"
    curto = encurtar(f, "Whisper Fogo histórico de ditados", largo)
    assert curto.endswith("…") and f.measure(curto) <= largo, curto
    assert encurtar(f, "qualquer coisa", 0) == "qualquer coisa"   # sem largura ainda
    assert encurtar(f, "", 100) == ""

    barra = BarraDeRolagem(raiz)
    barra.set(0.0, 0.25)
    assert barra.get() == (0.0, 0.25)
    barra.configure(height=400)
    raiz.update_idletasks()
    y0, y1 = barra._faixa()
    assert y0 == 0 and abs((y1 - y0) - 100) < 1, (y0, y1)

    barra.set(0.0, 0.01)           # lista enorme: 4px de polegar viraria o mínimo
    y0, y1 = barra._faixa()
    assert y1 - y0 == BarraDeRolagem.ALTURA_MINIMA, (y0, y1)

    barra.set(0.99, 1.0)           # esticado no fim: fica dentro do trilho
    y0, y1 = barra._faixa()
    assert y1 <= 400 and y0 >= 0, (y0, y1)

    barra.set(0.0, 1.0)            # nada a rolar: só o trilho
    barra._desenhar()
    assert not barra.find_all()

    movidos = []
    barra.comando = lambda *a: movidos.append(a)
    barra.set(0.0, 0.25)
    barra.agarre = 0
    barra._mover(400)              # arrastou até o fim: para no limite
    assert movidos == [("moveto", 0.75)], movidos

    raiz.destroy()
    print("tema.py: autoteste ok")


if __name__ == "__main__":
    _demo()
