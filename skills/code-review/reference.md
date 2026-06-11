# review-full

Use esta skill para executar revisão completa de PR com múltiplos sub-agents especializados em paralelo.

Invocação: `/review-full <PR#>` ou `/review-full` (usa branch atual)

## Objetivo

Orquestrar 5 revisores especializados em paralelo sobre o mesmo PR e consolidar o resultado em um único relatório salvo no Obsidian.

## Agents invocados em paralelo

| Agent | Foco |
|---|---|
| `pr-code-quality-reviewer` | Qualidade: naming, complexidade, SOLID, padrões do projeto, cobertura |
| `pr-security-reviewer` | Segurança defensiva: auth, injeção, segredos, exposição de dados |
| `pr-comments-reviewer` | Comentários e docs: XML docs, comentários obsoletos ou enganosos |
| `pr-jira-requirements-linker` | Verifica se as mudanças atendem aos requisitos da issue Jira vinculada |
| `pr-build-test-validator` | Checkout da branch + dotnet build + dotnet test |

**Regra obrigatória: os 5 agents devem ser disparados em paralelo em uma única mensagem. Nunca dispare em sequência.**

---

## Fluxo obrigatório

### Passo 1 — Coletar contexto do PR

Se número de PR foi fornecido como argumento:

```bash
gh pr view <PR#> --json number,title,body,headRefName,baseRefName,url,state
gh pr diff <PR#>
gh pr view <PR#> --json files
```

Se nenhum número foi fornecido, tente usar a branch atual:

```bash
git branch --show-current
gh pr view --json number,title,body,headRefName,baseRefName,url,state 2>/dev/null
git diff origin/develop...HEAD
git diff origin/develop...HEAD --name-only
```

Extraia:
- `branch_name` — nome da branch do PR
- `pr_title` — título do PR
- `pr_description` — descrição (pode conter SDN-XXXX)
- `base_branch` — branch base (develop por padrão)
- `pr_number` — número do PR no GitHub (se existir)
- `changed_files` — lista de arquivos modificados
- `diff` — diff completo

### Passo 2 — Determinar task_id

Tente extrair o ID de task nesta ordem:

1. Procure `{codigo-projeto}-\d+` no `branch_name`, `pr_title` e `pr_description`.
2. Se encontrar: `task_id = SDN-XXXX`.
3. Se não encontrar: `task_id = PR-<pr_number>` ou `BRANCH-<branch-slug>`.

### Passo 3 — Disparar os 5 agents em paralelo

Numa única mensagem, dispare simultaneamente os 5 agents abaixo.
Passe o contexto relevante para cada um no prompt.

**Agent 1 — pr-code-quality-reviewer**
Prompt:
```
Revise a qualidade do código do PR.
Branch: <branch_name>
Arquivos alterados: <changed_files>
Diff:
<diff>
```

**Agent 2 — pr-security-reviewer**
Prompt:
```
Revise os riscos de segurança das mudanças do PR.
Branch: <branch_name>
Arquivos alterados: <changed_files>
Diff:
<diff>
```

**Agent 3 — pr-comments-reviewer**
Prompt:
```
Revise a qualidade de comentários e documentação das mudanças do PR.
Branch: <branch_name>
Arquivos alterados: <changed_files>
Diff:
<diff>
```

**Agent 4 — pr-jira-requirements-linker**
Prompt:
```
Verifique se o PR atende aos requisitos da issue Jira vinculada.
Título do PR: <pr_title>
Descrição do PR: <pr_description>
Branch: <branch_name>
Arquivos alterados: <changed_files>
Diff resumido: <diff (primeiras 200 linhas ou resumo)>
```

**Agent 5 — pr-build-test-validator**
Prompt:
```
Faça checkout da branch e valide o build e os testes.
Branch: <branch_name>
Branch base: <base_branch>
```

### Passo 4 — Consolidar resultados

Aguarde todos os agents retornarem.

Para cada agent, extraia:
- Sumário em uma linha
- Achados com severidade (critical / high / medium / low / info)
- Arquivos afetados
- Ações recomendadas

Monte o relatório consolidado usando o formato abaixo.

### Passo 5 — Salvar no Obsidian

Salve em:

```
.cofre-backend/ai-obsidian-vault/07_AGENT_OUTPUTS/pr-reviews/<task-id>-pr-review.md
```

Aplique a skill `obsidian-linker` antes de salvar.

---

## Formato do relatório consolidado

```md
---
type: pr_review
task_id:
pr_number:
branch:
base_branch:
pr_url:
status: approved|changes_required|blocked
created_at:
agents_used:
  - pr-code-quality-reviewer
  - pr-security-reviewer
  - pr-comments-reviewer
  - pr-jira-requirements-linker
  - pr-build-test-validator
technologies:
project:
---

# PR Review — <task-id> — <pr_title>

## Sumário Executivo

> Uma linha. Decisão final: APPROVED | CHANGES_REQUIRED | BLOCKED

## Build e Testes

> Output consolidado do pr-build-test-validator.
> Status: PASSOU | FALHOU | NÃO RODOU
> Motivo se falhou.

## Requisitos Jira

> Output do pr-jira-requirements-linker.
> Issue: <SDN-XXXX> ou "nenhuma issue vinculada encontrada"
> Requisitos atendidos / não atendidos / não verificados.

## Qualidade de Código

> Output do pr-code-quality-reviewer.

## Segurança

> Output do pr-security-reviewer.

## Comentários e Documentação

> Output do pr-comments-reviewer.

## Achados Consolidados por Severidade

### Critical

### High

### Medium

### Low

### Informacional

## Decisão Final

APPROVED | CHANGES_REQUIRED | BLOCKED

### Razão

### Ações necessárias antes do merge (se houver)

## Ligações Obsidian
```

---

## Resposta final ao Gabriel

Após salvar o relatório, responda com:

```
## Revisão Completa — <pr_title>

**Decisão:** APPROVED | CHANGES_REQUIRED | BLOCKED

| Dimensão | Status | Resumo |
|---|---|---|
| Build/Testes | ✅/❌/⚠️ | <1 linha> |
| Requisitos Jira | ✅/⚠️/❌/➖ | <1 linha> |
| Qualidade de Código | ✅/⚠️/❌ | <1 linha> |
| Segurança | ✅/⚠️/❌ | <1 linha> |
| Comentários/Docs | ✅/⚠️/❌ | <1 linha> |

**Achados principais:**
- [severidade] <achado>
...

**Relatório completo:** .cofre-backend/ai-obsidian-vault/07_AGENT_OUTPUTS/pr-reviews/<task-id>-pr-review.md
```

---

## Regras de paralelização

1. Nunca dispare agents um por vez quando podem rodar juntos.
2. Os 5 agents são independentes entre si — sempre paralelos.
3. Só consolide após todos retornarem.
4. Se um agent falhar ou não retornar, marque a dimensão como "⚠️ não executado" e prossiga com os demais.

## Fallback

Se `gh` não estiver disponível ou não houver PR aberto:
- Use `git diff origin/develop...HEAD` para o diff.
- Use `git log --oneline origin/develop..HEAD` para o contexto.
- Para o pr-build-test-validator, use a branch atual sem checkout.
- Marque `pr_number` como "N/A" no relatório.
