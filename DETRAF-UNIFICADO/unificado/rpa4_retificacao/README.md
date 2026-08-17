# RPA 4 — Retificação de Contestação

**Existe desde 2026-08-10.** O Projeto 6 chegou com a HU-21 em `H21/`, e ela foi
migrada. O fluxo, etapa por etapa, está em [`FLUXO.md`](FLUXO.md).

## Escopo

| Campo | Valor |
|---|---|
| HU | **HU-21** — identificação de tráfego recuperado e retificação no AGI |
| Gatilho | Condição de negócio assíncrona: um tráfego contestado foi recuperado no mês seguinte |
| Origem | `projetos-origem/projeto-6-h20-h21/H21/` — o outro pedaço (HU-20) ficou no RPA 3 |

O Projeto 6 foi **o único que precisou ser cindido** entre dois RPAs, e ele já
veio cindido: `H20/` e `H21/` são dois pacotes irmãos, por cópia.

## O que mudou na migração

- **`conexao.py` não veio.** A origem falava com o MySQL por
  `mysql-connector`; aqui tudo passa por `comum/dados/repositorio_tabelas.py`
  (SQLAlchemy), que é quem sabe resolver SQLite em dev e WebFat em produção.
- **`print` → `logger`.** Na origem não havia log nenhum: os `print` iam para o
  console e o `db.log()` estava inteiramente comentado. Num passo irreversível,
  isso significa nenhuma trilha de auditoria.
- **O kill-switch passou a ser lido.** A origem declarava `PERMITIR_ACAO_AGI` e
  **nunca o consultava** — era decorativo, e no `.env` real estava ligado. Agora
  vale `PERMITIR_ACESSO_AGI`, que a configuração lê e o `--dry-run` desarma.
- **O `0,9635` virou constante** (`comum/config/constantes.FATOR_LIQUIDO_PIS_COFINS`),
  como esta página já exigia.
- **Os `assert` viraram `raise`.** `assert` desaparece com `python -O`, e a
  conferência que precede um evento irreversível não pode evaporar.
- **Os laços `while True` ganharam timeout.** Dois deles esperavam para sempre
  por uma imagem que pode nunca casar — sem log, sem saída.
- **A automação do AGI subiu para `comum/integracoes/agi.py`.** O critério de
  promoção (duas ocorrências reais em RPAs diferentes) passou a valer quando este
  robô nasceu. As telas da HU-21 estão agrupadas ao final da classe.
- **Ficou de fora:** `_ler_valor_dropdown` / `_selecionar_dropdown_por_valor`, a
  estratégia abandonada em 03/08 — código morto na origem, e a única coisa que
  puxava `pyperclip` para as dependências.

## Testes

37 testes em [`tests/`](tests/), cobrindo o que roda sem AGI: o cálculo do
evento, a conversão de valor BR, a busca do processo no CSV (com o export **real**
da grid como fixture, incluindo o caso das duas linhas que só diferem no valor),
a detecção e o encadeamento do controller com o AGI dublado.

Na origem não havia nenhum.

## Pendências de negócio, ainda abertas

Nenhuma é defeito do robô. Registradas em
[`../../docs/04-relatorios/duvidas-pendentes.md`](../../docs/04-relatorios/duvidas-pendentes.md).

- 🔴 **`carga_agi` tem dois donos.** Este robô o usa como "já retifiquei"; o
  RPA 3 como "o CONT_PROC subiu". Toda linha que o RPA 3 carregou fica invisível
  aqui. Resolver pede uma coluna própria (`retificacao_agi`) e um `ALTER TABLE`.
- **O critério de "recuperado" não foi validado.** Hoje só `vb_variacao_perc < 0`
  — poderia ser `minutos_variacao_perc`, ou as duas.
- **`vb_diferenca` × coluna "Valor Bruto" do CSV.** O cruzamento assume que são
  comparáveis; a origem registra que não confirmou. Se não for, o robô não acha o
  processo e **para** — falha ruidosa, que é o certo.
- **Nada confirma que o evento foi salvo.** O AGI não devolve sinal.
- **Nome de operadora que muda** (Q17): o cruzamento é por **EOT**, não por nome,
  então este robô não sofre com isso — a pendência segue valendo para o AGI.
- **Requer ambiente de teste do AGI** — o evento é irreversível (Q20).

## ⚠️ Segredos da origem

`H21/.env` traz senha do AGI (`TBR00841`) e do banco (`btime_prod`) em texto
claro, versionadas — o próprio cabeçalho do arquivo diz que segredos não deveriam
estar ali. **Nada disso foi copiado para cá**, mas as credenciais **precisam ser
rotacionadas**: remover o arquivo não desfaz a exposição.
