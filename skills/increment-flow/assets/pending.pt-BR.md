# Pendências — {{TOPIC}}

Itens para não esquecer nesta pesquisa. Uma tabela de incrementos (andamento de cada incremento), uma tabela de itens para o que ainda não está feito e uma tabela de feitos para o que está; cada item tem, abaixo, uma seção com o mesmo número, onde fica o texto completo.

- O `#` é o número da seção. Ele nunca muda e nunca é reaproveitado: "item N" e "§N" são sempre a seção N.
- Item novo entra no fim da tabela, com o próximo número livre.
- Item `Feito` vai, com a linha inalterada e mantendo o `#`, da tabela de itens para a tabela de feitos logo abaixo. Item `Recusado` ou `Rejeitado` fica na tabela de itens. Nos dois casos, o título da seção ganha o estado entre parênteses.

As colunas dos itens. Cada célula guarda só o que a coluna diz:

- **Item:** título curto, igual ao título da seção.
- **Estado:** só um valor da tabela de estados abaixo.
- **Depende de:** só números de item (`3` ou `3, 5`); `—` quando nada. Qualquer outra coisa que trave o item fica na seção.
- **Incremento:** só o número do incremento (`002`); `—` quando nenhum.
- **Detalhe:** resumo curto do que precisa ser feito, até 200 caracteres; o resto fica na seção.

| Estado | Quando usar |
|---|---|
| Aberto | registrado, nenhum trabalho começou |
| Em Pesquisa | discovery (`tlc-discover`) em andamento, ainda sem veredito |
| Pesquisado | discovery concluída com veredito; falta o plan |
| Em Planejamento | plan (`tlc-plan`) em andamento |
| Planejado | plan concluído; falta implementar |
| Desenvolvimento | implement (`tlc-implement`) em andamento |
| Feito | entregue e provado, com a linha movida para a tabela de feitos |
| Recusado | decidido não fazer |
| Rejeitado | fora do escopo atual, fica para outro momento |

Estado do incremento:

| Estado | Quando usar |
|---|---|
| Aberto | pasta aberta, nada feito ainda |
| Em Andamento | qualquer coisa feita nele: uma discovery, um plan, qualquer trabalho |
| Feito | fechado: todos os itens dele fechados e o trabalho commitado |

## Incrementos

| Número do Incremento | Título | Estado |
|---|---|---|
| 001 | Pesquisa inicial: {{TOPIC}} | Aberto |

## Itens

| # | Item | Estado | Depende de | Incremento | Detalhe |
|---|---|---|---|---|---|
| 1 | Pesquisa inicial: {{TOPIC}} | Aberto | — | 001 | {{SUMMARY}} |

## Itens Feitos

| # | Item | Estado | Depende de | Incremento | Detalhe |
|---|---|---|---|---|---|

## 1 — Pesquisa inicial: {{TOPIC}}

Registrado em {{DATE}}. {{QUESTION}}
