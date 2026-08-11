# Relatório — Unificação dos Projetos 5 e 7

**Data:** 2026-08-04 · **Escopo:** P5 (HU-15) e P7 (Épico 5 — HU-17/HU-18) → RPA 3

---

## O que era diferente nesta rodada

Os Projetos 1 a 4 vinham do mesmo esqueleto: unificá-los foi, em boa parte,
escolher entre versões de um mesmo código. **P5 e P7 não vêm dali.** Foram
montados a partir do `RPA_DETRAF_RECEITA` (MVP1 de Receita), com outra
configuração, outra camada de banco, outra convenção de nomes e — inédito no
repositório — automação de interface por comparação de imagem.

| | P1–P4 (unificado) | P5 / P7 |
|---|---|---|
| Configuração | `configuration.py` | `config.py` |
| Banco | SQLAlchemy + repositórios | `conexao.py`, mysql-connector, SQL cru |
| Log | `loguru` | `print()` |
| Pastas | `services/` minúsculo | `services/AGI/`, `services/Outlook/` |
| Interface | — | 27 PNGs, `pyautogui` + `pywinauto` |

---

## O resultado

### A camada de Outlook subiu para `comum/`

Era o único candidato **ADIADO** do catálogo, esperando desde a primeira
unificação exatamente o P5 como teste de confirmação. A hipótese se sustentou —
e o P5 mostrou por que o adiamento estava certo: **cada lado tinha metade da
abstração.**

O `outlook_standalone_original.py` do P5 são 1.191 linhas replicando o Projeto 1
inteiro. Mas as duas cópias divergiram: o P5 ganhou `send_email`, e o P1 ganhou a
navegação por **pasta nomeada** — que é o que a V2 exige, enquanto o P5 continuou
inbox-cêntrico.

`comum/integracoes/outlook.py` = base do P1 + os dois métodos de envio do P5. As
1.191 linhas não foram migradas. Três consumidores em três RPAs:

| RPA | Uso |
|---|---|
| 1 | lê a caixa, move e-mails, baixa anexos |
| 2 | responde à operadora quando o Detraf é inválido |
| 3 | envia a contestação com carta e `_ENV` (HU-15) |

O `win32com.client.Dispatch` inline que o RPA 2 tinha virou
`OutlookService.responder_email`. **Não existe mais nenhum `Dispatch` fora da
camada comum.**

### Três HUs saíram do zero

| HU | Antes | Agora |
|---|---|---|
| HU-15 | projeto não entregue | ⚠️ parcial — `services/envio_email_contestacao.py` |
| HU-17 | não implementada | ⚠️ parcial — `services/upload_detraf_agi.py` |
| HU-18 | não implementada | ⚠️ parcial — `services/upload_contestacao_agi.py` |

### Q3 resolvida

A pendência "onde está o código do Épico 5" estava aberta desde a etapa
documental, com três hipóteses. Era a segunda: **existe um sétimo projeto.** A
primeira (estar no P4) já tinha sido eliminada na leitura do P4.

---

## O defeito que apareceu três vezes de novo

Os três serviços novos varriam uma **pasta plana**, filtrando por substring do
nome do arquivo. A estrutura real é `{operadora}/{ano}/{aaaamm}/{subpasta}/`, e
`comum/arquivos/estrutura_pastas.py` já a conhece — foi o mesmo desvio já
encontrado entre RPA 1 e RPA 2 na rodada anterior (D-22).

Não é só uma questão de achar o arquivo: **a pasta plana perde a operadora**. E a
operadora é justamente a chave da regra de negócio que falta na HU-17.

---

## O que continua faltando

### Bloqueado no cliente

- **HU-15, destinatários (Q16).** A V2 cita "a tabela de contatos do WebFat" sem
  dar nome de tabela nem de coluna. Nenhum dos sete projetos chegou a consultá-la.
  Sem isso, `buscar_destinatarios` devolve lista vazia e o envio é recusado — de
  propósito: melhor não enviar do que enviar para lugar nenhum.
- **HU-15, controle de reenvio.** O *gatilho* já existe e já é legível
  (`tipo_contestacao`, via `obter_tipo_contestacao`) — o TODO do P5 que dizia o
  contrário estava desatualizado. O que falta é a coluna que marca "e-mail já
  enviado": sem ela, uma segunda execução reenviaria tudo.

### Desenvolvimento, fora do escopo desta rodada

- ~~**HU-17, regra de cenário.**~~ **Reenquadrado (2026-08-04):** a V2 diz que o
  `_INT` *"não chegou nem a ser criado"* nos cenários sem retenção — quem decide é
  a **HU-13**, e a carga sobe o que existe. Restava só a guarda contra sobra de
  execução anterior, implementada.
- ~~**Orquestração do RPA 3.** Continua stub~~ — **ligada em 2026-08-04**, ver
  `relatorio-fechamento-pendencias-codigo.md`.

### Validação em ambiente

- As imagens de `AGI_CONFIG/` e `AGI_Upload_Detraf/` vieram da VM de **Receita** e
  nunca foram conferidas na de Despesa. O mesmo vale para `REGION`, a área da
  grade na tela, e para a detecção de erro por linha vermelha.
- O título do diálogo nativo de upload na tela "Contestação > Gerenciar" é um
  palpite: está o mesmo da HU-17.
- Nada disso é testável sem a máquina — **não há ambiente de teste do AGI (Q20)**.
  É por isso que `PERMITIR_UPLOAD_AGI` importa tanto.

---

## Desvio consciente do plano

O plano listava a **evidência de sucesso por screenshot** como
desenvolvimento fora do escopo. Ela foi implementada: era um `print("[TODO]")`
depois de criar a pasta de destino, e completá-la é uma linha
(`pyautogui.screenshot().save(...)`). Deixar uma função que cria uma pasta vazia e
não grava nada seria pior do que terminá-la.

Ela nunca derruba o upload: se `DIRETORIO_EVIDENCIAS` não estiver configurado ou a
captura falhar, registra aviso e segue — o upload já aconteceu e não se desfaz.

---

## 🔴 Credencial do AGI exposta

`projetos-origem/projeto-7-epico-5-carga-agi/.env` traz
`RPA_DETRAF_DESPESA_AGI_USER` (8 caracteres) e `RPA_DETRAF_DESPESA_AGI_PASSWORD`
(28 caracteres) **preenchidos**.

Não é vazamento de repositório — `/projetos-origem` está no `.gitignore` —, mas é
credencial de acesso ao AGI num arquivo que circulou fora do controle de versão.
**Vale avaliar rotação com quem administra o acesso.**

O código unificado não herda o padrão: a credencial vem de variável de ambiente da
máquina, e o `.env.example` diz explicitamente que ela não entra ali.

---

## Verificação

| Critério | Resultado |
|---|---|
| `python executar_testes.py` | ✅ 345 testes, todos verdes (eram 299) |
| `win32com.client.Dispatch` fora de `comum/integracoes/outlook.py` | ✅ nenhum |
| `mysql.connector` em `unificado/` | ✅ nenhum |
| `conexao.py` ou `outlook_standalone*` em `unificado/` | ✅ nenhum |
| Kill-switches desligados não chegam a `Send()` nem ao AGI | ✅ coberto por teste |
| `projetos-origem/` intocada | ✅ |
| Credencial em código ou `.env.example` | ✅ nenhuma |

**46 testes novos:** 14 na camada comum de Outlook, 15 na HU-15, 17 na HU-17/18.

~~O RPA 2 continua sem suíte própria~~ — **a suíte foi escrita em 2026-08-04**, e
em 2026-08-05 ela achou o defeito que impedia a HU-09/HU-10 de executar.
