# Homologação — RPA 1 e RPA 2

**Escrito em 2026-08-06.** Leia antes o
[guia de partida](homologacao-guia-de-partida.md).

Os dois estão no mesmo documento porque formam um contrato: o RPA 2 lê exatamente
onde o RPA 1 gravou, e o erro mais provável entre eles é os dois apontarem para
lugares diferentes.

---

# RPA 1 — captura, identificação, salvamento

**Cobre:** HU-01 (captura no Outlook), HU-02 (identificação da operadora), HU-03
(salvamento na árvore).

## Pré-condições

- [ ] `python verificar_ambiente.py --rpa rpa1` sem falhas
- [ ] `CAMINHO_OPERADORAS` existe e é **gravável** (o pre-flight testa escrevendo)
- [ ] Para a HU-01: Outlook Desktop **Classic** aberto, com perfil, e
      `OUTLOOK_ACCOUNT` preenchida

> 💡 **Dois terços deste robô rodam sem Outlook.** `--pasta-entrada CAMINHO`
> pula a captura e processa arquivos já em disco. A identificação continua
> correta: ela é pela **EOT credora lida dentro do arquivo**, e o domínio do
> remetente é só fallback.

## Roteiro

### 1. Identificação e salvamento, sem Outlook

```
python rpa1_captura/main.py --pasta-entrada C:\temp\detrafs --referencia 202507
```

| O que conferir | Esperado |
|---|---|
| A operadora foi identificada | log diz `origem="eot"` |
| Onde o arquivo foi parar | `{CAMINHO_OPERADORAS}\{OPERADORA}\2025\202507\Detrafs Recebidos\` |
| O conteúdo | **byte a byte igual** ao original — a captura não transforma nada |
| Estrutura do mês | as quatro subpastas criadas (AGI, Contestações, Detrafs Recebidos, Detrafs Enviados) |

**Como falha:** operadora não identificada vai para `DIRETORIO_NAO_IDENTIFICADOS`,
com o EOT lido e o domínio no log. Se a EOT não está no Anexo 5, é a **Q16b** —
pergunta aberta, não defeito.

### 2. Captura por e-mail

```
python rpa1_captura/main.py --referencia 202507
```

| O que conferir | Esperado |
|---|---|
| Data de corte | antes do dia 5 o robô não processa (`DETRAF_DIA_LIBERACAO`) |
| E-mail capturado | move para a subpasta `PROCESSADOS` — é o que evita recapturar |
| Rastreamento | `_rastreamento.json` liga cada arquivo ao e-mail de origem |

⚠️ O `_rastreamento.json` é o **acoplamento real entre RPA 1 e RPA 2**, e não está
descrito na especificação. Se o RPA 2 não o encontrar, ele registra "nenhum e-mail
de origem encontrado" por arquivo e **nenhuma operadora é notificada** — sem erro
visível. Os dois robôs precisam apontar para o mesmo arquivo.

---

# RPA 2 — validação e batimento

**Cobre:** HU-04 a HU-11. Termina num **ponto de decisão humana**: o analista
escolhe no WebFat o que contestar.

## Pré-condições

- [ ] O RPA 1 já rodou para o mês, ou os arquivos já estão na árvore
- [ ] `CAMINHO_EXPECTATIVA_DETRAF` aponta para a raiz da expectativa Vivo
- [ ] `PASTAS_EXPECTATIVAS` lista as pastas a varrer

## Roteiro

### 1. Só a validação

```
python rpa2_validacao_apuracao/main.py --etapa validacao --referencia 202507 --dry-run
```

| O que conferir | Esperado |
|---|---|
| Layout | arquivo fora do padrão é recusado, e sai um `*_RECUSADO.md` **ao lado dele** |
| `_BK` e `_ERRO` | gerados por arquivo processado |
| Registro no banco | uma linha por arquivo em `tbl_rpa_log_detraf_despesa_arquivos` |

**O `*_RECUSADO.md` é o entregável desta etapa.** Ele traz posição, campo,
esperado, encontrado e duas linhas do arquivo — o suficiente para decidir se o
errado é o arquivo ou o código, sem abrir mais nada.

🔴 **A expectativa Vivo atual vai ser recusada.** É a pendência **N3**: a
especificação exige a coluna `R$ Bruto` (¶443) e manda o layout valer para os dois
tipos de arquivo (¶149), mas o arquivo real termina em `VALOR_LIQUIDO`. É
contradição entre documento e realidade, **não defeito** — e a rejeição é decisão
tomada: falhar alto é melhor que comparar coluna errada em silêncio.

### 2. Só o batimento

```
python rpa2_validacao_apuracao/main.py --etapa batimento --referencia 202507 --dry-run
```

| O que conferir | Esperado |
|---|---|
| Sumarização | por EOT × remuneração × mês de tráfego |
| Regra de variação | contesta quando a variação é **`>= 1%`** e a operadora cobrou **a mais** |
| Tabela de contestação | uma linha por combinação, com `carga_agi = "não carregado"` |

⚠️ O batimento **lê o que a validação registrou**. Rodá-lo sozinho num mês em que
a validação não rodou dá resultado vazio, e isso não é defeito — o robô avisa.

### 3. Os dois, como na agenda

```
python rpa2_validacao_apuracao/main.py --referencia 202507 --dry-run
```

---

## Os três avisos que mais aparecem, e o que significam

### `[Q21] Sem expectativa Vivo em [...]`

**Grave.** Sem expectativa não há com o que comparar: a variação sai como 100% e
**a operadora inteira é contestada indevidamente** — o que chega ao cliente como
carta assinada.

Não aborta de propósito: uma pasta vazia pode ser legítima (operadora sem tráfego
no mês). Mas **confira antes de considerar a apuração do mês concluída**.

### `... valor(es) não puderam ser convertidos para número e viraram ZERO`

O arquivo tem valores com **separador de milhar** (`1.234,56`). A especificação
não define separador para estes campos, então o código não pode simplesmente
removê-lo — uma planilha que use ponto como decimal viraria o erro simétrico,
silencioso do mesmo jeito.

**Um valor zerado aqui vira diferença inventada na contestação.** Confira o
arquivo antes de aceitar a apuração.

### `Chave sem linha correspondente no banco`

A linha-base é inserida pelo Épico 3, **fora do escopo deste projeto** (bloqueio
B-D20). É esperado quando o RPA 3 roda isolado. Não é defeito deste robô.

---

## Repetir um cenário

```
python resetar_homologacao.py --referencia 202507
```

Sem isto, a segunda execução do mesmo mês não processa nada — e parece defeito.
