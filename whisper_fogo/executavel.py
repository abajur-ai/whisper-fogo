"""O executável do Whisper Fogo no Windows.

O Windows mostra o nome, a editora e o ícone gravados dentro do executável que
roda: no Gerenciador de Tarefas (processos e aplicativos de inicialização), nas
Configurações, no aviso de microfone em uso e na lista de ícones da bandeja.
Rodando pelo pythonw.exe, o programa aparecia como "Python". Aqui o
interpretador vira `Whisper Fogo.exe`, com nome e ícone próprios, dentro do
ambiente isolado: o mesmo Python, só que apresentado como o programa que é.

O interpretador precisa das DLLs dele ao lado, e acha a biblioteca padrão e os
pacotes pelo `pyvenv.cfg` da pasta de cima, como qualquer Python de ambiente.

    python executavel.py           cria (o instalador chama assim)
    python executavel.py --teste   autoteste numa pasta temporária
"""
import ctypes
import shutil
import struct
import sys
from ctypes import wintypes
from pathlib import Path

CODIGO = Path(__file__).parent
SCRIPTS = CODIGO / ".venv" / "Scripts"
PROGRAMA = SCRIPTS / "Whisper Fogo.exe"
ICONE = CODIGO / "fogo.ico"

NOME = "Whisper Fogo"
EDITORA = "Abajur"
DESCRICAO = "Whisper Fogo"
DLLS = ("python3.dll", "vcruntime140.dll", "vcruntime140_1.dll")

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
INGLES_EUA, UNICODE = 0x0409, 1200

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
k32.FreeLibrary.argtypes = (wintypes.HMODULE,)
k32.BeginUpdateResourceW.restype = wintypes.HANDLE
k32.BeginUpdateResourceW.argtypes = (wintypes.LPCWSTR, wintypes.BOOL)
k32.UpdateResourceW.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                wintypes.WORD, ctypes.c_void_p, wintypes.DWORD)
k32.EndUpdateResourceW.argtypes = (wintypes.HANDLE, wintypes.BOOL)
ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p,
                          ctypes.c_void_p, wintypes.LPARAM)
ENUM_IDIOMA = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p,
                                 ctypes.c_void_p, wintypes.WORD, wintypes.LPARAM)
k32.EnumResourceNamesW.argtypes = (wintypes.HMODULE, ctypes.c_void_p, ENUM, wintypes.LPARAM)
k32.EnumResourceLanguagesW.argtypes = (wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p,
                                       ENUM_IDIOMA, wintypes.LPARAM)


def _recursos(arquivo, tipos):
    """[(tipo, nome, idioma)] do que o executável carrega daqueles tipos. Nome é
    número ou texto, como o Windows guarda."""
    achados = []
    h = k32.LoadLibraryExW(str(arquivo), None, 0x2)      # LOAD_LIBRARY_AS_DATAFILE
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for tipo in tipos:
            nomes = []

            def nome(_h, _t, n, _p):
                nomes.append(n if n < 0x10000 else ctypes.wstring_at(n))
                return True
            k32.EnumResourceNamesW(h, tipo, ENUM(nome), 0)
            for n in nomes:
                idiomas = []

                def idioma(_h, _t, _n, i, _p):
                    idiomas.append(i)
                    return True
                texto = ctypes.c_wchar_p(n) if isinstance(n, str) else None
                k32.EnumResourceLanguagesW(h, tipo, ctypes.cast(texto, ctypes.c_void_p) if texto
                                           else n, ENUM_IDIOMA(idioma), 0)
                achados += [(tipo, n, i) for i in idiomas]
    finally:
        k32.FreeLibrary(h)
    return achados


def _bloco(chave, valor=b"", filhos=(), texto=False):
    """Um nó do VS_VERSIONINFO: tamanho, tamanho do valor, tipo, chave, valor e
    filhos, cada parte alinhada em 4 bytes."""
    def alinhar(b):
        return b + b"\0" * (-(6 + len(b)) % 4)
    corpo = alinhar((chave + "\0").encode("utf-16-le")) + valor
    for f in filhos:
        corpo = alinhar(corpo) + f
    tam_valor = len(valor) // 2 if texto else len(valor)
    return struct.pack("<HHH", 6 + len(corpo), tam_valor, 1 if texto else 0) + corpo


def versao(versao_texto="1.0.0", descricao=DESCRICAO, arquivo=None):
    """Recurso de versão: é dele que sai o nome e a editora na tela."""
    partes = [int(p) for p in (versao_texto.split(".") + ["0"] * 4)[:4] if p.isdigit()]
    partes += [0] * (4 - len(partes))
    ms, ls = (partes[0] << 16) | partes[1], (partes[2] << 16) | partes[3]
    fixo = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0,
                       0x00040004, 1, 0, 0, 0)    # VOS_NT_WINDOWS32, VFT_APP
    campos = {"CompanyName": EDITORA, "FileDescription": descricao,
              "FileVersion": versao_texto, "InternalName": NOME,
              "LegalCopyright": "Abajur (abajur.ai)", "OriginalFilename": arquivo or PROGRAMA.name,
              "ProductName": NOME, "ProductVersion": versao_texto}
    textos = [_bloco(k, (v + "\0").encode("utf-16-le"), texto=True) for k, v in campos.items()]
    tabela = _bloco(f"{INGLES_EUA:04X}{UNICODE:04X}", filhos=textos, texto=True)
    traducao = _bloco("Translation", struct.pack("<HH", INGLES_EUA, UNICODE))
    return _bloco("VS_VERSION_INFO", fixo, filhos=[
        _bloco("StringFileInfo", filhos=[tabela], texto=True),
        _bloco("VarFileInfo", filhos=[traducao], texto=True)])


def _icones(ico):
    """Do .ico: as imagens (RT_ICON) e o diretório que as junta (RT_GROUP_ICON),
    que no executável aponta para cada imagem pelo número em vez do deslocamento."""
    dados = ico.read_bytes()
    _, tipo, quantos = struct.unpack_from("<HHH", dados)
    assert tipo == 1, "não é um .ico"
    imagens, grupo = [], struct.pack("<HHH", 0, 1, quantos)
    for i in range(quantos):
        entrada = struct.unpack_from("<BBBBHHII", dados, 6 + 16 * i)
        tamanho, inicio = entrada[6], entrada[7]
        imagens.append(dados[inicio:inicio + tamanho])
        grupo += struct.pack("<BBBBHHIH", *entrada[:7], i + 1)
    return imagens, grupo


def _carimbar(arquivo, origem, versao_texto, descricao=DESCRICAO, nome_arquivo=None):
    """Troca ícone e versão do executável. Os recursos antigos desses tipos saem
    todos, senão o Windows poderia continuar achando o ícone do Python."""
    velhos = _recursos(origem, (RT_ICON, RT_GROUP_ICON, RT_VERSION))
    imagens, grupo = _icones(ICONE)
    h = k32.BeginUpdateResourceW(str(arquivo), False)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    guarda = []                                   # mantém vivos os buffers até o fim

    def gravar(tipo, nome, idioma, dados):
        ref = ctypes.c_wchar_p(nome) if isinstance(nome, str) else None
        if ref:
            guarda.append(ref)
        buf = ctypes.create_string_buffer(dados, len(dados)) if dados else None
        guarda.append(buf)
        ok = k32.UpdateResourceW(h, tipo, ctypes.cast(ref, ctypes.c_void_p) if ref else nome,
                                 idioma, buf, len(dados))
        if not ok:
            erro = ctypes.get_last_error()
            k32.EndUpdateResourceW(h, True)
            raise ctypes.WinError(erro)

    for tipo, nome, idioma in velhos:
        gravar(tipo, nome, idioma, b"")
    for i, imagem in enumerate(imagens, 1):
        gravar(RT_ICON, i, INGLES_EUA, imagem)
    gravar(RT_GROUP_ICON, 1, INGLES_EUA, grupo)
    gravar(RT_VERSION, 1, INGLES_EUA, versao(versao_texto, descricao, nome_arquivo))
    if not k32.EndUpdateResourceW(h, False):
        raise ctypes.WinError(ctypes.get_last_error())


def _base():
    """Pasta do Python de verdade, a que o ambiente aponta no pyvenv.cfg."""
    for linha in (SCRIPTS.parent / "pyvenv.cfg").read_text("utf-8").splitlines():
        chave, _, valor = linha.partition("=")
        if chave.strip() == "home":
            return Path(valor.strip())
    raise RuntimeError("pyvenv.cfg sem home")


def _versao_instalada():
    try:
        import atualizacao
        return atualizacao.instalada() or "1.0.0"
    except Exception:
        return "1.0.0"


def criar(destino=None, base=None, versao_texto=None):
    """Monta o Whisper Fogo.exe: o pythonw da base com as DLLs ao lado, ícone e
    nome do programa. Monta numa cópia temporária e troca no fim, então um
    executável pela metade nunca fica no lugar."""
    destino = Path(destino or PROGRAMA)
    base = Path(base or _base())
    for dll in ("python%d%d.dll" % sys.version_info[:2],) + DLLS:
        if (base / dll).exists() and not (destino.parent / dll).exists():
            shutil.copy2(base / dll, destino.parent / dll)
    temporario = destino.with_suffix(".novo")
    shutil.copy2(base / "pythonw.exe", temporario)
    _carimbar(temporario, base / "pythonw.exe", versao_texto or _versao_instalada())
    temporario.replace(destino)
    return destino


def carimbar_motor(servidor):
    """O whisper-server roda como processo filho e aparece embaixo do Whisper
    Fogo no Gerenciador de Tarefas: leva o nome e o ícone do programa também.
    Carimba uma cópia e troca no fim; com o servidor aberto, fica para a próxima."""
    servidor = Path(servidor)
    marca = servidor.with_name("carimbado")
    if marca.exists():
        return
    try:
        temporario = servidor.with_suffix(".novo")
        shutil.copy2(servidor, temporario)
        _carimbar(temporario, servidor, _versao_instalada(), DESCRICAO, servidor.name)
        temporario.replace(servidor)
        marca.touch()
    except Exception as e:
        print(f"[motor sem o nome do programa, tento na próxima abertura] {e}", file=sys.stderr)


def garantir():
    """Cria o executável se ainda não existe. Quem atualiza pelo menu chega aqui
    rodando o pythonw.exe antigo, e a partir da abertura seguinte já roda o
    Whisper Fogo.exe."""
    if not PROGRAMA.exists():
        try:
            criar()
        except Exception as e:
            print(f"[executável não criado] {e}", file=sys.stderr)
    return PROGRAMA if PROGRAMA.exists() else SCRIPTS / "pythonw.exe"


def atualizar_atalhos():
    """Atalhos "Whisper Fogo" do Desktop e do menu Iniciar que ainda abrem pelo
    pythonw.exe passam a abrir pelo Whisper Fogo.exe. O atalho é refeito inteiro e
    relido do disco: editar só o alvo de um .lnk pode zerar o resto em silêncio."""
    if not PROGRAMA.exists():
        return
    try:
        from comtypes.client import CreateObject
        ws = CreateObject("WScript.Shell", dynamic=True)
        for pasta in ("Desktop", "Programs"):
            lnk = Path(ws.SpecialFolders(pasta)) / "Whisper Fogo.lnk"
            if not lnk.exists():
                continue
            velho = ws.CreateShortcut(str(lnk))
            if Path(velho.TargetPath) == PROGRAMA:
                continue
            argumentos, pasta_trabalho = velho.Arguments, velho.WorkingDirectory
            descricao = velho.Description
            temporario = lnk.with_name("Whisper Fogo.novo.lnk")
            novo = ws.CreateShortcut(str(temporario))
            novo.TargetPath = str(PROGRAMA)
            novo.Arguments = argumentos or f'"{CODIGO / "voz.py"}"'
            novo.WorkingDirectory = pasta_trabalho or str(CODIGO)
            novo.IconLocation = f"{ICONE},0"
            novo.Description = descricao
            novo.WindowStyle = 7
            novo.Save()
            if Path(ws.CreateShortcut(str(temporario)).TargetPath) == PROGRAMA:
                temporario.replace(lnk)
            else:
                temporario.unlink(missing_ok=True)
                print(f"[atalho não atualizado] {lnk}", file=sys.stderr)
    except Exception as e:
        print(f"[atalhos não atualizados] {e}", file=sys.stderr)


def _autoteste():
    import json
    import subprocess
    import tempfile
    assert struct.unpack_from("<HHH", versao("1.6.0"))[0] == len(versao("1.6.0"))
    with tempfile.TemporaryDirectory() as t:
        venv = Path(t) / "venv"
        scripts = venv / "Scripts"
        scripts.mkdir(parents=True)
        base = Path(sys.base_prefix)
        (venv / "pyvenv.cfg").write_text(f"home = {base}\ninclude-system-site-packages = false\n")
        exe = criar(scripts / PROGRAMA.name, base, "1.6.0")
        tipos = {t for t, _, _ in _recursos(exe, (RT_ICON, RT_GROUP_ICON, RT_VERSION))}
        assert tipos == {RT_ICON, RT_GROUP_ICON, RT_VERSION}, tipos
        assert len(_recursos(exe, (RT_ICON,))) == len(_icones(ICONE)[0])
        # nome e editora, lidos do jeito que o Windows lê
        ver = ctypes.WinDLL("version")
        n = ver.GetFileVersionInfoSizeW(str(exe), None)
        buf = ctypes.create_string_buffer(n)
        assert ver.GetFileVersionInfoW(str(exe), 0, n, buf)
        lido = {}
        for campo in ("FileDescription", "CompanyName", "ProductName"):
            p, tam = ctypes.c_void_p(), wintypes.UINT()
            assert ver.VerQueryValueW(buf, f"\\StringFileInfo\\040904B0\\{campo}",
                                      ctypes.byref(p), ctypes.byref(tam))
            lido[campo] = ctypes.wstring_at(p, tam.value).rstrip("\0")
        assert lido == {"FileDescription": "Whisper Fogo", "CompanyName": "Abajur",
                        "ProductName": "Whisper Fogo"}, lido
        # roda como Python do ambiente: biblioteca padrão da base, prefixo do ambiente
        saida = Path(t) / "saida.txt"
        codigo = (f"import sys, json; open(r'{saida}', 'w').write("
                  "json.dumps([sys.prefix, sys.base_prefix, sys.executable]))")
        subprocess.run([str(exe), "-c", codigo], check=True, timeout=60)
        prefixo, base_prefixo, executavel = json.loads(saida.read_text())
        assert Path(prefixo) == venv and Path(base_prefixo) == base, (prefixo, base_prefixo)
        assert Path(executavel).name == PROGRAMA.name, executavel
        assert not (scripts / "Whisper Fogo.novo").exists()
    print("executavel: autoteste ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        _autoteste()
    else:
        print(criar())
