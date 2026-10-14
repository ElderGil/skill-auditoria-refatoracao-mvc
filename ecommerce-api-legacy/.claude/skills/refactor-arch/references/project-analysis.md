# Análise de projeto (Fase 1)

Como transformar o JSON do `inventory.py` em diagnóstico: stack, banco, arquitetura, grau de
organização e domínio. O script dá os fatos; esta referência diz como interpretá-los e o que
conferir lendo o código.

## Índice

1. [Linguagem e framework](#1-linguagem-e-framework)
2. [Banco de dados](#2-banco-de-dados)
3. [Arquitetura atual e grau de organização](#3-arquitetura-atual-e-grau-de-organização)
4. [Domínio](#4-domínio)
5. [Resumo da Fase 1](#5-resumo-da-fase-1)
6. [Preparar o ambiente sem tocar no projeto](#6-preparar-o-ambiente-sem-tocar-no-projeto)
7. [Plano de fumaça](#7-plano-de-fumaça)

---

## 1. Linguagem e framework

| Sinal (ordem de confiança) | Conclusão |
|---|---|
| Manifesto: `requirements.txt`, `pyproject.toml`, `Pipfile` | Python |
| Manifesto: `package.json` (sem `typescript` nem `.ts`) | Node.js / JavaScript |
| `package.json` com `typescript` ou arquivos `.ts` | Node.js / TypeScript |
| `go.mod`, `pom.xml`/`build.gradle`, `Gemfile`, `composer.json` | Go, Java/Kotlin, Ruby, PHP |
| Sem manifesto | Linguagem com mais linhas (`lines_by_language`) |

Framework: dependência declarada no manifesto (`flask`, `django`, `fastapi`, `express`, `koa`,
`fastify`, `@nestjs/core`...). Confirme no código: `Flask(__name__)`, `express()`, `FastAPI()`.
Se a versão não estiver fixada no manifesto, diga isso ("Express ^4.18.2, faixa — sem lock"),
e se houver lockfile (`package-lock.json`, `poetry.lock`), leia a versão resolvida dele.

Dependências: liste as de runtime além do framework (ex.: `flask-cors`, `sqlite3`). Marque as
declaradas e não importadas em lugar nenhum (`grep` pelo nome do módulo); isso vira achado de
código morto na Fase 2.

## 2. Banco de dados

- Dependência (`sqlite3`, `psycopg2`, `mongoose`, `flask-sqlalchemy`...) e dica no código
  (`sqlite3.connect`, `sqlite:///`, `:memory:`, URL de conexão).
- Tabelas: `CREATE TABLE` (SQL à mão) ou `__tablename__` / nome das classes de model (ORM).
- Anote **onde** o acesso a dados acontece (arquivo de model, rota, controller, classe-deus).
  Isso alimenta o mapa de arquitetura e o achado de mistura de camadas.
- Anote se o banco é arquivo (cria `*.db` no diretório onde roda), em memória (zera a cada boot)
  ou servidor externo. Isso define como o plano de fumaça prepara dados.

## 3. Arquitetura atual e grau de organização

Use `layer_dirs`, o tamanho dos arquivos (`files`) e a leitura dos 2–3 maiores arquivos.

| Grau | Como reconhecer | O que a Fase 3 faz |
|---|---|---|
| **A — Monólito** | Sem pastas de camada; 1 a 5 arquivos concentram rotas, SQL e regra; um arquivo ou classe com mais de ~250 linhas misturando domínios | Cria a estrutura MVC inteira e redistribui o código |
| **B — Camadas parciais** | Existem pastas (`models/`, `routes/`, `services/`...), mas a regra de negócio e a serialização estão nas rotas; models anêmicos; serviços sem uso | Mantém o que serve, move regra para a camada certa, cria o que falta (config, controllers, error handler, factory) |
| **C — Organizado** | Camadas com responsabilidades respeitadas, entrada única, config externa | Corrige pontualmente; mudança estrutural só onde houver achado |

Descreva a arquitetura em uma frase concreta, com números: "Monolítica — 4 arquivos, rotas em
`app.py`, SQL e regra em `models.py` (314 linhas, 4 domínios)". Evite rótulo vago como "código
legado".

Pontos de entrada: `if __name__ == "__main__"`, `app.run(`, `.listen(`, `main`/`scripts.start`
do `package.json`. Portas fixas no código (`hardcoded_ports`) entram no achado de configuração e
no plano de fumaça.

## 4. Domínio

Infira pelo nome das tabelas, das rotas e das entidades, e diga em uma linha o que a aplicação
faz e quais são as entidades: "E-commerce API (produtos, pedidos, usuários, relatório de
vendas)", "LMS com checkout (cursos, matrículas, pagamentos)", "Task Manager (tarefas,
usuários, categorias, relatórios)". Se o README do projeto disser o domínio, use-o para
confirmar, não para substituir o que o código mostra.

## 5. Resumo da Fase 1

Imprima exatamente neste formato (valores reais, sem placeholder):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem>
Framework:     <framework + versão declarada>
Dependencies:  <dependências de runtime além do framework>
Domain:        <domínio em uma linha, com as entidades>
Architecture:  <grau A/B/C + descrição concreta>
Source files:  <N> files analyzed (<linhas> lines)
DB tables:     <tabelas>
Endpoints:     <N> (<lista curta método + caminho, ou "ver abaixo">)
Entry point:   <arquivo:linha e comando de execução>
================================
```

O número de arquivos é o `source_files` do inventário (não conte arquivos da skill, `node_modules`
nem ambientes virtuais).

## 6. Preparar o ambiente sem tocar no projeto

Nada da Fase 1 e da Fase 2 escreve dentro do projeto. Tudo vai para a pasta de trabalho
`$WORK` (fora do projeto, ver `SKILL.md`).

- **Python:** `python3 -m venv "$WORK/venv" && "$WORK/venv/bin/pip" install -q -r requirements.txt`
  (ou `pip install -q .` se for `pyproject.toml`).
- **Node:** `mkdir -p "$WORK/deps" && cp package.json package-lock.json "$WORK/deps/" 2>/dev/null;
  (cd "$WORK/deps" && npm ci --no-audit --no-fund || npm install --no-audit --no-fund)`.
  O plano liga `node_modules` da cópia a `$WORK/deps/node_modules`.
- Se a instalação falhar por versão de interpretador, registre como achado de ambiente e tente a
  menor mudança possível (nunca editando o projeto na Fase 1).

Auditoria de dependências (fato, não opinião; rode se houver rede):
- Python: `"$WORK/venv/bin/pip" install -q pip-audit && "$WORK/venv/bin/pip-audit" -r requirements.txt`
- Node: `(cd "$WORK/deps" && npm audit --omit=dev)`
Se não for possível rodar, diga que não rodou. Não invente CVE.

## 7. Plano de fumaça

`$WORK/plan.json` descreve como subir a aplicação e quais requisições fazer. O `smoke.py` roda o
plano numa cópia temporária do projeto, numa porta livre, e nunca toca o banco original.

```json
{
  "setup": ["{work}/venv/bin/python seed.py"],
  "start": {"before": "{work}/venv/bin/flask --app app run -p {port}",
            "after":  "{work}/venv/bin/python app.py"},
  "port": null,
  "link": {"node_modules": "{work}/deps/node_modules"},
  "env": {"FLASK_DEBUG": "0"},
  "env_mode": {"after": {"ADMIN_TOKEN": "smoke-admin-token"}},
  "boot_timeout": 30,
  "requests": [
    {"id": "listar-produtos", "method": "GET", "path": "/produtos"},
    {"id": "criar-produto", "method": "POST", "path": "/produtos",
     "json": {"nome": "Produto Teste", "preco": 10.5, "estoque": 3, "categoria": "geral"}},
    {"id": "listar-usuarios", "method": "GET", "path": "/usuarios",
     "after": {"removed_keys": ["senha"], "note": "senha deixa de ser exposta (achado #4)"}},
    {"id": "sonda-qtd-negativa", "kind": "probe", "method": "POST", "path": "/pedidos",
     "json": {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": -5}]},
     "after": {"status": 400, "note": "quantidade inválida passa a ser rejeitada (achado #10)"}}
  ]
}
```

Campos:
- `start` e `setup` aceitam um valor único ou `{"before": ..., "after": ...}` quando o comando
  muda com a refatoração. Placeholders: `{port}`, `{work}`, `{src}` (projeto original), `{run}`
  (cópia em execução). A variável de ambiente `PORT` sempre é exportada.
- `port`: deixe `null` para porta livre. Só fixe se a aplicação original não aceitar porta por
  argumento nem por ambiente (ex.: `{"before": 3000, "after": null}`).
- `kind: "probe"`: requisição hostil (ver `hostile-inputs.md`). Só o status e a queda do
  processo são conferidos, não o formato.
- `after`: o que muda de propósito depois da refatoração. `status` (ou `status_in: [400, 422]`),
  `removed_keys` (campos que deixam de existir, ex.: senha), `body_kind` (ex.: `"json"` quando a
  resposta deixa de ser texto puro), `shape: "any"` (formato livre), `headers` não existe aqui:
  cabeçalhos ficam na própria requisição. **Toda entrada `after` precisa de `note` citando o
  achado que a justifica.** Mudança sem achado é quebra de contrato, não correção.

Como montar:
1. Um caminho feliz para **cada** endpoint do inventário, com dados válidos tirados do seed, do
   `api.http`/README do projeto ou do próprio código.
2. Ordem: leituras → criações → atualizações → exclusões, para uma requisição não destruir o dado
   da outra. Use IDs que existem depois do seed.
3. Sondas no fim, uma por achado CRITICAL/HIGH confirmável por HTTP. Sonda que derruba o processo
   vai por último (o `smoke.py` reinicia a app, mas o estado em memória se perde).
4. Rotas administrativas que a Fase 3 vai proteger: no caminho feliz, mande o cabeçalho de
   autorização que a refatoração vai exigir (o original ignora); acrescente uma sonda sem o
   cabeçalho com `after.status` 401/403.
5. Endpoint destrutivo que apaga tudo (ex.: reset do banco) entra só como sonda sem autorização,
   nunca como caminho feliz no meio do plano.
