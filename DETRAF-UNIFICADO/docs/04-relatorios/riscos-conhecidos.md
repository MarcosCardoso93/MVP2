# Riscos Conhecidos

Duas famílias: os que a **documentação declara** (riscos do produto) e os que a **unificação introduz ou herda** (riscos do projeto).

Cada risco traz probabilidade, impacto, quando se manifesta e como mitigar.

---

## Status — revisado em 2026-08-04

Este arquivo foi escrito na etapa documental e **não era atualizado desde então**.
Vários riscos já se materializaram ou foram mitigados, e continuavam descritos
como hipótese. A tabela abaixo é a fonte do status; o corpo do documento mantém a
análise original de cada um.

| # | Risco | Status hoje |
|---|---|---|
| **R1** | Dupla tarifa em fevereiro | 🟢 **mitigado** — `repositorio_tabelas.validar_tarifas_na_tabela` considera o mês de tráfego e trata 28/02 explicitamente |
| **R4** | Código implementando a V1 | 🔴 **confirmado**, não é mais probabilidade: a HU-02 tinha fallback por domínio e a HU-09 gravava planilha **e** banco (esta última corrigida em 2026-08-04) |
| **R5** | Sem ambiente de teste | 🔴 **impedimento confirmado** — a Q20 foi respondida: **não existe**. Deixou de ser "probabilidade desconhecida" |
| **R6** | Épico 5 não implementado | 🟢 **fechado** — chegou como Projeto 7 e foi migrado |
| **R8** | Cisão do Projeto 6 | 🔴 **materializou-se pela metade (2026-08-05)** — o P6 chegou **só com a HU-20**. A cisão não aconteceu: a HU-21 e o RPA 4 continuam sem código |
| **R9** | Convergência de quatro origens no RPA 3 | 🟢 **concluído (2026-08-05)** — P4, P5, P7 e a HU-20 do P6 convergiram sem conflito estrutural |
| **R11** | Compartilhar regra em pendência aberta | ⚠️ **realizou-se de forma consciente**: `variacao.py` foi promovida com a Q2 residual em aberto |
| **R13** | Numeração CT sem trava | 🟢 **fechado (2026-08-05)** — trava por arquivo (`O_CREAT|O_EXCL`) cobrindo o par ler→gravar. Virou pré-requisito quando a Q25 fez a mesma execução consumir dois números seguidos |
| **R18** | WebFat de outra frente | 🟢 **fechado** — a Q19 foi respondida: a decisão do analista vem de coluna no banco |
| **R21** | Validação posicional × deslocamento de colunas | 🟢 **fechado (2026-08-06)** — o layout completo chegou (Q6) e **as 15 primeiras colunas não se mexem**: CBS e IBS entram depois do `R$_Bruto`. O deslocamento que se temia não acontece |
| **R20** | Credenciais expostas | 🔴 **ampliado (2026-08-05)** — além dos dois `.env`, os prints embutidos no `.docx` expõem host e schema do banco, endereços de rede internos, matrícula e e-mails de contato (achado A3) |
| demais | — | sem alteração desde a etapa documental |

---

# Parte 1 — Riscos declarados pela V2

## R1 — Dupla convivência de tarifas em fevereiro

**Fonte.** V2, item 7: *"As tarifas reguladas são alteradas anualmente em fevereiro, fazendo com que duas tarifas sejam válidas durante todo o tempo que exista mês de tráfego igual ao mês da alteração."*

**Mecânica.** O Detraf é consolidado até 24/02, mas há tráfego entre 25/02 e o encaminhamento de fevereiro. O reajuste cai nessa janela.

**Alcance maior do que parece.** Como a coluna Tráfego aceita até **mês −3**, uma tarifa de fevereiro pode continuar válida nos Detrafs de março, abril e maio. Não é um problema de um mês — é de quatro.

**Probabilidade.** Certa, todo ano.
**Impacto.** Alto — validação de tarifa incorreta gera contestação indevida ou deixa de gerar contestação devida.

**Mitigação.** `tbl_detraf_tarifas` tem `data_inicio`/`data_fim`; a consulta deve considerar o **mês do tráfego**, não a data de execução. ⚠️ Verificar na análise se os projetos implementam isso — é o tipo de regra que se esquece em código escrito fora de fevereiro.

---

## R2 — Novo imposto em 2028 deslocando colunas

**Fonte.** V2, item 7: *"Existe a projeção para que em 2028 mais um imposto seja inserido na tabela deslocando as colunas."*

**Probabilidade.** Declarada como projeção.
**Impacto.** Alto — se a leitura dos arquivos for por posição fixa, todo o parsing quebra.

**Mitigação.** É requisito, não sugestão: o layout dos arquivos precisa ser **configurável**. Junto com o CBS/IBS (que já está chegando), isso significa que a leitura por índice fixo de coluna é dívida técnica desde já.

⚠️ Item obrigatório do checklist de análise: procurar índices de coluna constantes no código.

---

## R3 — "Os ajustes nos arquivos são dinâmicos"

**Fonte.** V2: *"A solução não poderá ficar condicionada a regras de negócio que podem ser alteradas a qualquer momento."*
Reforçado pelas premissas 10.3 e 10.4: regras e tabelas de consulta devem ser **editáveis e gerenciáveis pelo usuário**.

**Probabilidade.** Alta — é a natureza do domínio regulatório.
**Impacto.** Alto e recorrente — cada mudança regulatória vira alteração de código se as regras estiverem embutidas.

**Mitigação.** Nenhuma tarifa, mapeamento descritor→remuneração, limiar (1%, 0,9635) ou EOT constante no código. Tudo vem de tabela editável.

⚠️ Se os projetos de origem violarem isso, é dívida a registrar — mas **não se corrige durante a migração**, sob pena de misturar mudança de comportamento com mudança de estrutura.

---

# Parte 2 — Riscos da unificação

## R4 — Código implementando a V1 nas HUs 🔴

**Descrição.** Cinco HUs mudaram estruturalmente entre V1 e V2. Código escrito antes da V2 implementa regra revogada.

| HU | V1 (revogada) | V2 (vigente) |
|---|---|---|
| HU-02 | domínio do remetente | EOT da Credora × Anexo 5 |
| HU-07 | fluxo dedicado L-L | regra geral `_ERRO` |
| HU-09 | planilha `Base_Contestação` | `tbl_..._contestacao` |
| HU-10 | aba `Contest` | banco |
| HU-19 | planilha de Encontro de Contas | campos do banco |

**Probabilidade.** Alta. A V2 é recente e os projetos podem ser anteriores.
**Impacto.** Alto — migrar código V1 carrega regra revogada para o repositório novo; reescrever é esforço não previsto.

**Manifesta-se em.** M2 (descoberta), M5/M6/M8 (custo).

**Mitigação.** Verificação obrigatória da versão da regra no [checklist de análise](../03-checklists/checklist-analise-de-codigo.md), seção 3. Redimensionar o esforço após M2.

---

## R5 — Ausência de ambiente de teste do AGI e de e-mail

**Descrição.** Os RPAs 3 e 4 executam ações **irreversíveis e externas**: enviam contestações formais a operadoras, lançam valores no sistema financeiro e registram eventos de recuperação.

**Probabilidade.** ⚠️ Desconhecida — precisa ser levantada em M1 (pergunta Q20).
**Impacto.** **Impedimento.** Sem ambiente isolado, a equivalência funcional dos RPAs 3 e 4 não pode ser comprovada sem tocar produção.

**Manifesta-se em.** M7 e M8.

**Mitigação.** Levantar em M1, não na validação. Se não existir, escalar como impedimento formal — não como atraso.

---

## R6 — Épico 5 não implementado

**Descrição.** Se HU-17/HU-18 não estiverem em nenhum projeto, o RPA 3 fica sem a etapa de carga no AGI.

**Probabilidade.** Média — é uma das três hipóteses.
**Impacto.** Alto — transforma parte de M8 de migração em desenvolvimento, com estimativa própria.

**Manifesta-se em.** M1 (descoberta), M8 (custo).

**Mitigação.** Verificação específica ao receber o P4 (checklist de inserção, §7.1). Escalar imediatamente se confirmado.

---

## R7 — Fronteira real dos projetos difere da informada

**Descrição.** O mapa desta etapa descreve onde o código *deveria* estar. Na prática, o P2 pode conter código do Épico 3, o P4 pode conter o Épico 5, ou pode haver código do fluxo de **Receita** (escopo de outras demandas) misturado.

**Probabilidade.** Média-alta. É comum.
**Impacto.** Médio — o mapa se ajusta, mas o planejamento de M3 em diante muda.

**Manifesta-se em.** M2.

**Mitigação.** Mapear código → HU nos dois sentidos: toda HU tem código, e todo código tem HU. Código sem HU é o achado.

---

## R8 — Cisão do Projeto 6

**Descrição.** O P6 contém HU-20 (RPA 3) e HU-21 (RPA 4). É o único projeto que precisa ser dividido, e a separação pode não ser limpa.

**Probabilidade.** Certa — a menos que a HU-20 saia do escopo (Q7).
**Impacto.** Médio.

**Manifesta-se em.** M7.

**Mitigação.** Responder Q7 **antes** de planejar M7. Se a HU-20 for descartada, não há cisão. Se ambas compartilharem a camada de automação do AGI, essa camada é candidata natural à base comum.

---

## R9 — Convergência de quatro origens no RPA 3

**Descrição.** O RPA 3 recebe P4 + P5 + P6(HU-20) + P7?. Quatro bases de código, provavelmente com convenções, configurações e camadas de acesso diferentes, viram um `main.py` coerente.

**Probabilidade.** Certa.
**Impacto.** Alto — é o maior e mais fragmentado dos quatro RPAs.

**Manifesta-se em.** M8.

**Mitigação.** Migrar o RPA 3 **por último**, com a base comum já provada por três consumidores. Prever ciclos de correção da base comum durante M8.

---

## R10 — Abstração prematura na base comum

**Descrição.** Promover componentes por antecipação ("isso claramente vai ser reutilizado") em vez de por evidência de duas ocorrências reais.

**Probabilidade.** Alta — é o erro mais comum em unificações.
**Impacto.** Alto e difícil de reverter: acopla quatro robôs que deveriam ser independentes, e cada mudança na base comum passa a exigir revalidar tudo.

**Manifesta-se em.** M4, com consequências em M5–M8.

**Mitigação.** Critério C1 dos [critérios de compartilhamento](../02-planejamento/criterios-de-compartilhamento.md): duas ocorrências reais, com arquivo e linha. Sem exceção. Promover depois é barato — o código já foi lido.

---

## R11 — Compartilhar regra em pendência aberta

**Descrição.** Promover à base comum um componente cuja regra ainda não foi decidida (borda de 1%, data de corte, CBS/IBS, envio automático).

**Probabilidade.** Média.
**Impacto.** Alto — quando a regra fechar, a mudança na base comum obriga a revalidar os quatro RPAs.

**Manifesta-se em.** M4, com custo em M9 ou depois.

**Mitigação.** Critério C3. Regra aberta fica no RPA que a usa, registrada como **compartilhamento adiado** — promoção automática quando a pendência fechar.

---

## R12 — Passos irreversíveis sem ponto de retomada

**Descrição.** O RPA 3 encadeia passos irreversíveis (numeração CT, envio de e-mail, carga no AGI) com passos reexecutáveis. Se a carga falhar depois do envio da carta, reprocessar do início reenviaria a contestação à operadora.

**Fonte.** Levantado pelo próprio relatório de separação: *"Caso a carga no AGI se mostre historicamente instável, vale considerar isolá-la em uma etapa própria dentro do mesmo RPA, para permitir reprocessamento sem repetir o envio da carta."*

**Probabilidade.** Média-alta — automação de UI é instável por natureza.
**Impacto.** Alto — reenvio de contestação a operadora tem consequência comercial; duplicação de lançamento no AGI tem consequência financeira.

**Manifesta-se em.** M8 e em produção.

**Mitigação.** Definir pontos de retomada em F4. Marcar explicitamente no código todo passo irreversível.

---

## R13 — Numeração CT concorrente

**Descrição.** O contador de cartas é estado compartilhado em pasta de rede, lido e incrementado sem transação. Duas execuções simultâneas — ou o robô junto com um humano — podem gerar cartas com o mesmo número.

**Probabilidade.** Baixa-média, dependendo da granularidade de execução.
**Impacto.** Médio — numeração duplicada em documento formal enviado a terceiros é problema de controle documental.

**Mitigação — implementada em 2026-08-05 (Q18).** `geracao_env_carta.travar_numeracao`
trava a pasta de controle com `O_CREAT|O_EXCL` — atômico no Windows e no POSIX, e o
único mecanismo que funciona sobre compartilhamento de rede, que é o caso aqui.

**A seção crítica é o par**, não cada metade: o número sai do maior encontrado na
pasta e só passa a existir ali quando a carta é gravada. Travar só a leitura não
resolveria nada.

A trava é liberada mesmo em erro. Se o processo morrer sem liberar, a próxima
execução espera o timeout (60s) e **segue com aviso alto** — travar o mês inteiro
por causa de um `.lock` órfão seria pior do que o risco evitado.

⚠️ **Ficou obrigatória com a Q25:** a operadora com cenário misto recebe duas
cartas, e a **mesma execução** consome dois números seguidos da sequência global.

Resta da mitigação original: **isolar o contador durante os testes em produção** —
parte do que se pede ao GP-Vivo na Q20.

---

## R14 — Concorrência de recursos entre RPAs

**Descrição.** A V2 diz que "o robô irá atuar com a memória da máquina local". Se os quatro RPAs rodarem na mesma máquina, disputam Outlook, sessão do AGI e pastas de rede. O Outlook e a automação de UI do AGI, em particular, não toleram bem dois processos simultâneos.

**Probabilidade.** Média.
**Impacto.** Médio-alto — falhas intermitentes e difíceis de reproduzir.

**Manifesta-se em.** M9 e em produção.

**Mitigação.** Mapear a granularidade de execução e a presença de travas na análise (M2). Decidir a política de execução em F4.

---

## R15 — Volume: 1.600 arquivos/mês

**Descrição.** A V2 declara ~1.600 arquivos de Detraf de despesa por mês. Se algum projeto acumula tudo em memória num único passe, pode não escalar — e impede processar uma operadora isoladamente, o que é necessário para reprocessamento.

**Probabilidade.** ⚠️ Desconhecida — o tamanho dos arquivos não está documentado.
**Impacto.** Médio.

**Manifesta-se em.** M2 (descoberta), produção (efeito).

**Mitigação.** Registrar a granularidade de execução de cada projeto na análise.

---

## R16 — Dependências externas não versionadas

**Descrição.** O processo depende de artefatos que vivem fora do repositório e mudam sem aviso:

| Dependência | Risco |
|---|---|
| Modelos de carta por operadora | Operadora nova sem modelo → falha não tratada |
| `CONT_PROC_MASCARA Geral {aaaamm}` | Nome contém ano-mês; atualização não documentada |
| Arquivos-modelo `_EXT`/`_INT` na pasta AGI | A V2 diz que o robô "abre" o arquivo, como se já existisse |
| Anexo 5 (ABR Telecom) | Fonte externa; nomes de operadora mudam (ver R17) |
| `DE_EBT_..._MODELO.xlsx` | Papel desconhecido |

**Probabilidade.** Alta.
**Impacto.** Médio — falhas em produção por motivo externo ao código.

**Mitigação.** Mapear todas as dependências externas na análise; definir tratamento explícito para ausência de cada uma.

---

## R17 — Nome de operadora muda entre meses

**Descrição.** O filtro do AGI na retificação (HU-21) é por **nome da empresa**. Se o nome mudou no Anexo 5 entre o mês da contestação e o da retificação, o robô não encontra o processo.

**Fonte.** Pendência declarada pela própria V2: *"Pendência Vivo para mapear essa ponta."*

**Probabilidade.** Média.
**Impacto.** Alto para o RPA 4 — a retificação simplesmente não acontece, silenciosamente.

**Mitigação.** Q17. Enquanto não resolvido, o RPA 4 precisa **falhar visivelmente** quando não encontrar o processo, nunca passar batido.

---

## R18 — WebFat como dependência de outra frente

**Descrição.** Se as telas do WebFat forem entrega de outra frente, o gatilho do RPA 3 (decisão do analista) depende de algo fora do controle deste projeto.

**Probabilidade.** ⚠️ Desconhecida (Q19).
**Impacto.** Alto — sem a tela, o RPA 3 não tem gatilho.

**Mitigação.** Q19, em M1.

---

## R19 — Pendências de negócio sem resposta

**Descrição.** Seis pendências bloqueantes e uma de alta prioridade dependem de decisão da área cliente. Sem resposta, partes dos RPAs ficam isoladas e incompletas.

**Probabilidade.** Média-alta — a data de corte já está "em análise" desde a redação da V2.
**Impacto.** Alto — atrasa M5 a M8 parcialmente.

**Mitigação.** Trilha P1 do roadmap: encaminhar em paralelo a M1, não esperar M4. Manter o painel de [`duvidas-pendentes.md`](duvidas-pendentes.md) atualizado.

---

## R20 — Credenciais expostas nos projetos de origem

**Descrição.** Projetos de automação frequentemente carregam credenciais em código ou configuração.

**Probabilidade.** Média.
**Impacto.** Alto — incidente de segurança, não achado técnico.

**Manifesta-se em.** M1.

**Mitigação.** Verificação obrigatória no [checklist de inserção](../03-checklists/checklist-insercao-dos-codigos.md), §4.1. Se encontrado, **escalar antes de prosseguir** — não commitar no repositório unificado até resolvido.

### O que se confirmou (2026-08-06)

Comparação por impressão digital, sem exibir valor:

- **banco:** `USUARIO_BD` e `SENHA_BD` **idênticos** entre P2 e P3;
- **AGI:** usuário e senha **idênticos** entre P6 e P7.

As credenciais circularam fora do controle de versão. **A rotação da credencial
do AGI continua sendo pré-condição da primeira execução contra ele** — e
autorização para usar o AGI, concedida em 2026-08-06, **não é** autorização para
usar aquela credencial.

### ⚠️ Uma credencial informada em 2026-08-07 NÃO era rotação

Chegou uma credencial do AGI para uso. A comparação mostrou:

| | |
|---|---|
| usuário | **idêntico** ao que já estava no `.env` |
| senha | difere em **um caractere**, na posição 14 |

E o caractere é o par mais clássico de confusão de transcrição: **`l` (letra L
minúscula) contra `1` (dígito um)** — indistinguíveis em fonte sem serifa. Os
outros 27 caracteres são iguais.

Não é rotação: é a mesma senha, transcrita de dois jeitos. **Decisão de
2026-08-07: fica a do `.env`**, que veio byte a byte dos `.env` do P6 e do P7 —
dois arquivos independentes que concordam, e que os robôs originais usaram para
logar de fato.

**O R20 continua aberto.** Registrado aqui para que a coincidência de
comprimento (8 e 28 caracteres nos dois casos) não seja lida no futuro como
"a rotação já foi feita".

---

# Matriz de priorização

| # | Risco | Prob. | Impacto | Quando | Prioridade |
|---|---|---|---|---|---|
| R5 | Sem ambiente de teste | ? | **Impedimento** | M1 | 🔴 1 |
| R20 | Credenciais expostas | Média | Alto | M1 | 🔴 2 |
| R4 | Código implementa a V1 | Alta | Alto | M2 | 🔴 3 |
| R19 | Pendências sem resposta | Média-alta | Alto | contínuo | 🔴 4 |
| R10 | Abstração prematura | Alta | Alto | M4 | 🔴 5 |
| R6 | Épico 5 não implementado | Média | Alto | M1 | 🟡 6 |
| R12 | Passos irreversíveis | Média-alta | Alto | M8 | 🟡 7 |
| R9 | Convergência no RPA 3 | Certa | Alto | M8 | 🟡 8 |
| R1 | Dupla tarifa em fevereiro | Certa | Alto | produção | 🟡 9 |
| R3 | Regras embutidas no código | Alta | Alto | produção | 🟡 10 |
| R11 | Compartilhar regra aberta | Média | Alto | M4 | 🟡 11 |
| R17 | Nome de operadora muda | Média | Alto (RPA 4) | produção | 🟡 12 |
| R18 | WebFat de outra frente | ? | Alto | M1 | 🟡 13 |
| R16 | Dependências não versionadas | Alta | Médio | produção | 🟡 14 |
| R7 | Fronteira real difere | Média-alta | Médio | M2 | 🟢 15 |
| R14 | Concorrência de recursos | Média | Médio-alto | produção | 🟢 16 |
| R2 | Imposto de 2028 | Projeção | Alto | 2028 | 🟢 17 |
| R8 | Cisão do P6 | Certa | Médio | M7 | 🟢 18 |
| R13 | Numeração CT | Baixa-média | Médio | produção | 🟢 19 |
| R15 | Volume de arquivos | ? | Médio | produção | 🟢 20 |

**Os cinco primeiros se manifestam cedo (M1–M4) e são os que mais alteram o planejamento.** Tratá-los nas primeiras semanas evita retrabalho nas fases caras.


---

## ~~R21~~ — A validação posicional quebra quando o layout mudar

🟢 **FECHADO em 2026-08-06, sem virar defeito.**

O risco foi registrado em 2026-08-05, a partir do item 7 da V2: *"projeção para
que em 2028 mais um imposto seja inserido na tabela **deslocando as colunas**"*.
A leitura era que CBS/IBS entrariam no bloco de impostos e empurrariam o
`R$_Bruto` — e o modo de falha seria o pior possível, porque a leitura posicional
continuaria lendo **um número** e nada acusaria.

**O layout completo chegou com a resposta da Q6, e o deslocamento não acontece:**

```
… 13 PIS_Cofins · 14 ICMS · 15 R$_Bruto · 16 CN_RELACIONAMENTO ·
17 CBS · 18 IBS_Municipal · 19 IBS_Estadual · 20 EOT_Ponta · 21 Corredor
```

As 15 primeiras colunas ficam onde estavam. CBS e IBS entram **depois** do
`R$_Bruto`, e colunas extras à direita já são aceitas de propósito. Toda a
leitura posicional dos índices 0 a 14 continua correta.

**O que ficou do risco:** nada a mitigar. O layout completo está registrado em
`comum/config/constantes.py` (`COL_CBS`, `COL_IBS_MUNICIPAL`, `COL_IBS_ESTADUAL`,
`COL_EOT_PONTA`, `COL_CORREDOR`), sem validação por enquanto — os arquivos reais
de hoje têm outra coisa nessas posições, e validá-las rejeitaria arquivos
corretos.
