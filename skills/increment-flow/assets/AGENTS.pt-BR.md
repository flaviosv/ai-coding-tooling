# AGENTS.md — Pesquisa: {{TOPIC}}

Esta pasta guarda uma pesquisa, tocada em incrementos pequenos e numerados. Carregue a skill `increment-flow` antes de mexer no `pending.md` ou numa pasta de incremento: ela tem os procedimentos, e o `scripts/pending.py check` dela precisa passar depois de toda edição do `pending.md`.

## Mapa

| Caminho | O que é | Leia quando |
|---|---|---|
| `001-*/` | A pesquisa inicial: veredito e decisões do tema inteiro | Antes de abrir qualquer incremento |
| `NNN-<slug>/` | Um incremento e tudo o que ele produz | Ao trabalhar nesse incremento |
| `pending.md` | Estado de cada incremento, e todos os itens desta pesquisa com o estado de cada um e o incremento que o trabalha | Antes de escolher o que fazer a seguir |
| `progress.md` | Resumo do que cada incremento decidiu, fez e mudou até agora | Ao retomar o trabalho, ou antes de mexer num incremento que você não começou |

## Regras

- **Decisão já fechada na pesquisa inicial é entrada, não pauta.** Reabrir exige um motivo nomeado.
- **Mantenha o `pending.md` em dia.** Atualize o estado do item na hora em que ele avança, sem esperar o incremento fechar.
- **Um incremento não fecha com lacuna aberta.** Cada lacuna da verificação independente vira correção no próprio incremento, ou vai ao usuário e só entra no `pending.md` com a aceitação dele registrada.
- **Ao fechar um incremento, devolva o aprendizado** à pesquisa inicial (a decisão, o item ou a evidência que ele mudou), apontando para a pasta do incremento.
- **Mantenha o `progress.md` em dia.** Quando um incremento decide, conclui, muda, customiza ou adiciona algo que vale saber depois, acrescente uma linha na seção desse incremento. Um resumo, não uma transcrição.
- **`IC <x>` é o incremento `<x>`** (`IC 3` → `003-<slug>/`), nunca o item `<x>`.
- **Versionada:** {{VERSIONED}}
