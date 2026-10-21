<div align="center">

[Leia em português](README.md) · **English**

<img src="docs/img/banner.png" alt="Whisper Fogo" width="820">

**Free voice transcription that runs entirely on your computer, built first for Portuguese.**

You speak, and the text shows up wherever your cursor is. In any app.
No cloud, no subscription, no account to create.

<br>

<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.bat"><img src="docs/img/botao-windows.svg" alt="Download the Windows installer" height="28"></a>&nbsp;&nbsp;<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.zip"><img src="docs/img/botao-macos.svg" alt="Download the macOS installer" height="28"></a>

<sub><b>Windows</b> 10 and 11. <b>macOS</b> 11 and later on Apple Silicon, 10.15 and later on Intel.<br>
The first time you open it, both systems show a security warning, because the app is not signed with a paid developer account.
<a href="#installation">See the step by step</a>.</sub>

<br><br>

![Free](https://img.shields.io/badge/price-free-FB5B04)
![Runs offline](https://img.shields.io/badge/cloud-none-FB5B04)
![Portuguese](https://img.shields.io/badge/built%20for-Portuguese-FB5B04)
![Any graphics card](https://img.shields.io/badge/graphics%20card-NVIDIA%20%7C%20AMD%20%7C%20Intel%20%7C%20Apple-FB5B04)
![MIT License](https://img.shields.io/badge/license-MIT-555555)

A product by [Abajur](https://abajur.ai).

</div>

---

## Why it exists

Good voice dictation has always been designed around English. The tools worth using
charge a subscription, send your voice to the cloud and treat Portuguese as one more
language on the list: they write "cloud" when you said "Claude", mangle your
company's name and drop the accents.

Whisper Fogo starts from the other side. **Portuguese is the main language, not an
item on a list.** The model settings, the punctuation and the dictionary that learns
your words are tuned for people who speak and write in Portuguese.

And it is **free** and runs **entirely on your computer**. No audio, no
transcription and no word from your dictionary ever leaves your machine. There is no
account, no server to go down, no minute limit.

The app itself speaks Portuguese: menus, buttons and messages are in Portuguese, and
this page quotes them as they appear on screen, with the English meaning next to
them.

---

## New in version 1.5: fast on any computer

Up to version 1.4, Whisper Fogo was only fast with an **NVIDIA** graphics card. The
transcription engine back then,
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), runs on
[CTranslate2](https://github.com/OpenNMT/CTranslate2), which can only use two things:
the processor and CUDA, which is NVIDIA-only. AMD cards, Intel graphics and the chip
in Macs were left out, and transcription fell back to the processor. In practice,
anyone without NVIDIA waited almost half a minute to see a 10-second sentence turn
into text.

**Starting with 1.5, the engine is [whisper.cpp](https://github.com/ggml-org/whisper.cpp)**,
the same foundation as the most used open source transcription apps (Handy, Buzz,
OpenWhispr, Vibe, VoiceInk). It talks to the graphics card through **Vulkan** on
Windows, which NVIDIA, AMD and Intel all support, and through **Metal** on the Mac.
The model is still the same Whisper `large-v3-turbo`, and the rest of the app did not
change.

| Computer | Before (1.4) | Now (1.5) |
|---|---|---|
| Laptop with NVIDIA | fast | just as fast |
| Laptop with Intel or AMD integrated graphics | processor, slow | graphics card, fast |
| Dedicated AMD or Intel Arc card | processor, slow | graphics card, fast |
| Mac with Apple Silicon | processor, slow | the chip's graphics, through Metal |
| No graphics card | processor | processor, faster than before |

**Measured on 20/10/2026 on one laptop** (Intel Core i7-13700H, Intel Iris Xe
integrated graphics and a 6 GB RTX 4050), with real speech in Portuguese:

| Where transcription runs | 11.5 s of speech | 11 min of speech |
|---|---|---|
| RTX 4050, old engine (CUDA) | 0.9 s | 37 s |
| RTX 4050, new engine (Vulkan) | 1.0 to 1.3 s | 41 to 43 s |
| Intel Iris Xe integrated, old engine | 28 to 33 s (processor) | not measured |
| Intel Iris Xe integrated, new engine | 5.2 s | 145 s |
| Processor only, old engine | 28 to 33 s | not measured |
| Processor only, new engine | 19 to 21 s | not measured |

With NVIDIA the difference is tenths of a second on a short sentence. On integrated
graphics, which is what most laptops have, the same sentence comes out five to six
times faster than before.

---

## How to use it

| You do | On Windows | On macOS | What happens |
|---|---|---|---|
| Speak while holding the keys | `Ctrl` + `Shift` | `Fn` | Records while you hold and pastes the text when you release |
| Speak hands-free | `Ctrl` + `Shift` + `Space` | `Fn` + `Space` | Talk as long as you want; `Ctrl` + `Shift` (or `Fn`) stops |
| Click the flame icon | in the system tray | in the menu bar | Opens the admin panel |
| Fix a word in the text field | | | The app learns your spelling |

The text goes wherever your cursor is: code editor, chat, email, terminal,
spreadsheet, a form in the browser. If the app accepts text, it accepts your voice.

On Windows, all three shortcuts can be changed in the panel (see
[Shortcuts your way](#shortcuts-your-way)).

---

## The admin panel

<div align="center">
<img src="docs/img/painel.png" alt="Whisper Fogo admin panel" width="820">
</div>

<br>

Everything you said is kept here, newest first.

- **Nothing gets lost.** Every transcription is saved before it goes to the
  clipboard. If no text field had focus, the paste goes nowhere, but the text is
  still in the panel: one click on **Copiar transcrição** ("Copy transcription") and
  you are done.
- **The whole history, no waiting.** The list loads in batches as you scroll, so
  thousands of transcriptions open instantly. The arrow keys move one at a time.
- **Clear what you want.** **Limpar histórico** ("Clear history") shows checkboxes
  next to each transcription, with **Selecionar todas** ("Select all"), and asks for
  confirmation before deleting.
- **If a transcription fails**, the audio is saved to disk instead of disappearing.

---

## It learns your words

<div align="center">
<img src="docs/img/aviso.png" alt="Learned spelling notice">
</div>

<br>

You dictated, the text was pasted and you fixed a word right there? Whisper Fogo
notices, learns the right spelling and gets it right from then on. A notice in the
corner of the screen shows what was learned, with **Desfazer** ("Undo") in case you
don't want it.

It is not a keylogger: the app asks the system for the field's content, the same way
a screen reader does, and only for 60 seconds after pasting. Password fields are never
read, and none of it goes into any log.

### The Dictionary

<div align="center">
<img src="docs/img/dicionario.png" alt="Whisper Fogo spelling dictionary" width="820">
</div>

<br>

The **Dicionário** ("Dictionary") button in the panel shows everything that was
learned: each correct spelling with all the wrong forms that lead to it, and the
status of each one.

- **Ativa** ("Active"): fixes every transcription.
- **Aguardando** ("Waiting"): a common Portuguese word corrected only once. It
  becomes active on the second identical correction, or when you click **Ativar**
  ("Activate"). Proper names, brands and acronyms are active from the first one.

There you can edit the correct spelling or any form, add and remove forms, create
spellings by hand and delete one, several or all of them. Everything saves on its
own, and the next transcription already uses the new dictionary.

If you prefer a file, `dicionario.json` accepts fixed replacements, brands that only
get the capitalization wrong and the vocabulary the recognizer should expect to hear:

```json
{
  "trocas":     { "Cloud Code": "Claude Code", "Verso": "Vercel" },
  "maiusculas": [ "GitHub", "PostgreSQL" ],
  "hotwords":   [ "Kubernetes", "endpoint", "deploy" ],
  "expansoes":  false
}
```

`expansoes` turns on replacing "pra" with "para" and "tá" with "está" in the final
text. After editing, use **Recarregar dicionário** ("Reload dictionary") in the icon
menu.

---

## Shortcuts your way

<div align="center">
<img src="docs/img/configuracoes.png" alt="Whisper Fogo shortcut settings" width="820">
</div>

<br>

In the panel's gear, every action has **Regravar** ("Re-record"): you click, press
the keys of the combination, watch each one show up on screen and confirm with the
mouse. A single key works too, like the ones on a macro keypad (`F13`, `F14`), and it
takes effect right away, without restarting. The icon menu always shows the current
keys, and **Restaurar padrão** ("Restore default") puts everything back.

Available on Windows. On macOS the keys are the system's (`Fn`).

---

## Always ready, always up to date

- **Starts with the system.** Turn on the computer and the flame is in the tray.
  If you don't want that, turn it off in Task Manager, and the choice is respected.
- **Tells you when there is a new version.** Every time it opens, the app checks the
  latest version published here. If there is something new, a notice appears along
  with the **Atualizar para a versão X** ("Update to version X") item in the icon
  menu. The update keeps your history, your dictionary and your shortcuts, and the
  app restarts on its own.
- **Verificar atualização** ("Check for updates"), in the same menu, checks whenever
  you want.

On macOS it works the same way: the update replaces only the app's code, and the
microphone and accessibility permissions keep working.

---

## Installation

### If you just want to use it

Click the button for your system, the file downloads and you double-click it. The
installer checks whether your machine can handle it, installs everything in an
isolated folder, downloads the engine and the model, prepares the graphics card,
creates the shortcuts and opens the app. It touches nothing outside its own folder.

<div align="center">

<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.bat"><img src="docs/img/botao-windows.svg" alt="Download the Windows installer" height="28"></a>&nbsp;&nbsp;<a href="https://github.com/abajur-ai/whisper-fogo/releases/latest/download/Instalar-Whisper-Fogo.zip"><img src="docs/img/botao-macos.svg" alt="Download the macOS installer" height="28"></a>

</div>

On both systems the app is not signed with a paid account, so the first time a
security warning shows up. It is part of the path and goes away after the first
approval.

**On Windows**

1. Double-click the downloaded file.
2. Defender asks whether you trust it. Click **More info** and then **Run anyway**.
3. The installation runs to the end, creates the shortcut on the Desktop and in the
   Start menu and opens the app in the tray.

**On macOS**

1. The download is a compressed file. Double-click it to get the **Instalar Whisper
   Fogo** ("Install Whisper Fogo") app.
2. Double-click the app. The system says **the item could not be opened**: close it
   with **Done**, not Move to Trash.
3. Open **System Settings > Privacy & Security**, scroll to the end, to the
   **Security** section, and click **Open Anyway** on the Instalar Whisper Fogo line.
   If the line is not there, open the app again so the warning shows up again.
4. Double-click the app once more. The installation runs to the end, the app opens in
   the menu bar, gets a Dock icon and starts opening with the Mac.

On the first recording, macOS asks for **Microphone** and **Accessibility**, both on
behalf of Whisper Fogo. Only once: later updates do not ask again.

The installer also reserves the `Fn` key for Whisper Fogo. On its own, it no longer
opens Apple's dictation, the emoji picker or the input source switcher, which would
fire along with every dictation.

### If you want to work on the code

```bash
git clone https://github.com/abajur-ai/whisper-fogo.git
cd whisper-fogo

# Windows
powershell -ExecutionPolicy Bypass -File instalador/instalar.ps1

# macOS
bash instalador/instalar.sh
```

The installer detects that it is inside the repository and uses your local files
instead of downloading them again.

### What your machine needs

Speeds **measured** on 20/10/2026 on a laptop with an Intel Core i7-13700H, Intel
Iris Xe integrated graphics and a 6 GB RTX 4050, with 11 minutes of real speech in
Portuguese.

**On Windows**

|  | Minimum | Recommended | Ideal |
|---|---|---|---|
| **System** | Windows 10, 64-bit | Windows 10 or 11 | Windows 11 |
| **Graphics card** | none, runs on the processor | recent integrated (Intel Iris Xe, AMD Radeon) | dedicated NVIDIA, AMD or Intel Arc with 4 GB or more |
| **Free graphics memory** | zero | uses system memory | 2 GB |
| **RAM** | 4 GB | 8 GB | 16 GB or more |
| **Disk** | 1.1 GB | 1.8 GB | 1.8 GB |
| **Speed** | ~0.6x real time | ~4.6x | ~16x |

**On macOS**

|  | Minimum | Recommended | Ideal |
|---|---|---|---|
| **Chip** | Intel Core i5 (processor only) | Apple Silicon M1 or M2 | Apple Silicon Pro, Max or M3 and later |
| **System** | macOS 10.15 (Intel) or 11 (Apple Silicon) | macOS 13 | macOS 14 or newer |
| **RAM** | 8 GB | 8 GB | 16 GB or more |
| **Disk** | 1.1 GB | 1.8 GB | 1.8 GB |
| **Speed** | not measured (Intel, processor only) | ~6x real time (M1) | not measured |

On Apple Silicon, transcription uses the chip's graphics through Metal. Measured on
20/10/2026 on an 8 GB MacBook Air M1: 10 seconds of speech in 2.9 seconds and 39
seconds in 6.2 seconds.

**What the speed means:** how many times faster than real time. With a dedicated
card, 1 minute of speech becomes text in about 4 seconds. On integrated graphics, in
about 13 seconds. On the processor alone, in about 1 minute and 40 seconds.

**Graphics memory used:** about 1.9 GB, the 1.6 GB model plus room for computation.
After 10 minutes without use, the model leaves the graphics memory on its own.

<details>
<summary><b>How the engine uses your graphics card</b></summary>

<br>

- **Which card.** On Windows, the engine asks Vulkan which cards exist. On a laptop
  with both integrated and dedicated graphics, the dedicated one is chosen, even when
  Windows lists the integrated one first. With only integrated graphics, that is the
  one that works. On a Mac with Apple Silicon, it is the chip's graphics, through
  Metal.
- **No usable card.** Vulkan comes with the NVIDIA, AMD and Intel graphics drivers.
  Without it, or if the card fails to load the model, transcription continues on the
  processor, on its own, with nothing for you to do.
- **Two precisions of the same model.** On the graphics card, `large-v3-turbo` runs
  at full precision (1.6 GB). On the processor, it runs at 8 bits (0.9 GB), which is
  one and a half times faster there, with the same text. The installer downloads only
  the one your machine uses.
- **The first time on a card.** The graphics driver compiles the engine's programs
  on the first transcription, which would take tens of seconds. That is why the
  installer runs a test transcription at the end, and the driver keeps the result.
  Your first real sentence already comes out at normal speed.
- **Graphics driver updated while the app is open.** If the engine goes down, it
  comes back up on its own and repeats the transcription. If it still fails, the
  audio is saved to disk.

</details>

---

## What gets installed

| Component | Size | What for |
|---|---|---|
| Whisper `large-v3-turbo` | 1.6 GB with a graphics card, 0.9 GB without | Transcribing speech |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) engine | 58 MB on Windows, 9 MB on Mac | Running the model on the card or the processor |
| Isolated Python and libraries | ~120 MB | The app itself |

The engine is built from the whisper.cpp source by this repository's own GitHub
workflow, and the app checks the SHA-256 of every downloaded file before using it.

**Measured speed** on a laptop RTX 4050: 11 minutes of speech transcribed in 42
seconds, 16 times faster than real time. Short everyday sentences come out in 1 to 3
seconds.

---

## Privacy and performance, in numbers

- **0 bytes** sent while you use it. The internet is only used to download the app,
  the engine and the model, once, and to check for a new version.
- **127.0.0.1** is the only address the engine listens on: it runs in a process next
  to the app and accepts no connection from outside your machine.
- **0 accounts** to create. No login, no telemetry, no server.
- **0 audio files** kept: the recording lives in memory only until it becomes text.
- **60 seconds** is the window in which the app watches the field to learn your
  spelling. Outside it, it looks at nothing.
- **1 hour** of continuous speech per recording, the cap against a microphone left
  open by mistake.
- **10 minutes** without use and the model gives the graphics memory back.

---

## How the app is built

Plain Python, no framework, no Electron. Recognition runs in whisper.cpp's
`whisper-server`, in a process next to the app, which the app starts, uses and shuts
down on its own. Each file does one thing:

| File | Responsibility |
|---|---|
| `voz.py` | The app: icon, recording, transcription, pasting, start with the system |
| `motor.py` | The engine: download, card choice, server start-up and transcription |
| `teclado.py` | The global shortcut, with the hold and hands-free state machine |
| `atalhos.py` | Key combinations, the defaults and each key's name |
| `historico.py` | The on-disk log and the admin panel |
| `grafias.py` | The panel's Dictionary |
| `configuracoes.py` | The panel's settings, with shortcut re-recording |
| `tema.py` | The look: colors, title bar, buttons, layers and scrolling |
| `aprendizado.py` | Decides what becomes a spelling from your corrections |
| `observador.py` | Reads the field through the accessibility API and watches for 60 seconds |
| `corrigir.py` | Applies the dictionary to the transcription |
| `atualizacao.py` | Checks for and applies the version published here |
| `aviso.py` | The learned spelling notice, with undo |
| `clip.py` | Clipboard and pasting, per system |
| `caminhos.py` | Where the code and the data live on each system |

**Tests:** 140 asserts, running without a microphone or a graphics card, and without
touching your data:

```bash
cd whisper_fogo
python corrigir.py         # dictionary and expansions
python observador.py       # anchor and watch window
python tema.py             # title trimming and scroll bar
python grafias.py          # Dictionary rules
python atalhos.py          # key combinations
python atualizacao.py      # version comparison and code swap
python motor.py            # card choice, verified download and text assembly
python historico.py --teste
python teste_corte.py      # long recording, safety cutoff and icon color
```

---

## Windows and macOS

| Feature | Windows | macOS |
|---|---|---|
| Dictation with a global shortcut | `Ctrl` + `Shift` | `Fn` |
| Re-recordable shortcuts | yes | no, uses `Fn` |
| Pasting at the cursor | yes | yes |
| Transcription | NVIDIA, AMD or Intel graphics (Vulkan), or processor | Apple Silicon graphics (Metal); Intel Mac on the processor |
| Admin panel and Dictionary | yes | yes |
| Learning from your corrections | UI Automation | Accessibility API |
| Starts with the system | yes | yes |
| Updates | inside the app | inside the app |

**On Windows** Whisper Fogo lives in `AppData\Local\WhisperFogo`, with Python and the
libraries in an isolated folder, shortcuts on the Desktop and in the Start menu and
the flame in the tray next to the clock.

**On macOS** it is an app in `~/Applications`, in the menu bar and in the Dock. The
app is only the interpreter, with Whisper Fogo's name and icon, and it is what macOS
grants microphone and accessibility to. The code, the libraries, the model and your
data live in `~/Library/Application Support/WhisperFogo`, and only that folder is
replaced by updates: the app does not change, and the permissions keep working.

---

## FAQ

**Does my voice go to any server?**
No. The model runs on your machine. You can turn off the internet after installing
and the app keeps working the same.

**Is it really free?**
Yes. No paid plan, no minute limit, no ads.

**Does it work in any app?**
In any text field that accepts pasting.

**Do I need an expensive graphics card? Does it have to be NVIDIA?**
No and no. Since version 1.5, any card with Vulkan works: NVIDIA, AMD or Intel,
dedicated or a laptop's integrated graphics. On a Mac with Apple Silicon, the chip's
own. With no card at all, it runs on the processor, more slowly.

**Why does the first transcription of the day take longer?**
The model loads the first time you speak, which takes a few seconds. After that it
stays in memory until you go 10 minutes without speaking.

**I was already on version 1.4. What changes for me?**
Nothing on screen or in how you use it: history, Dictionary, shortcuts and learned
spellings stay as they are. After updating from the icon menu, the app downloads the
new engine and the model on its own, in the background, as soon as it opens. If you
dictate before the download finishes, that first transcription waits for it. On the
Mac, coming from 1.4 means installing one last time from the download button and
allowing microphone and accessibility again; from then on, updates come from the menu
and the permissions stay.

**Does it work in English?**
The recognizer understands dozens of languages, but everything here is tuned for
Portuguese: the dictionary, the punctuation, the list of common words.

**Can I use it at work?**
Yes. The license is MIT, and since nothing leaves the machine, no client data travels
outside.

---

## Contributing

Issues and pull requests are welcome. What helps the most:

1. **Cases where the transcription gets Portuguese badly wrong**, with the audio if
   possible.
2. **Words the learning should or should not have picked up.**
3. **Reports from Macs and macOS versions we have not tested**, especially Intel.
4. **Measurements on cards we have not tested**, especially AMD and Intel Arc: how
   long one sentence takes and the card's name.

The code is written and commented in Portuguese, explaining the reasons behind each
decision.

---

## Credits

Built on [whisper.cpp](https://github.com/ggml-org/whisper.cpp) and the
[Whisper](https://github.com/openai/whisper) model, with the
[Silero VAD](https://github.com/snakers4/silero-vad) speech detector. Up to version
1.4 the engine was [faster-whisper](https://github.com/SYSTRAN/faster-whisper). The
list of common Portuguese words comes from
[FrequencyWords](https://github.com/hermitdave/FrequencyWords).

---

<div align="center">

A product by **[Abajur](https://abajur.ai)**
[MIT](LICENSE) license

</div>
