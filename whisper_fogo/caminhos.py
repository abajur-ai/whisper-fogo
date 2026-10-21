"""Onde ficam o código e onde ficam os dados, em cada sistema.

No Windows os dois moram na mesma pasta, que é onde o programa é instalado.

No macOS o aplicativo assinado é só o interpretador, e é a ele que o sistema
concede microfone e acessibilidade, presos à assinatura. Para que atualizar o
programa não mude a assinatura (e não peça as permissões de novo), o código fica
em `app/` dentro da pasta de dados que o macOS reserva para cada programa, ao
lado do histórico de ditados e do dicionário que você ensina.
"""
import sys
from pathlib import Path

MAC = sys.platform == "darwin"

CODIGO = Path(__file__).parent

if MAC:
    DADOS = Path.home() / "Library" / "Application Support" / "WhisperFogo"
    DADOS.mkdir(parents=True, exist_ok=True)
else:
    DADOS = CODIGO
