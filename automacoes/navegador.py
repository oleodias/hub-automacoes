"""
automacoes/navegador.py — criação centralizada do WebDriver (Chrome/Chromium).

POR QUE ISSO EXISTE
-------------------
No servidor (contêiner Docker/Linux) o navegador é o *Chromium* instalado pelo
apt (a versão que o Debian congela, ex.: 150) e o driver casado vem junto no
pacote `chromium-driver` (em /usr/bin/chromedriver). O Dockerfile exporta:

    ENV CHROME_BIN=/usr/bin/chromium
    ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

Se, em vez disso, deixarmos o webdriver-manager baixar o driver da internet, ele
pega SEMPRE a versão mais nova (ex.: 151) — que NÃO casa com o Chromium 150 do
Debian e o robô morre logo ao abrir:

    SessionNotCreatedException: This version of ChromeDriver only supports
    Chrome version 151. Current browser version is 150...

COMO FUNCIONA
-------------
    • CHROME_BIN definido        -> aponta o navegador (options.binary_location).
    • CHROMEDRIVER_PATH existente -> usa esse driver do sistema (servidor).
    • Nenhum dos dois (PC de dev)  -> cai no webdriver-manager, como era antes.

Cada robô continua montando as próprias Options (headless, downloads, detach…)
e só entrega elas prontas aqui. Assim o comportamento no Windows de
desenvolvimento fica idêntico ao de antes, e o servidor passa a usar o par
Chromium+driver casado que o Dockerfile já instalou.

Este módulo só importa bibliotecas externas (selenium/os), então pode ser
carregado tanto por `import navegador` (robôs rodados como script direto, onde
sys.path[0] é a pasta automacoes/) quanto por
`from automacoes.navegador import criar_driver` (código com a raiz no path).
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def criar_driver(options):
    """Cria e devolve o webdriver.Chrome a partir das Options já montadas.

    Prefere o Chromium + chromedriver do sistema (servidor, via CHROME_BIN e
    CHROMEDRIVER_PATH); no dev (Windows, sem essas variáveis) usa o
    webdriver-manager para baixar o driver compatível com o Chrome local.
    """
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path and os.path.exists(chromedriver_path):
        # Servidor: driver do apt, casado com o Chromium. Sem baixar da internet.
        return webdriver.Chrome(service=Service(chromedriver_path), options=options)

    # Fallback dev (Windows): baixa o chromedriver compatível com o Chrome local.
    # Import local de propósito: no servidor esse caminho nunca roda.
    from webdriver_manager.chrome import ChromeDriverManager
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
