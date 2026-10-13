---
name: refactor-arch
description: >
  Audita e refatora um projeto backend para o padrão MVC, em qualquer stack (Python/Flask,
  Node.js/Express e outras). Use quando o usuário invocar "/refactor-arch" ou pedir para "auditar a
  arquitetura", "achar code smells e corrigir", "refatorar este projeto para MVC". Roda em 3 fases:
  análise da stack e da arquitetura; relatório de auditoria com severidade e arquivo:linha, com
  pausa obrigatória para confirmação; refatoração validada por boot da aplicação e chamada dos
  endpoints. NÃO use para revisar um diff ou PR, implementar feature nova, gerar testes isolados ou
  analisar repositório sem aplicação executável. Produz o resumo da Fase 1, o relatório da Fase 2 e
  o projeto refatorado com o resultado da validação.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[caminho do projeto; padrão: diretório atual]"
---

# Refactor Arch

Três fases em sequência: **analisar → auditar e pausar → refatorar e validar**. Os fatos vêm de
scripts determinísticos (`scripts/`); a interpretação, a classificação e a correção são suas,
guiadas pelas referências (`references/`). Leia cada referência só na fase que pede.

## Regras que valem o tempo todo

1. **Fases 1 e 2 não escrevem no projeto.** Ambiente, planos, baseline e relatório ficam na pasta
   de trabalho `WORK`, fora do projeto. O primeiro arquivo do projeto só muda depois da confirmação.
2. **Segredo nunca aparece na saída.** Cite `arquivo:linha` e o nome da variável; nunca o valor de
   chave, senha, token ou cartão. Não leia nem altere `.env` nem arquivos de banco (`*.db`).
3. **Sem confirmação explícita, não há Fase 3.**
4. **Só declare sucesso com evidência.** A Fase 3 termina com o `smoke.py compare` verde, ou com a
   falha relatada como falha.
5. Não faça commit nem push. Quem decide o commit é o usuário.

## Preparação

Resolva os caminhos uma vez e use os valores absolutos em todos os comandos (o estado do shell não
persiste entre chamadas):

```bash
PROJECT="$(pwd)"            # ou o caminho passado como argumento
WORK="${TMPDIR:-/tmp}/refactor-arch/$(basename "$PROJECT")"
mkdir -p "$WORK" && echo "PROJECT=$PROJECT" && echo "WORK=$WORK"
```

Scripts: `${CLAUDE_SKILL_DIR}/scripts/` (Python 3, só biblioteca padrão).

## Fase 1 — Análise

1. Rode `python3 "${CLAUDE_SKILL_DIR}/scripts/inventory.py" "$PROJECT" --out "$WORK/inventory.json"`.
2. Leia `references/project-analysis.md`, seções 1 a 5. Abra os manifestos e os maiores arquivos
   para confirmar framework, banco, pontos de entrada e o grau de organização (A, B ou C).
3. Imprima o resumo **PHASE 1: PROJECT ANALYSIS** no formato da seção 5.
4. Prepare o ambiente em `WORK` (seção 6): venv ou `npm ci` fora do projeto e, se houver rede,
   auditoria de dependências.

## Fase 2 — Auditoria

1. Rode `python3 "${CLAUDE_SKILL_DIR}/scripts/scan_signals.py" "$PROJECT" --out "$WORK/signals.json"`.
2. Leia `references/antipatterns-catalog.md` e `references/hostile-inputs.md`.
3. Confirme cada grupo de sinais **lendo o trecho**: achado real, falso positivo (descarte) ou
   ocorrência do mesmo achado. Leia também os arquivos principais por inteiro: god class, regra
   no controller, transação, integridade e máquina de estados (AP21–AP25) não têm sinal de regex.
4. Percorra os endpoints com a lista de entradas hostis. Para cada consequência grave, crie uma
   sonda.
5. APIs deprecated: use a tabela do AP16. Se houver ferramentas do MCP Context7 nesta sessão
   (`resolve-library-id` / `query-docs`), confirme na documentação da versão declarada. Sem elas,
   siga com a tabela e diga a fonte no relatório.
6. Escreva `"$WORK/plan.json"` (seção 7 do `project-analysis.md`): caminho feliz de todos os
   endpoints mais as sondas. Rode o baseline no código original:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/smoke.py" baseline --plan "$WORK/plan.json" --project "$PROJECT" --work "$WORK"`.
   O resultado das sondas é evidência para o relatório. Se a aplicação original não subir, registre
   o motivo e avise que a Fase 3 não terá contra o que comparar.
7. Monte o relatório com `references/report-template.md`, ordenado de CRITICAL a LOW, e salve em
   `"$WORK/audit-report.md"`. Imprima o relatório inteiro.
8. **Pausa obrigatória.** Pergunte: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.
   Use `AskUserQuestion` se estiver disponível; se não estiver (execução não interativa), imprima a
   pergunta e **encerre o turno**. Só siga com resposta afirmativa explícita (`y`, `sim`, `yes`).
   Resposta negativa: encerre informando onde está o relatório.

## Fase 3 — Refatoração

1. **Pré-checagem:** `git -C "$PROJECT" status --porcelain -- .`. Se houver arquivo rastreado
   modificado, pare e pergunte (a refatoração precisa de ponto de retorno limpo). Anote o
   `git rev-parse HEAD` para o resumo.
2. Leia `references/mvc-guidelines.md`, `references/stacks/<flask|express|generic>.md` (só o da
   stack) e `references/refactoring-playbook.md`.
3. Imprima a estrutura alvo e o mapa arquivo antigo → novo **antes** de editar.
4. Refatore na ordem do playbook. Corrija todos os achados CRITICAL e HIGH; corrija MEDIUM e LOW no
   código que for tocado. Preserve o contrato (rotas, campos, envelope, status do caminho feliz,
   comando de execução). Atualize o README do projeto e crie `.env.example` se a execução passar a
   usar variáveis de ambiente.
5. Atualize `"$WORK/plan.json"`: comando `start.after` se mudou, e `after` + `note` **somente** para
   mudanças intencionais ligadas a um achado do relatório. Nunca afrouxe o plano para fazer uma
   falha passar.
6. Checagem rápida: import/compilação (comandos no guia da stack).
7. **Gate:** rode `smoke.py compare` com os mesmos argumentos do baseline.
   - `exit 0`: siga.
   - `exit 2`: leia cada violação, corrija o código e rode de novo.
   - Depois de **3** rodadas sem verde, pare, mostre as violações e pergunte como seguir
     (`AskUserQuestion` ou fim do turno).
8. Rode `scan_signals.py` de novo no projeto refatorado e compare com `"$WORK/signals.json"` por
   AP. Cada sinal que restou precisa de justificativa (falso positivo, fora de escopo) ou correção.
9. Imprima o resumo final e salve em `"$WORK/phase3-summary.md"`:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore real dos arquivos de código, depois da refatoração>

## Validation
  ✓|✗ Application boots without errors (<comando>)
  ✓|✗ All endpoints respond correctly (<n>/<n> requisições conferidas contra o baseline)
  ✓|✗ Probes fixed (<n>/<n> sondas com o comportamento corrigido)
  ✓|✗ Anti-pattern signals: <antes> → <depois> (restantes justificados abaixo)

## Intentional behavior changes
- <mudança> (achado #n)

## Proposed improvements (not applied)
- <melhoria> — <motivo de ficar fora>

## How to run
<comandos, variáveis de ambiente>

Rollback: git checkout <hash anotado> -- .  (arquivos novos: git clean -n para listar antes de remover)
================================
```

Use ✗ quando não for verdade. "Zero anti-patterns remaining" só aparece se o scan confirmar.
