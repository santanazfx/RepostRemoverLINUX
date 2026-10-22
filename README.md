# RepostRemoverLINUX

Automatiza a remoção de reposts do TikTok usando Python, Selenium e Brave no Linux. O programa é controlado pelo terminal; você escolhe se quer deixar o navegador visível ou oculto.

> Use somente na sua própria conta ou em uma conta que você tem autorização para gerenciar. A automação depende da interface do TikTok, que pode mudar sem aviso.

## O que dá para fazer

| Opção | Ação |
| --- | --- |
| `1` | Percorrer os reposts e tentar remover todos |
| `2` | Remover reposts cuja legenda corresponde a palavras-chave |
| `3` | Abrir o contador manual e confirmar cada remoção |

O contador mostra o total confirmado por você; ele não consegue verificar sozinho se o TikTok concluiu a remoção.

## Linux: instalação e execução

### 1. Instale os pré-requisitos

- Python 3.9 ou mais recente.
- Brave Browser instalado. O programa procura `brave-browser` no `PATH` e também reconhece as variantes beta e nightly.

Instale o Brave pelas instruções oficiais para Linux em [brave.com/linux](https://brave.com/linux/). Não é necessário instalar Chromium nem Google Chrome.

### 2. Abra o terminal na pasta do projeto

Se ainda não clonou o repositório:

```bash
git clone https://github.com/santanazfx/RepostRemoverLINUX.git
cd RepostRemoverLINUX
```

### 3. Crie o ambiente e instale as dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Ative `.venv` novamente (`source .venv/bin/activate`) sempre que abrir um terminal novo para usar o projeto. Se iniciar `python3 tiktok.py` sem ativar o ambiente, o programa usará automaticamente a `.venv` local, caso ela já exista.

### 4. Inicie

```bash
python tiktok.py
```

Siga as perguntas no terminal:

1. Informe o nome do perfil a processar, com ou sem `@`.
2. Escolha a ação (`1`, `2` ou `3`).
3. Escolha o navegador **visível** ou **oculto**. Se pressionar Enter, a opção padrão é visível.
4. Informe o e-mail/usuário e senha para tentar preencher o login automaticamente. A senha não aparece enquanto é digitada. Para login manual, deixe o campo de e-mail/usuário vazio.
5. No modo `2`, informe as palavras da legenda separadas por vírgula.

## Navegador visível ou oculto?

- **Visível (recomendado):** permite entrar manualmente na conta e resolver CAPTCHA ou código de verificação. Também é obrigatório para o contador manual.
- **Oculto:** o navegador não abre uma janela. É necessário informar e-mail/usuário e senha; se o TikTok pedir uma verificação, execute novamente no modo visível.

No Linux, o programa abre Brave e ajusta o ChromeDriver à versão instalada. Em Windows e macOS, usa Google Chrome.

## Problemas comuns

- **Brave não encontrado:** confirme que o Brave está instalado e que `brave-browser` funciona no terminal.
- **Erro ao iniciar o navegador ou driver:** confira a conexão com a internet e atualize o Brave e as dependências Python.
- **Login não avançou ou surgiu uma verificação:** escolha o navegador visível e conclua o login/CAPTCHA manualmente.
- **Botão ou aba não encontrado:** o TikTok pode ter alterado a página. O programa salva captura de tela e HTML em `debug_screenshots/` quando não encontra o botão de remover; esses arquivos ajudam a identificar qual interação falhou.
- **Interação falhou repetidamente:** interrompa a execução com `Ctrl+C`, confira a janela do navegador e os arquivos de diagnóstico antes de tentar novamente. A remoção automática pode parar antes de processar todos os reposts.

## Arquivos principais

- `tiktok.py` — menu do terminal e modos de remoção/contador.
- `contador.py` — contador manual com confirmação do usuário.
- `selenium_driver.py` — inicialização do Brave no Linux e do Chrome em outros sistemas.
