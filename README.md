<div align="center">

<img src="docs/img/banner.png" alt="Whisper Fogo" width="820">

**Transcrição de voz grátis, que roda inteira na sua máquina e é especialista em língua portuguesa.**

Você fala, o texto aparece onde o cursor estiver. Em qualquer programa.
Sem nuvem, sem mensalidade, sem conta para criar.

<br>

<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.bat"><img src="docs/img/botao-windows.svg" alt="Baixar o instalador para Windows" height="28"></a>&nbsp;&nbsp;<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.zip"><img src="docs/img/botao-macos.svg" alt="Baixar o instalador para macOS, versão beta" height="28"></a>

<sub><b>Windows:</b> versão estável. <b>macOS:</b> versão beta, ainda em teste.<br>
Na primeira abertura, os dois sistemas mostram um aviso de segurança, porque o programa não é assinado com conta paga.
<a href="#instalação">Veja o passo a passo</a>.</sub>

<br><br>

![Grátis](https://img.shields.io/badge/preço-grátis-FB5B04)
![Roda offline](https://img.shields.io/badge/nuvem-nenhuma-FB5B04)
![Português](https://img.shields.io/badge/especialista%20em-língua%20portuguesa-FB5B04)
![Licença MIT](https://img.shields.io/badge/licença-MIT-555555)

Um produto da [Abajur](https://abajur.ai).

</div>

---

## Por que ele existe

Ditado por voz bom sempre foi pensado em inglês. As ferramentas que valem a pena
cobram mensalidade, mandam a sua voz para a nuvem e tratam o português como mais
um idioma da lista: escrevem "cloud" quando você disse "Claude", trocam o nome da
sua empresa e esquecem o acento.

O Whisper Fogo começa pelo outro lado. **A língua portuguesa é o idioma principal,
e não um item da lista.** O modelo, a pontuação e o dicionário que aprende as suas
palavras foram afinados para quem fala e escreve em português.

E ele é **grátis** e roda **inteiro no seu computador**. Nenhum áudio, nenhuma
transcrição e nenhuma palavra do seu dicionário saem da sua máquina. Não há conta,
não há servidor para cair, não há limite de minutos.

---

## Como usar

| Você faz | No Windows | No macOS | O que acontece |
|---|---|---|---|
| Fala segurando a tecla | `Ctrl` + `Shift` | `Fn` | Grava enquanto segurar e cola o texto ao soltar |
| Fala de mãos livres | `Ctrl` + `Shift` + `Espaço` | `Fn` + `Espaço` | Fala à vontade; `Ctrl` + `Shift` (ou `Fn`) encerra |
| Clica no ícone da chama | na bandeja | na barra de menus | Abre o painel administrativo |
| Corrige uma palavra no campo | | | O programa aprende a sua grafia |

O texto vai para onde o cursor estiver: editor de código, chat, e-mail, terminal,
planilha, formulário no navegador. Se o programa aceita texto, aceita a sua voz.

No Windows, as três teclas podem ser trocadas pelo painel (veja
[Teclas do seu jeito](#teclas-do-seu-jeito)).

---

## O painel administrativo

<div align="center">
<img src="docs/img/painel.png" alt="Painel administrativo do Whisper Fogo" width="820">
</div>

<br>

Tudo o que você falou fica guardado aqui, da mais recente para a mais antiga.

- **Nada se perde.** Toda transcrição é salva antes de ir para a área de
  transferência. Se não havia campo de texto em foco, a colagem cai no vazio, mas o
  texto continua no painel: um clique em **Copiar transcrição** e pronto.
- **Histórico inteiro, sem espera.** A lista carrega em blocos conforme você rola,
  então milhares de transcrições abrem na hora. As setas do teclado andam de uma em
  uma.
- **Limpar o que quiser.** **Limpar histórico** abre caixas de seleção ao lado de
  cada transcrição, com **Selecionar todas**, e pede confirmação antes de apagar.
- **Se a transcrição falhar**, o áudio é guardado em disco em vez de sumir.

---

## Ele aprende as suas palavras

<div align="center">
<img src="docs/img/aviso.png" alt="Aviso de grafia aprendida">
</div>

<br>

Ditou, o texto colou e você corrigiu uma palavra ali mesmo? O Whisper Fogo percebe,
aprende a grafia certa e passa a acertar sempre. Um aviso no canto da tela mostra o
que foi aprendido, com **Desfazer** para o caso de você não querer.

Não é keylogger: o programa pergunta ao sistema o conteúdo do campo, pelo mesmo
caminho que um leitor de tela usa, e só durante 60 segundos depois de colar. Campo
de senha nunca é lido, e nada disso vai para log nenhum.

### O Dicionário

<div align="center">
<img src="docs/img/dicionario.png" alt="Dicionário de grafias do Whisper Fogo" width="820">
</div>

<br>

No botão **Dicionário** do painel você vê tudo o que foi aprendido: cada grafia
certa com todas as formas erradas que levam a ela, e o status de cada uma.

- **Ativa:** corrige toda transcrição.
- **Aguardando:** palavra comum do português corrigida uma vez só. Ela vira ativa
  na segunda correção igual, ou quando você clica em **Ativar**. Nome próprio,
  marca e sigla já entram ativos na primeira.

Ali você edita a grafia certa ou qualquer forma, acrescenta e remove formas, cria
grafias à mão e apaga uma, várias ou todas. Tudo salva sozinho, e a próxima
transcrição já usa o dicionário novo.

Para quem prefere arquivo, o `dicionario.json` aceita trocas fixas, marcas que só
erram a caixa e o vocabulário que o reconhecedor deve esperar ouvir:

```json
{
  "trocas":     { "Cloud Code": "Claude Code", "Verso": "Vercel" },
  "maiusculas": [ "GitHub", "PostgreSQL" ],
  "hotwords":   [ "Kubernetes", "endpoint", "deploy" ],
  "expansoes":  false
}
```

`expansoes` liga a troca de "pra" por "para" e de "tá" por "está" no texto final.
Depois de editar, use **Recarregar dicionário** no menu do ícone.

---

## Teclas do seu jeito

<div align="center">
<img src="docs/img/configuracoes.png" alt="Configurações de teclas do Whisper Fogo" width="820">
</div>

<br>

Na engrenagem do painel, cada ação tem **Regravar**: você clica, aperta as teclas
da combinação, vê cada uma aparecer na tela e confirma com o mouse. Vale tecla
única, como as de um teclado de macros (`F13`, `F14`), e vale na hora, sem
reiniciar. O menu do ícone mostra sempre as teclas atuais, e **Restaurar padrão**
volta tudo ao começo.

Disponível no Windows. No macOS as teclas são as do sistema (`Fn`).

---

## Sempre pronto e sempre atualizado

- **Abre junto com o sistema.** Ligou o computador, a chama está na bandeja.
  Quem não quiser desliga pelo Gerenciador de Tarefas, e a escolha é respeitada.
- **Avisa quando há versão nova.** A cada vez que abre, o programa confere a última
  versão publicada aqui. Se houver novidade, aparece um aviso e o item
  **Atualizar para a versão X** no menu do ícone. A atualização preserva o seu
  histórico, o seu dicionário e as suas teclas, e o programa reinicia sozinho.
- **Verificar atualização**, no mesmo menu, faz a conferência na hora que você quiser.

No macOS, a atualização abre a página da versão nova para baixar.

---

## Instalação

### Para quem só quer usar

Clique no botão do seu sistema, o arquivo baixa e você dá dois cliques nele. O
instalador confere se a sua máquina aguenta, instala tudo numa pasta isolada,
baixa o modelo, cria os atalhos e abre o programa. Não mexe em nada fora da pasta
dele.

<div align="center">

<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.bat"><img src="docs/img/botao-windows.svg" alt="Baixar o instalador para Windows" height="28"></a>&nbsp;&nbsp;<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.zip"><img src="docs/img/botao-macos.svg" alt="Baixar o instalador para macOS, versão beta" height="28"></a>

</div>

Nos dois sistemas o programa não é assinado com conta paga, então na primeira vez
aparece um aviso de segurança. Ele faz parte do caminho e some depois da primeira
autorização.

**No Windows**

1. Dê dois cliques no arquivo baixado.
2. O Defender pergunta se você confia. Clique em **Mais informações** e depois em
   **Executar assim mesmo**.
3. A instalação corre até o fim, cria o atalho no Desktop e no menu Iniciar e abre
   o programa na bandeja.

**No macOS (beta)**

1. O download é um arquivo compactado. Dê dois cliques nele para sair o aplicativo
   **Instalar Whisper Fogo**.
2. Dê dois cliques no aplicativo. O sistema mostra **"o item não foi aberto"**:
   feche no botão **Concluído**, e não em Mover para o Lixo.
3. Abra **Ajustes do Sistema > Privacidade e Segurança**, role até o fim, na seção
   **Segurança**, e clique em **Abrir Mesmo Assim** na linha do Instalar Whisper
   Fogo. Se a linha não estiver lá, abra o aplicativo de novo para o aviso
   reaparecer.
4. Dê dois cliques no aplicativo mais uma vez. A instalação corre até o fim, o
   programa abre na barra de menus, ganha ícone no Dock e passa a abrir junto com
   o Mac.

Na primeira gravação, o macOS pede **Microfone** e **Acessibilidade**, as duas em
nome do Whisper Fogo.

### Para quem quer mexer no código

```bash
git clone https://github.com/abajur-ai/whisper-fogo.git
cd whisper-fogo

# Windows
powershell -ExecutionPolicy Bypass -File instalador/instalar.ps1

# macOS
bash instalador/instalar.sh
```

O instalador detecta que você está dentro do repositório e usa os seus arquivos
locais em vez de baixar de novo.

### O que a sua máquina precisa ter

Números **medidos**, não estimados, numa RTX 4050 de notebook e num MacBook Air M1.

**No Windows**

|  | Mínimo | Recomendado | Ideal |
|---|---|---|---|
| **Placa de vídeo** | nenhuma, roda na CPU | NVIDIA com 4 GB de VRAM | NVIDIA com 6 GB ou mais |
| **VRAM livre** | zero | 2,5 GB | 2,5 GB |
| **Memória RAM** | 4 GB | 8 GB | 16 GB ou mais |
| **Disco** | 4 GB | 4 GB | 4 GB |
| **Velocidade** | ~1,4x o tempo real | ~15x | ~29x |

**No macOS (beta)**

|  | Mínimo | Recomendado | Ideal |
|---|---|---|---|
| **Chip** | Intel Core i5 | Apple Silicon M1 ou M2 | Apple Silicon Pro, Max ou M3 em diante |
| **Sistema** | macOS 11 | macOS 13 | macOS 14 ou mais novo |
| **Memória RAM** | 8 GB | 8 GB | 16 GB ou mais |
| **Disco** | 4 GB | 4 GB | 4 GB |
| **Velocidade** | ~1,2x o tempo real | ~2x | ~4x |

**Traduzindo a velocidade:** é quantas vezes mais rápido que o tempo real. No
Windows, 1 minuto de fala vira texto em uns 45 segundos no mínimo e em 2 segundos
no ideal. No macOS, o mesmo minuto sai em uns 50 segundos no mínimo e em 15
segundos no ideal.

**Quanto ocupa da placa de vídeo:** 2,2 GB na precisão padrão (`float16`) e 1,2 GB
no modo econômico (`int8`). Depois de 10 minutos sem uso, o modelo sai da memória
da placa sozinho.

<details>
<summary><b>Por que precisa ser NVIDIA, e o que acontece com AMD, Intel ou Mac</b></summary>

<br>

O motor de transcrição é o [CTranslate2](https://github.com/OpenNMT/CTranslate2),
que aceita dois tipos de dispositivo: **CPU e CUDA**. Não há suporte a ROCm (AMD),
Metal (Apple), Intel Arc, Vulkan ou OpenCL:

```python
>>> import ctranslate2
>>> ctranslate2.get_supported_compute_types("cuda")
{'float16', 'int8', 'bfloat16', 'float32', ...}
>>> ctranslate2.get_supported_compute_types("rocm")
ValueError: unsupported device rocm
```

Se a sua placa não é NVIDIA, o programa usa a CPU sozinho. **Ele funciona**, na
velocidade da coluna "mínimo". O instalador mede a sua máquina e avisa antes de
baixar qualquer coisa.

</details>

---

## O que é instalado

| Componente | Tamanho | Para quê |
|---|---|---|
| Whisper `large-v3-turbo` | 1,6 GB | Transcrever a fala |
| Python isolado e bibliotecas | ~2 GB | O programa em si |

**Velocidade medida** numa RTX 4050 de notebook: 42 minutos de áudio transcritos em
86 segundos, 29 vezes mais rápido que o tempo real. Falas curtas do dia a dia saem
em 2 a 6 segundos.

---

## Privacidade e desempenho, em números

- **0 bytes** enviados durante o uso. A internet só entra para baixar na instalação e
  para conferir se há versão nova.
- **0 conta** para criar. Não há login, telemetria nem servidor.
- **0 arquivo de áudio** guardado: a gravação vive na memória só até virar texto.
- **60 segundos** é a janela em que o programa observa o campo para aprender a sua
  grafia. Fora dela, ele não olha nada.
- **1 hora** de fala contínua por gravação, o teto contra microfone esquecido aberto.
- **10 minutos** sem uso e o modelo devolve a memória da placa de vídeo.

---

## Como o programa é feito

Python puro, sem framework, sem servidor local, sem Electron. Cada arquivo faz uma
coisa:

| Arquivo | Responsabilidade |
|---|---|
| `voz.py` | O programa: ícone, gravação, transcrição, colagem, início com o sistema |
| `teclado.py` | O atalho global, com a máquina de estados de segurar e de mãos livres |
| `atalhos.py` | As combinações de teclas, o padrão e o nome de cada tecla |
| `historico.py` | O registro em disco e o painel administrativo |
| `grafias.py` | O Dicionário do painel |
| `configuracoes.py` | As configurações do painel, com a regravação de teclas |
| `tema.py` | O visual: cores, barra de título, botões, camadas e rolagem |
| `aprendizado.py` | Decide o que vira grafia a partir das suas correções |
| `observador.py` | Lê o campo pela API de acessibilidade e observa por 60 segundos |
| `corrigir.py` | Aplica o dicionário na transcrição |
| `atualizacao.py` | Confere e aplica a versão publicada aqui |
| `aviso.py` | O aviso de grafia aprendida, com desfazer |
| `clip.py` | Área de transferência e colagem, por sistema |
| `caminhos.py` | Onde ficam o código e os dados em cada sistema |

**Testes:** 123 asserts, rodando sem microfone e sem placa de vídeo, e sem tocar nos
seus dados:

```bash
cd whisper_fogo
python corrigir.py         # dicionário e expansões
python observador.py       # âncora e janela de observação
python tema.py             # corte de títulos e barra de rolagem
python grafias.py          # regras do Dicionário
python atalhos.py          # combinações de teclas
python atualizacao.py      # comparação de versões e troca do código
python historico.py --teste
python teste_corte.py      # gravação longa, corte de segurança e cor do ícone
```

---

## Windows e macOS

| Recurso | Windows | macOS (beta) |
|---|---|---|
| Ditado com atalho global | `Ctrl` + `Shift` | `Fn` |
| Teclas regraváveis | sim | não, usa `Fn` |
| Colagem no cursor | sim | sim |
| Transcrição | GPU NVIDIA ou CPU | CPU |
| Painel administrativo e Dicionário | sim | sim |
| Aprender pela sua correção | UI Automation | API de Acessibilidade |
| Abre com o sistema | sim | sim |
| Atualização | dentro do programa | abre a página da versão |

**No Windows** o Whisper Fogo fica em `AppData\Local\WhisperFogo`, com o Python e
as bibliotecas numa pasta isolada, atalho no Desktop e no menu Iniciar e a chama na
bandeja ao lado do relógio.

**No macOS** ele é um aplicativo em `~/Applications`, com o Python e as bibliotecas
dentro dele, na barra de menus e no Dock. Os seus dados ficam em
`~/Library/Application Support/WhisperFogo`.

---

## Perguntas frequentes

**Minha voz vai para algum servidor?**
Não. O modelo roda na sua máquina. Você pode desligar a internet depois de instalar
e o programa continua funcionando igual.

**É grátis mesmo?**
É. Sem plano pago, sem limite de minutos, sem anúncio.

**Funciona em qualquer programa?**
Em qualquer campo de texto que aceite colar.

**Precisa de placa de vídeo cara?**
Não. Ele foi construído numa RTX 4050 de notebook, que é placa de entrada. Sem
placa nenhuma, roda na CPU, mais devagar.

**Por que a primeira transcrição do dia demora mais?**
O modelo carrega na primeira vez que você fala, o que leva alguns segundos. Depois
fica na memória até você passar 10 minutos sem falar.

**Ele funciona em inglês?**
O reconhecedor entende dezenas de idiomas, mas tudo aqui é afinado para português:
o dicionário, a pontuação, a lista de palavras comuns.

**Posso usar no trabalho?**
Pode. A licença é MIT, e como nada sai da máquina, nenhum dado de cliente trafega
para fora.

---

## Contribuir

Issue e pull request são bem-vindos. O que mais ajuda:

1. **Casos em que a transcrição erra feio** em português, com o áudio se possível.
2. **Palavras que o aprendizado deveria ou não deveria ter pegado.**
3. **Relatos do macOS**, que está em beta.

O código é escrito e comentado em português, explicando o porquê das decisões.

---

## Créditos

Construído sobre [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[CTranslate2](https://github.com/OpenNMT/CTranslate2) e o modelo
[Whisper](https://github.com/openai/whisper). A lista de palavras comuns do
português vem do [FrequencyWords](https://github.com/hermitdave/FrequencyWords).

---

<div align="center">

Um produto da **[Abajur](https://abajur.ai)**
Licença [MIT](LICENSE)

</div>
