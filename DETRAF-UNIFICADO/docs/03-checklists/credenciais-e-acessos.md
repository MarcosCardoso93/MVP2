# Credenciais, acessos e valores de configuração

**Escrito em 2026-08-06** · Para quem vai provisionar o ambiente de homologação
ou de produção.

---

## 🔴 A única coisa que bloqueia hoje: rotação da credencial do AGI

Ela veio **preenchida** nos `.env` dos Projetos 6 e 7, e a comparação por
impressão digital confirmou: **é a mesma credencial nos dois arquivos**.
Circulou fora do controle de versão.

**Autorização para usar o AGI — concedida em 2026-08-06 — não é autorização para
usar esta credencial.** Rotacione, ponha a nova no `unificado/.env`, e só então
rode contra o AGI.

É o risco **R20**. Não é pendência de negócio: é tarefa de segurança com dono
definido.

> ⚠️ **Uma credencial informada em 2026-08-07 não fechou o R20.** O usuário era o
> mesmo, e a senha diferia em **um caractere** — `l` (letra) contra `1` (dígito),
> na posição 14. Mesma senha, transcrita de dois jeitos. Ficou a do `.env`, que
> veio dos `.env` do P6 e do P7 e é a que os robôs originais usaram para logar.
> Detalhe em [riscos-conhecidos.md](../04-relatorios/riscos-conhecidos.md), R20.

> ⚠️ O `.gitignore` **não ignorava `.env`** até 2026-08-06. Nenhum foi commitado
> porque nenhum existia aqui — os de origem estavam em `projetos-origem/`, já
> ignorada. Se alguém criou um `.env` neste repositório antes dessa data,
> **confira o histórico do git**.

---

## De onde vieram os valores

O `unificado/.env` foi consolidado a partir dos `.env` dos sete projetos de
origem, que traziam os valores reais e nunca tinham sido reunidos. O
`.env.example` versionado **não tem valor nenhum preenchido** — ele é a
documentação das variáveis.

---

# 🔑 Segredos

| O quê | Variável | Quem fornece | Estado |
|---|---|---|---|
| Usuário e senha do MySQL | `USUARIO_BD` · `SENHA_BD` | DBA / infra Vivo | ✅ nos `.env` do P2/P3 |
| Credencial do AGI | `RPA_DETRAF_DESPESA_AGI_USER` · `..._PASSWORD` | Infra Vivo | ⚠️ existe, **pendente de rotação** |

O Outlook **não tem senha**: usa o perfil da sessão do Windows. O que precisa
existir é o **Outlook Desktop Classic** instalado, aberto e com perfil — o "Novo
Outlook" do Windows 11 não expõe COM. **Os três robôs precisam dele**: o RPA 1
lê a caixa, o RPA 2 manda a crítica, e o RPA 3 manda o e-mail de contestação.

---

# 📍 Endereços de sistema

| O quê | Variável | Valor conhecido | Quem confirma |
|---|---|---|---|
| Banco | `HOST_BD_RPA` · `PORT_BD_RPA` · `DATABASE_RPA` | ✅ `10.124.66.77` / `webfat` — **verificado** | ✅ |
| Caixa do processo | `OUTLOOK_ACCOUNT` | `detrafTBRA.br@telefonica.com` (P1) | ✅ |
| Executável do AGI | `DIRETORIO_AGI` | `aplicacao_agi/Portal AIR/portal_air_vivo.exe`, relativo a `unificado/` (na VM do P6/P7 era `C:\RPA\Dtraf\aplicacao_agi\...`) | ✅ |
| Ambiente do AGI | `AGI_AMBIENTE` | `producao` ou `homologacao` | ✅ |
| Host no título do diálogo — **produção** | `AGI_JANELA_HOST_PRODUCAO` | `10.238.6.120` (P6/P7, e o que o portal aponta) | ✅ |
| Host no título do diálogo — **homologação** | `AGI_JANELA_HOST_HOMOLOGACAO` | `10.129.178.159` | ✅ |

## O AGI tem dois ambientes

Descoberto em 2026-08-06, ao instalar o aplicativo em `unificado/aplicacao_agi/`.
O **Portal AIR da Triad** é um menu que abre os sistemas no navegador, e tem uma
página por ambiente:

| Ambiente | AGI | Título da janela do portal |
|---|---|---|
| Produção | `http://10.238.6.120:7010/Agi/` | `Portal Triad: Vivo - Produção` |
| Homologação | `http://10.129.178.159:7010/Agi/` | `Portal Triad: Vivo - Homologação` |

É o host da URL que aparece no título do diálogo nativo de upload
(`Select file for upload by <host>`) — por isso host e ambiente andam juntos, e
por isso o `AGI_JANELA_HOST` passou a ser derivado do `AGI_AMBIENTE` em vez de
configurado à parte.

⚠️ **Isto afeta a pendência Q20** (*"não existe ambiente de teste do AGI"*).
Existe um AGI de homologação. Falta confirmar com a área: (1) se ele tem dado de
Despesa utilizável, e (2) se `RPA_DETRAF_DESPESA_AGI_USER` vale nele.

## Alcance de rede — produção ✅, homologação ❌

Medido em 2026-08-06, com a VPN de pé (adaptador EAA, IP de origem
`10.125.77.78`), depois do ajuste de acesso:

| Host | Porta | O quê | TCP | HTTP |
|---|---|---|---|---|
| `10.124.66.77` · `10.124.66.79` | 3306 | MySQL | ✅ | — |
| `10.238.58.43` | 80 | TVAS de produção | ✅ | — |
| **`10.238.6.120`** | **7010** | **AGI produção** | ✅ | **200 OK** |
| **`10.129.178.159`** | **7010** | **AGI homologação** | ❌ timeout | — |

O acesso é **por aplicação** (o EAA libera por app, não por rede): produção foi
liberada e homologação não. Enquanto ela não for, a Q20b não tem como ser
testada — só respondida pela área.

⚠️ O ICMP continua bloqueado em tudo. **`ping` não serve de teste aqui**; use
`Test-NetConnection -Port`.

## 🔍 O AGI é uma aplicação Adobe **Flex/Flash** — e é por isso que o portal existe

A página do AGI declara, no próprio HTML: *"This application was built using
Adobe Flex […] delivered via the Flash Player or to desktops via Adobe AIR"*,
com `requiredMajorVersion = 10` do Flash.

**O Flash foi removido de todos os navegadores em janeiro de 2021.** Abrir
`http://10.238.6.120:7010/Agi/` no Chrome ou no Edge devolve a página, mas a
aplicação **não roda**.

O que faz funcionar está dentro do próprio pacote: `aplicacao_agi/Portal AIR/
runtime/win/Adobe AIR/Versions/1.0/Resources/` traz o **`NPSWF32.dll`, o Flash
Player, com 18,5 MB**, ao lado do `WebKit.dll`. O Portal AIR carrega o seu
próprio Flash.

Duas consequências práticas:

1. 🔴 **Não valide o acesso abrindo a URL no navegador.** Vai parecer quebrado e
   não prova nada. O teste válido é pelo Portal AIR.
2. Isto explica por que a automação **dirige o aplicativo** em vez de apenas
   abrir uma URL — e por que a pasta `aplicacao_agi/` é insubstituível: sem ela
   não há como executar o AGI nesta máquina.

## ✅ O banco, resolvido em 2026-08-06

**Não era divergência entre os projetos — era topologia.** São dois servidores, e
cada um tem uma base. Verificado conectando de verdade:

| Host | Base | O que tem | Serve a este código? |
|---|---|---|---|
| **`10.124.66.77`** | **`webfat`** | as 5 tabelas do Detraf, mais 8 | ✅ **é esta** |
| `10.124.66.79` | `rpa` | 8 tabelas de receita/log de outros robôs | ❌ não tem `webfat` |
| `10.126.70.170` | — | não responde na 3306 | ❌ |

O que cada origem dizia, e quem acertou:

| Origem | Dizia | Veredito |
|---|---|---|
| P2, P3 | `.79` / `webfat` | ❌ essa base não existe no `.79` |
| P6, P7 | `.79` / `rpa` **e** `.77` / `webfat` (duas conexões) | ✅ **certo** |
| Print do Workbench (`.docx`) | `10.126.70.170` / `webfat` | ❌ host inacessível |

**A decisão registrada aqui até 2026-08-06 estava errada.** Tinha-se adotado o
`.79`/`webfat` do P2/P3 com o argumento de que eram "os projetos que de fato leem
e escrevem as cinco tabelas". O argumento era bom e a conclusão, falsa: os P6/P7
mantinham **duas** conexões justamente porque são dois bancos, e a que interessa
a este código é a `HOST_BD_WEBFAT` deles.

### ⚠️ Duas armadilhas, para quem for reconferir

1. **O `.79` autentica.** A mesma credencial `btime_prod` conecta normalmente e só
   falha ao abrir a base: `Unknown database 'webfat'` (erro 1049). Um teste de
   conectividade ou de login passa nos dois hosts.
2. **Os grants do usuário no `.79` citam `webfat.<as 5 tabelas>` nominalmente.**
   São grants órfãos — o mesmo servidor tem grants para tabelas `mvp2` que
   também não existem lá. **Grant não prova onde o schema está.**

Restam ao DBA só perguntas de semântica, não de endereço — ver
[pendencias-para-o-cliente.md](../04-relatorios/pendencias-para-o-cliente.md) (Q24).

---

# 📂 Permissões de rede — não é senha, é acesso

O `verificar_ambiente.py` testa a permissão de **escrita de verdade**, criando e
apagando um arquivo. `os.access(W_OK)` mente em compartilhamento de rede Windows,
que é justamente onde este repositório grava.

| Pasta | Variável | Precisa | Quem para sem ela |
|---|---|---|---|
| Árvore das operadoras | `CAMINHO_OPERADORAS` | leitura + **escrita** | RPA 1, 2 e 3 |
| Expectativa Vivo | `CAMINHO_EXPECTATIVA_DETRAF` | leitura | RPA 2 |
| **Controle de numeração CT** | `CAMINHO_CONTROLE_CT` | leitura + **escrita** | HU-14 |
| Entrada dos anexos | `DIRETORIO_ENTRADA` | leitura + escrita | RPA 1 |
| Não identificados | `DIRETORIO_NAO_IDENTIFICADOS` | escrita | RPA 1 |
| Histórico | `DIRETORIO_HISTORICO_ARQUIVOS` | escrita | RPA 1 e 2 |
| Logs e derivadas | `RAIZ_LOGS` | escrita | todos |

⚠️ **A pasta CT é a mais sensível.** Ela guarda a sequência **global** de números
de carta. Apontada para o compartilhamento real durante a homologação, **cada
rodada de teste consome números de verdade — e eles não voltam.**

🔴 **Os caminhos de produção não estão documentados em lugar nenhum.** Os `.env`
de origem traziam caminhos de máquina de desenvolvedor
(`C:\Users\...\Desktop\...`) ou da VM (`C:\RPA\Dtraf\...`). Os compartilhamentos
Lagoa reais precisam ser informados pela operação.

---

# 📄 O que falta e **não é credencial** — mas para o robô igual

| O quê | Variável | Falha silenciosa? | Sem ele |
|---|---|---|---|
| Contatos das operadoras | `CAMINHO_CONTATOS_OPERADORAS` | não | HU-15 recusa o envio, com aviso |
| Template do e-mail de crítica | `CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO` | não | HU-04 sem corpo de e-mail |
| **Substrings de arquivo validado** | `ARQUIVOS_VALIDADOS` | 🔴 **SIM** | ver abaixo |

O modelo do CSV de contatos existe em
`unificado/configuracao/contatos-operadoras.csv`, com endereços fictícios.

## 🔴 As listas de filtro: o modo de falha mais traiçoeiro do projeto

Quatro variáveis são lidas assim:

```python
any(sub in nome_arquivo for sub in LISTA)
```

Com a lista **vazia**, `any(...)` é `False` e o filtro **rejeita tudo**. Nenhum
erro, nenhum aviso: a execução termina com **sucesso** tendo processado zero
arquivos, e quem lê o log conclui que não havia nada a fazer.

Foi achado em 2026-08-06 comparando o `.env.example` com os `.env` de origem: o
`ARQUIVOS_VALIDADOS` estava em branco aqui e valia `_ENV` lá.

**Duas delas são opostas e as duas são obrigatórias:**

- a **validação** renomeia o que aprovou acrescentando `_ENV`;
- o **batimento** só lê arquivos que contenham `ARQUIVOS_VALIDADOS`.

| Variável | Valor | Errado, acontece o quê |
|---|---|---|
| `ARQUIVOS_VALIDADOS` | `_ENV` | vazia → o batimento pula **todo** arquivo |
| `IGNORAR_ARQUIVOS` | `_BK,_ERRO,_ENV` | sem `_ENV` → a validação reprocessa o que já validou, e o arquivo vira `X_ENV_ENV.csv` |
| `EXPECTATIVA_SUBSTRING` | `_D_` | vazia → nenhuma expectativa é encontrada |
| `PASTAS_EXPECTATIVAS` | `VIVO,TLF` | vazia → nenhuma pasta é varrida |

O histórico anti-reprocessamento **não protege** o segundo caso: ele indexa pelo
caminho completo, que muda justamente no rename.

**O `verificar_ambiente.py` acusa as quatro desde 2026-08-06.** Rode-o antes.

---

# 👤 Acesso humano

- **WebFat** — o analista precisa conseguir gravar `tipo_contestacao`. Sem esse
  sinal, o RPA 3 gera os artefatos e não contesta nada. **Não é defeito**: é o
  ponto de decisão humana entre o RPA 2 e o RPA 3;
- **AGI de produção** — ✅ autorizado em 2026-08-06.

---

# Ordem de provisionamento

Dá para começar sem nada do AGI:

| # | O que liberar | Destrava |
|---|---|---|
| 1 | Banco + pastas Lagoa | RPA 1 e RPA 2 inteiros |
| 2 | Perfil do Outlook | HU-01 (captura), HU-04 (crítica) e o e-mail de contestação do RPA 3 |
| 3 | Contatos e template de e-mail | HU-15 e HU-04 completas |
| 4 | **Credencial do AGI rotacionada** | RPA 3 — HU-17, HU-18 e HU-20 |

O passo 4 é o único que depende da rotação. Os três primeiros podem correr em
paralelo com ela.

---

## Ver também

- [`homologacao-guia-de-partida.md`](homologacao-guia-de-partida.md) — o perfil
  de homologação isolada, com o `.env` completo
- [`checklist-validacao-agi.md`](checklist-validacao-agi.md) — o procedimento
  contra produção
- [`../04-relatorios/riscos-conhecidos.md`](../04-relatorios/riscos-conhecidos.md) — R20
