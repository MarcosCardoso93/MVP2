# Checklist — validação do AGI contra produção

**✅ Autorizado em 2026-08-06 · destinatário: quem operar a VM de Despesa**

> A pendência **Q20 está fechada**: a autorização para abrir e logar no AGI de
> produção foi concedida. Este documento deixou de ser um pedido e passou a ser o
> procedimento.

---

## 🔴 A única coisa que ainda bloqueia

**As credenciais do AGI precisam ser rotacionadas antes da primeira execução.**

Elas vieram **preenchidas** nos `.env` de dois projetos de origem
(`projeto-6-h20-h21/H20/.env` e `projeto-7-epico-5-carga-agi/.env`), com os
mesmos comprimentos nos dois — provavelmente a mesma credencial, circulando fora
do controle de versão. É o risco **R20**.

Autorização para usar o AGI não é o mesmo que autorização para usar **essa**
credencial. Rotacione, ponha a nova no ambiente da VM (não num `.env`
versionado), e só então siga.

---

## Passo 0 — o ensaio offline, que não precisa de acesso ao AGI

```
python ensaiar_portal_agi.py                        # usa o AGI_AMBIENTE do .env
python ensaiar_portal_agi.py --ambiente homologacao
```

O fluxo tem duas metades, e **só a segunda precisa de rede**:

```
inicializar() ──► acessar_ambiente() ──┊──► login() ──► menus ──► upload
└──── Portal AIR, HTML LOCAL ─────────┘┊    └──── AGI no navegador ────┘
                                (botão ACESSAR)
```

O ensaio exercita a primeira: abre o aplicativo, espera a janela, confere as
três imagens do portal (`bnt_producao_ini`, `bnt_homo_ini`, `card_agi`),
navega até a tela do ambiente e **para antes do ACESSAR**. Não faz login e não
toca no AGI — limite provado em
`rpa3_contestacao_agi_ec/tests/test_ensaio_portal.py`.

Ele também responde os dois 🔎 dos passos 1 e 2 abaixo: qual processo é o AGI, e
se o laço de `inicializar()` pode travar.

⚠️ **O Bootstrap do portal vem de um CDN externo** (`stackpath.bootstrapcdn.com`).
Sem ele, as páginas renderizam só com o CSS local, e a aparência muda — o que
basta para as imagens não casarem. O ensaio diz se o CDN respondeu; **anote em
qual condição ele rodou**, porque é a primeira hipótese quando uma imagem casa
numa máquina e falha na outra.

---

## Antes de tudo: confira as imagens, sem abrir nada

```
python verificar_imagens_agi.py --listar
python verificar_imagens_agi.py --grupo AGI_CONFIG
```

Este comando **não clica, não digita e não abre o AGI** — só procura as imagens
na tela atual e diz quais são encontradas, com o grau de confiança de cada uma.

**Por que fazer isso primeiro.** Sem ele, descobrir uma imagem quebrada custa uma
execução inteira: abrir o AGI, logar, navegar — e falhar no meio, uma imagem por
vez, porque cada `_wait_appear` espera até **180 segundos** antes de desistir.
Sete imagens quebradas eram sete rodadas.

Rode **uma vez por grupo**, com a tela correspondente aberta. Imagem "ausente" só
é problema se a tela dela estiver na frente.

⚠️ Imagem marcada como **FRACA** (casa, mas abaixo de 0.8) é a pior categoria:
ela funciona no teste e **falha de forma intermitente** em produção. Recapture
antes de seguir.

⛔ **Nunca baixe o `confidence` no código para fazer um passo passar.** Confiança
baixa casa o botão errado, e o robô clica nele.

---

## O problema que este roteiro contorna

**Não existe ambiente de teste do AGI**, e não vai existir — o AGI é um
aplicativo de produção numa VM. `ENV=dev` isola o **banco**, e só ele; não há
"AGI de desenvolvimento". A automação é por imagem
(`pyautogui.locateOnScreen` compara pixel), e as 30 capturas em
`unificado/rpa3_contestacao_agi_ec/src/view/imagens/` foram feitas na máquina de
quem escreveu cada projeto de origem — nunca na VM em que este repositório vai
rodar. Resolução, tema do Windows, escala de fonte e versão do AGI mudam pixel, e
pixel diferente é imagem não encontrada.

A decisão foi **validar contra produção, com cuidado**. O cuidado é a combinação
de kill-switches abaixo.

> 🆕 **2026-08-06 — pode haver alternativa.** Ao instalar o aplicativo em
> `unificado/aplicacao_agi/` descobriu-se que o Portal AIR abre **dois**
> ambientes, e que existe um AGI de homologação (`10.129.178.159:7010/Agi/`).
> O robô já sabe abri-lo: `AGI_AMBIENTE=homologacao`. Antes de trocar a decisão
> acima, é preciso confirmar com a área se aquela instância tem dado de Despesa
> utilizável e se a credencial vale nela — ver a pendência **Q20**.

---

## O modo "só leitura"

```ini
# Só o RPA 3 abre o AGI — o sufixo por robô evita ligar isto para os outros.
PERMITIR_ACESSO_AGI_RPA3=true
PERMITIR_UPLOAD_AGI=false     # não sobe arquivo nenhum
PERMITIR_ENVIO_EMAIL=false    # não envia e-mail para operadora

# O banco continua isolado: a validação do AGI não precisa do WebFat real.
ENV=dev
CAMINHO_SQLITE=banco_de_dados/TABELAS_DETRAF_espelho.db

# ⚠️ A numeração CT numa pasta LOCAL. Ela não é banco nem kill-switch: apontada
# para o compartilhamento real, cada rodada consome números da sequência de
# verdade, e eles não voltam.
CAMINHO_CONTROLE_CT=C:\homologacao\CT
```

Confira antes de rodar:

```
python verificar_ambiente.py --rpa rpa3
```

Ele imprime, em destaque, **quais efeitos externos estão ligados** — que é a
linha a conferir antes de cada execução.

Para exercitar só a conferência do relatório, sem o resto do fluxo:

```
python rpa3_contestacao_agi_ec/main.py --etapa verificacao --referencia 202507
```

### O que essa combinação garante

| Efeito | Acontece? | Onde a guarda está |
|---|---|---|
| Abrir o AGI e **fazer login em produção** | ✅ **sim** | inerente — é o que se quer exercitar |
| Baixar o relatório Detraf de Receita/Despesas | ✅ sim | `agi.baixar_remessa` |
| Reescrever esse CSV baixado (correção de aspas) | ✅ sim | `agi._corrigir_aspas_impares` |
| Gravar a planilha de inconsistências em `logs/` | ✅ sim | `verificacao_relatorio.gravar_inconsistencias` |
| `Detraf > Importar Dados` (EXT/INT) | ❌ **não** | `upload_detraf_agi.py:199` |
| `Contestação > Gerenciar` (CONT_PROC) | ❌ **não** | `upload_contestacao_agi.py:129` |
| `Send()` no Outlook | ❌ **não** | `envio_email_contestacao.py` |

⚠️ **As três escritas que sobram são todas locais** — o CSV baixado, a planilha de
inconsistências e o log. Nada é escrito **no AGI**.

⚠️ **O login em produção acontece.** Não há como exercitar a navegação sem ele.
✅ Autorizado em 2026-08-06.

### Isto está provado por teste, não prometido

`rpa3_contestacao_agi_ec/tests/test_orquestracao_rpa3.py::TestModoSoLeitura` roda
o fluxo inteiro com os **uploaders reais** ligados a um AGI que levanta
`AssertionError` ao primeiro toque, e o Outlook idem. Se alguém remover uma
guarda, o teste vermelha.

---

## Antes de ligar qualquer coisa

- [ ] `RPA_DETRAF_DESPESA_AGI_USER` e `RPA_DETRAF_DESPESA_AGI_PASSWORD` vêm do
      ambiente da VM, **não** de um `.env` versionado.
      🔴 As duas credenciais que vieram em `projetos-origem/` **precisam ser
      rotacionadas antes desta validação** (risco R20).
- [ ] `DIRETORIO_AGI` aponta para o `portal_air_vivo.exe` do Portal AIR — em
      `aplicacao_agi/Portal AIR/`, relativo a `unificado/`. **Não** é o
      `adl.exe`, que fica no `runtime/` ao lado (o texto antigo deste item
      mandava apontar para ele, e estava errado).
- [ ] `AGI_AMBIENTE` é o ambiente que se quer exercitar. Ele decide em qual
      botão do portal o robô clica **e** qual host entra na regex do diálogo.
- [ ] `AGI_JANELA_HOST_PRODUCAO` / `AGI_JANELA_HOST_HOMOLOGACAO` batem com o
      host que aparece no título do diálogo de download — ele entra na regex de
      `janela_salvar`. Produção `10.238.6.120`, homologação `10.129.178.159`.
- [ ] `DIRETORIO_RELATORIO_AGI` e `DIRETORIO_INCONSISTENCIAS` existem e são
      graváveis.
- [ ] A VM está com a **resolução e a escala que vão valer em operação**. Mudar
      isso depois invalida qualquer captura recapturada aqui.
- [ ] Ninguém mais está usando a área de trabalho da VM. O `pyautogui` move o
      mouse de verdade: uma janela por cima muda o que está na tela.

---

## Passo a passo, e o que observar em cada um

A ordem segue `agi.py`. Rode com o log em `DEBUG` — cada `_click` registra a
imagem que procurou.

### 1. Abrir o aplicativo — `inicializar()`

Mata os processos do Portal AIR e sobe o executável de `DIRETORIO_AGI`.

- [ ] O AGI abriu.
- **Se falhar:** é `DIRETORIO_AGI` errado ou permissão — não é imagem.

> ✅ **Resolvido em 2026-08-06, pelo passo 0.** O que aqui era dúvida virou
> observação, e as duas correções já estão no `agi.py`:
>
> - **O `portal_air_vivo.exe` é um lançador.** Ele sobe o `adl.exe`, que é quem
>   fica com a janela, e sai — com código 1. São **dois** processos.
> - **`inicializar()` travava.** O laço `while processo.poll() is not None`
>   esperava pelo lançador; com um lançador que sai, ele não termina nunca. O
>   RPA 3 teria travado em silêncio na primeira execução com kill-switch ligado.
>   Agora ele espera pelo processo que **aparece**, e levanta `AGIError` se
>   nenhum aparecer.
> - **`fechar()` deixava o lançador vivo.** Matava só o `adl.exe`, herdado de
>   Receita; agora mata os dois e espera o Windows soltá-los.
>
> Fixado em `rpa3_contestacao_agi_ec/tests/test_agi_ciclo_de_vida.py`.

### 2. Portal → ambiente — `acessar_ambiente()`

Imagens: `bnt_producao_ini.png` **ou** `bnt_homo_ini.png` (conforme
`AGI_AMBIENTE`), e `card_agi.png`.

- [ ] A tela do ambiente escolhido abriu, com o título certo.
- **Se falhar:** recapture. As três foram recapturadas nesta máquina em
      2026-08-06 e casam em **0.95**; o passo 0 mede isso sozinho.

> ✅ **As três imagens do portal foram refeitas em 2026-08-06.** As antigas,
> vindas da máquina de Receita, não casavam **nem em `confidence=0.6`** — não era
> margem, era botão de outro tamanho. Recapturar não dependeu de acesso ao AGI:
> estas telas são HTML local.
>
> Três coisas mudaram junto, e nenhuma é cosmética:
>
> **1. O cursor é afastado antes de cada busca.** O CSS do portal tem
> `.homo:hover { background: roxo; color: branco }` — o botão sob o mouse fica
> com a aparência invertida em relação à imagem. E a automação **deixa o cursor
> onde clicou**. Com o `PRODUÇÃO` assim escondido, a busca por ele casou no
> `HOMOLOGAÇÃO`: **o robô abriu o ambiente errado**. Na direção contrária, o
> estrago é maior.
>
> **2. O botão do ambiente exige `confidence=0.9`**, não o 0.8 padrão. Os dois
> botões são a mesma moldura, do mesmo tamanho, e diferem só na palavra. Cada um
> casa no seu com 0.99; o errado só entra em 0.8 ou menos. E, por garantia,
> `acessar_ambiente()` agora **confere o título da janela** e aborta se entrou no
> ambiente errado — antes do ACESSAR, portanto antes de qualquer contato com o
> AGI.
>
> **3. `bnt_acessar_agi.png` virou `card_agi.png`.** Os sete cards da página têm
> o mesmo botão `ACESSAR`, e o vizinho do AGI é o **AGI Garliavo**, que é outro
> sistema. Um recorte do card inteiro casa nos **dois** a partir de 0.95, porque
> a logo é uma fração pequena de uma área quase toda uniforme. Agora a imagem é
> só a **logo** — única em 0.95 —, e o botão é alcançado por deslocamento
> calculado a partir dela, no lugar do `moveRel(0, 75)` cego que descia a partir
> de onde o clique anterior tivesse caído.

> ⚠️ **O título da janela muda ANTES de a página repintar.** O Adobe AIR o lê do
> documento assim que ele carrega. Quem procurar uma imagem nesse intervalo mede
> a tela **anterior** — foi o que fez o card do AGI parecer vazio numa primeira
> medição. O robô não sofre com isso (o `_wait_appear` insiste por até 180s), mas
> **quem for recapturar à mão precisa esperar a pintura terminar**.

### 3. Login — `login()`

Imagens: `windows_login.png`, `bnt_user.png`, `bnt_entrar.png`.

- [ ] Entrou.
- ⚠️ O campo de senha é preenchido por **deslocamento relativo**
      (`moveRel(175, 50)` a partir do canto da janela de login), não por imagem.
      Resolução diferente desloca o clique e a senha vai para o campo errado, ou
      para lugar nenhum. **É o passo mais frágil do fluxo.**
- **Se falhar:** confira antes se a credencial está no ambiente — `login()`
      levanta `AGIError` explícito quando ela falta, e isso não é problema de
      imagem.

### 4. Relatórios > Detraf > Receitas e Despesas — `baixar_remessa()`

Imagens: `bnt_menu_relatorio.png`, `bnt_submenu_detraf.png`,
`bnt_submenu_receita_despesas.png`.

- [ ] Chegou na tela do relatório.
- Os dois primeiros estão em **laço com `moveRel(0, 70)`** entre eles: o submenu
      só aparece com o mouse sobre o item. Se o menu piscar sem abrir, o
      deslocamento não bate com a altura do item nesta resolução.

### 5. Filtro de período

Imagens: `bnt_filtro.png`, `bnt_periodo_referencia.png`.

- [ ] O período selecionado é o **mês de referência correto**.
- ⚠️ `_selecionar_periodo()` navega **só por teclado** (`down`, `tab`,
      `Shift+TAB`, `SPACE`) — não há imagem que confirme o resultado. Uma versão
      do AGI com um campo a mais no formulário seleciona **outro período em
      silêncio**. **Confira na tela antes de exportar.**

### 6. Exportar para CSV

Imagens: `drop_box_export.png`, `submenu_export_para_csv.png`.

- [ ] O diálogo de salvar apareceu.

### 7. Diálogo de salvar — `janela_salvar()`

- [ ] O arquivo foi salvo no caminho pedido.
- O título é casado por **regex bilíngue** (`Select location for download by|
      Selecionar local para download de`) + `AGI_JANELA_HOST` — correção que veio
      do Projeto 6, de quem rodou em produção. Se der timeout, compare o título
      real da janela com o que a regex espera.

### 8. Correção de aspas — `_corrigir_aspas_impares()`

- [ ] O CSV foi reescrito sem erro.
- Tem `chmod` + **retry 5×** para `PermissionError`: logo após o download, o
      antivírus ou o processo que salvou ainda seguram o arquivo. Se falhar
      mesmo com retry, é permissão de pasta, não transitório.

### 9. A conferência (HU-20) — `verificacao_relatorio.py`

- [ ] A soma por operadora bateu com o Encontro de Contas dentro de
      `TOLERANCIA_VERIFICACAO` (0,01 — decisão nossa, N11).
- [ ] A planilha de inconsistências saiu em `DIRETORIO_INCONSISTENCIAS`.
- ⚠️ Divergência aqui **não é falha de automação** — é o que a HU existe para
      encontrar. Compare com o AGI na tela antes de tratar como defeito.

---

## Quando o `locateOnScreen` falha

`_click` tenta **3 vezes** com `confidence=0.8` e `_wait_appear` espera até 180s.
Se estourar, o log diz qual arquivo `.png` não foi encontrado. Então:

1. **Tire um print da tela no momento da falha** e compare com o `.png`. Na maior
   parte dos casos a diferença é óbvia (tema, escala, botão que mudou de lugar).
2. **Recapture na própria VM**, recortando exatamente o mesmo elemento, e
   substitua o arquivo. O nome tem de continuar o mesmo — o módulo os referencia
   por nome.
3. **Não baixe o `confidence`** para fazer passar. Confiança baixa casa o botão
   errado, e o robô clica em outra coisa em produção.
4. Se um elemento **não tem** imagem estável, é caso de `pywinauto` por
   identificador de controle — não de imagem mais frouxa.

Toda imagem recapturada é uma alteração de código: entra em commit, com a nota de
que foi recapturada na VM de Despesa e em que resolução.

---

## Ordem para ligar os outros dois switches

Só depois de **os passos 1 a 9 passarem duas execuções seguidas**.

1. **`PERMITIR_UPLOAD_AGI=true` com uma operadora só.**
   Use o parâmetro `operadoras=["<uma>"]` do `gerar_artefatos`. Exercita
   `Detraf > Importar Dados` e `Contestação > Gerenciar` (imagens de
   `AGI_Upload_Detraf/` e `AGI_Upload_Contestacao/`).
   - [ ] Confira no AGI que a carga entrou e que `carga_agi` virou `"carregado"`.
   - [ ] Confira a evidência em `DIRETORIO_EVIDENCIAS`.
   - ⚠️ **Esta é a primeira escrita real em produção.** Combine antes com o
     GP-Vivo qual operadora e qual mês.

2. **`PERMITIR_UPLOAD_AGI=true` para o lote inteiro**, depois que uma operadora
   tiver passado.

3. **`PERMITIR_ENVIO_EMAIL=true`, por último.**
   ⚠️ Depende também de `CAMINHO_CONTATOS_OPERADORAS` estar preenchido (a ponte
   da Q16). Com os dois, **o e-mail sai para a operadora** — é o único efeito
   deste repositório que chega a alguém de fora da Vivo, e não tem desfazer.
   - [ ] Valide primeiro com o arquivo de contatos apontando para um endereço
     **interno**, e só depois com os contatos reais.

---

## O que este roteiro **não** cobre

- **A HU-21 / RPA 4.** Não veio código (pendência N12). `Contestação > Gerenciar`
  é exercitado pela HU-18, mas a tela de retificação nunca foi tocada.
- **Falha no meio da carga.** O que fazer quando parte do lote subiu e parte não
  é pergunta em aberto — a V2 ¶705 pergunta a mesma coisa e não responde.
- **Concorrência com um operador humano no AGI.** O robô assume a tela inteira.
