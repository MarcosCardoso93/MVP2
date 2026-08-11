# Projeto 1 — Épico 1: Captura de Arquivos via E-mail

**Insira aqui o código do Projeto 1, sem alterações.**

---

## Escopo

| Campo | Valor |
|---|---|
| Épico | 1 — Captura de Arquivos via E-mail |
| HUs | HU-01, HU-02, HU-03 |
| RPA de destino | **RPA 1 — Captura de Arquivos das Operadoras** |
| Transformação | **Direta (1:1)** — único projeto que mapeia sozinho num RPA |
| Ordem de análise | **1º** |

## Responsabilidades

1. Acessar a caixa `detrafTBRA.br@telefonica.com` no Outlook Desktop Classic
2. Localizar e-mails do mês de referência que **não** contenham a palavra "CONTESTAÇÃO"
3. Baixar apenas anexos `.csv` ou Excel
4. Organizar os e-mails na pasta "Detraf Despesas" do Outlook
5. Identificar a operadora pela **EOT da Credora** no Anexo 5 (coluna nome fantasia)
6. Salvar na pasta de rede da operadora/mês **e** no servidor do WebFat
7. Sinalizar "não validado" no WebFat para arquivos divergentes

**Entrega:** arquivos salvos e replicados, prontos para o RPA 2 processar.

---

## 🔴 Verificação prioritária — HU-02

**A V2 mudou o mecanismo de identificação da operadora.**

| | Mecanismo |
|---|---|
| **V1 (revogada)** | domínio do remetente + tabela de contatos do WebFat |
| **V2 (vigente)** | **EOT da Credora lida no arquivo** + Anexo 5, coluna nome fantasia |

Se o código implementa a V1, isto é **retrabalho**, não migração — dimensione à parte.

**Consequência da V2:** é preciso **abrir o anexo** antes de saber onde salvá-lo. Verifique a ordem das operações no código.

---

## Pontos de atenção

- **Data de corte indefinida (Q1).** O critério V1 "varredura diária após o dia 05" perdeu sustentação; a V2 não colocou nada no lugar. Como o código implementa a periodicidade hoje?
- **Casos de exceção da HU-02 (Q16).** Arquivo corrompido, protegido por senha, coluna Credora vazia, EOT ausente do Anexo 5, e-mail com anexos de mais de uma operadora — a V2 não define nenhum desses.
- **Salvamento no servidor do WebFat** é novo na V2. Está implementado?
- **Reenvio com o mesmo nome** deve sobrescrever e reiniciar o processamento.
- **Local × WebFat × Lagoa (Q15).** O item 2.13 da V2 sugere que o robô salve local e que a transferência para o Lagoa seja **manual, feita pelo analista** — o que conflita com a HU-03.
- **Criação da pasta do mês** copiando a estrutura do mês anterior.

## Candidatos a componente compartilhado esperados aqui

Consulta ao Anexo 5 · construção de caminhos de rede · convenções de nome de arquivo · automação do Outlook (leitura e movimentação) · acesso ao banco WebFat · logging · configuração.

---

## Procedimento

1. [`../../docs/03-checklists/checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md)
2. [`../../docs/05-proxima-etapa/roteiro-analise-tecnica.md`](../../docs/05-proxima-etapa/roteiro-analise-tecnica.md)
3. [`../../docs/03-checklists/checklist-analise-de-codigo.md`](../../docs/03-checklists/checklist-analise-de-codigo.md)

**Saídas:** `trabalho/inventarios/recebimento-projeto-1.md` e `inventario-projeto-1.md`

**Detalhamento das HUs:** [`../../docs/01-entendimento/entendimento-das-historias.md`](../../docs/01-entendimento/entendimento-das-historias.md)

> ⚠️ Este projeto é o **primeiro a ser analisado e o primeiro a ser migrado**. É onde o processo se calibra e onde a base comum nasce. Se algo falha aqui, falha em tudo.
