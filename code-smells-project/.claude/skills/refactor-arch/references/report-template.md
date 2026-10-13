# Template do relatório de auditoria (Fase 2)

O relatório é impresso inteiro no terminal e salvo em `$WORK/audit-report.md`. Mesma estrutura
em qualquer stack. Preencha com valores reais; não deixe placeholder.

Regras:
- Achados **ordenados por severidade** (CRITICAL → HIGH → MEDIUM → LOW) e numerados em sequência.
- Cada achado tem **arquivo e linhas exatos** (`models.py:28-41` ou `models.py:28, 48, 58`).
- Um achado por problema; ocorrências do mesmo problema ficam juntas.
- Evidência: sonda do baseline, saída de script ou "confirmado por leitura". Nada de "pode ser".
- **Nunca copie valor de segredo**, senha ou número de cartão. Cite arquivo, linha e nome da
  variável.
- Seção de APIs deprecated sempre presente, mesmo que seja para dizer que não há uso.
- O que é melhoria de arquitetura ou de fluxo, e não defeito, vai em "Melhorias propostas", não
  na lista de achados.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta>
Stack:   <linguagem> + <framework versão>
Files:   <N> analyzed | ~<linhas> lines of code
Grade:   <A monólito | B camadas parciais | C organizado>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n> | Total: <n>

## Findings

### [CRITICAL] #1 <título curto> (<AP id>)
File: <arquivo:linhas>
Description: <o que o código faz, em uma ou duas frases concretas>
Impact: <o que acontece por causa disso: dado exposto, quebra, custo de manutenção>
Evidence: <sonda/saída/leitura>
Recommendation: <correção concreta> (playbook <T id>)

### [HIGH] #2 ...

...

## Deprecated APIs
| Uso | Onde | Equivalente moderno | Fonte |
|---|---|---|---|
| <api> | <arquivo:linhas (N ocorrências)> | <substituto> | <tabela do catálogo / Context7 / aviso do interpretador> |
(ou: "Nenhum uso de API deprecated encontrado no código. Versões antigas de dependência estão em AP27.")

## Dependencies
<resultado do pip-audit / npm audit: total por severidade e pacotes principais>
(ou: "Auditoria de dependências não executada: <motivo>.")

## Baseline (estado atual dos endpoints)
<N> requisições | <n> 5xx/sem resposta | <n> derrubaram o processo
<lista curta das sondas e do que mostraram>

## Proposed improvements (not defects)
- <melhoria de arquitetura/fluxo que não é bug, e por quê>

## Phase 3 plan
- Target structure: <árvore resumida>
- Intentional behavior changes: <lista, cada uma com o achado que a justifica>
- Out of scope: <o que não será feito e por quê>

================================
Total: <n> findings
================================
```

Ao final, a pergunta da pausa (ver `SKILL.md`):

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```
