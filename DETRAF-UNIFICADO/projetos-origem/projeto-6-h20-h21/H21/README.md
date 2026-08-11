# HU-21 - Identificação de tráfego recuperado e retificação AGI

Pacote isolado para a HU-21 (Épico 6 - Encontro de Contas), montado seguindo a mesma
estrutura do Épico 5 e do exemplo de referência `RPA_DETRAF_RECEITA`.

Legenda: ✅ Pronto (reaproveitado)  |  🔄 Adaptado  |  🆕 A criar

**Aviso importante**: esta é a HU com menor reaproveitamento de todo o projeto até agora —
o exemplo de Receita nunca automatizou "Contestação > Gerenciar" nem nada parecido com um
evento de retificação. Praticamente tudo aqui é esqueleto novo.

## Critérios de aceite x status

| Critério | Status |
|---|---|
| Identificação de tráfego recuperado (variação negativa no mês corrente) | 🆕 A criar (regra de negócio ainda não definida) |
| Filtro no AGI por período e operadora | 🆕 A criar (imagens não existem) |
| Seleção do ID Processo correto | 🆕 A criar — **em aberto**: reconhecimento por imagem não é suficiente, ver README/manifesto |
| Tipo Evento = "Recuperação" | 🆕 A criar (dropdown, padrão adaptado do `_selecionar_periodo`) |
| Campo Duração = minutos da diferença | ✅ Fórmula já implementada (`_calcular_valores_evento`) |
| Valor Líquido = VB × 0,9635 | ✅ Fórmula já implementada |
| Valor PIS/Cofins = VB − Valor Líquido | ✅ Fórmula já implementada |
| Valor Bruto Negociado = VB da tabela | ✅ Fórmula já implementada |

## ✅ O que está pronto (reaproveitado 1:1)

- `AGI_config.py` completo — login, abrir/fechar AGI, helpers de imagem (`_click`,
  `_wait_appear`, `_Janela_salvar`).
- `conexao.py`, `utils.py`, `requirements.txt` — copiados sem alteração.
- **As 4 fórmulas de cálculo** dos campos do evento de Recuperação (Duração, Valor Líquido,
  Valor PIS/Cofins, Valor Bruto Negociado) já estão implementadas em
  `_calcular_valores_evento` — são regras de negócio simples e bem definidas no To Be MVP2
  (parágrafos 369-372), isoladas em uma função pura que pode ser testada sem precisar do
  AGI aberto.

## 🔄 O que foi adaptado (padrão de código, não código pronto)

- **Kill-switch** (`PERMITIR_ACAO_AGI`) — mesmo padrão de segurança do Épico 5, adaptado
  para esta HU (permite calcular tudo e só não grava no AGI até estar validado).
- **Navegação até "Contestação > Gerenciar"** — mesmo código já esboçado na HU-18 (Épico 5).
  Como é a mesma tela, as imagens de menu podem ser reaproveitadas de lá.
- **Seleção de opção em dropdown** (campo "Tipo Evento") — inspirado no método
  `AGI_config._selecionar_periodo()`, que já faz seleção de dropdown via teclado
  (down/tab/shift+tab/space) em vez de imagem por opção. A ideia é a mesma, mas a
  sequência de teclas precisa ser calibrada nesta tela específica.
- **Preenchimento de campo de texto** — mesmo padrão de `pyautogui.typewrite(...)` usado em
  `AGI_config.Login_AGI_producao()`.

## 🆕 O que precisa ser criado do zero

1. **Regra de negócio "identificar tráfego recuperado"** (`_identificar_trafego_recuperado`):
   hoje é um esqueleto vazio. Precisa definir a fonte de dados (comparar a Base de
   Contestação do mês corrente com o histórico de contestações já enviadas) e a lógica de
   variação negativa.
2. **6 imagens novas** da tela de Contestação > Gerenciar (campo período, campo empresa,
   botão buscar, botão "+ Adicionar", campo Tipo Evento, botão Salvar) — checklist completo
   em `src/view/imagens/AGI_Contestacao_Gerenciar/MANIFESTO_IMAGENS.md`. Duas outras imagens
   (menu Contestação / submenu Gerenciar) são compartilhadas com a HU-18 e não precisam ser
   recapturadas se já existirem lá.
3. **Seleção do ID Processo na grid de resultado** — sinalizado no código com
   `raise NotImplementedError`. Reconhecimento por imagem não resolve isso (a lista muda a
   cada busca); precisa avaliar uma abordagem via `pywinauto` para localizar a linha pelo
   número do processo.
4. Gravação em tabela de log específica da Despesa (mesma pendência do Épico 5/HU-20).

## Checklist antes de rodar

1. Definir e implementar a regra de identificação de tráfego recuperado.
2. Capturar as imagens novas (ver manifesto) e confirmar/copiar as 2 compartilhadas com a HU-18.
3. Resolver a estratégia de seleção do ID Processo antes de remover o `NotImplementedError`.
4. Copiar `.env.example` para `.env` e ajustar os caminhos.
5. Rodar primeiro com `PERMITIR_ACAO_AGI=False` para validar os cálculos sem tocar no AGI.
