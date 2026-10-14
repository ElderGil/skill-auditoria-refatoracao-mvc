# Entradas hostis (Fase 2)

Ler o código acha a maior parte dos problemas; o resto aparece quando cada endpoint é provocado.
Para cada endpoint que recebe dados, percorra a lista abaixo **lendo o handler** e decida o que
aconteceria. Quando a consequência for grave (500, queda do processo, dado corrompido, acesso
indevido), transforme a provocação em **sonda** no plano de fumaça (`kind: "probe"`): o baseline
registra o comportamento atual como evidência, e a Fase 3 prova a correção.

Sondas rodam só na cópia temporária do `smoke.py`. Nunca mande requisição hostil para uma
instância real.

| # | Provocação | O que procurar no handler | Achado típico |
|---|---|---|---|
| 1 | **Tipo errado** em cada campo: número onde se espera texto e o contrário, lista com item de outro tipo, booleano como texto (`"false"`), objeto no lugar de valor | Comparação `<`/`>` direto no valor da requisição; `.startsWith`, `len()`, `join` sem checar tipo; coluna booleana recebendo texto | AP11 (500) ou AP08 (Node: exceção em callback derruba o processo) |
| 2 | **Item repetido** numa lista (`[{id:1,qtd:6},{id:1,qtd:6}]`) | Checagem feita item a item contra o estoque/saldo, sem somar por chave | AP24 (estoque negativo) |
| 3 | **Limites**: zero, negativo, fração, vazio, só espaços, texto enorme | Validação só de presença (`if not x`), `x < 0` sem cobrir zero, sem `strip()`, sem tamanho máximo | AP11 (total negativo, estoque fracionado, título em branco) |
| 4 | **Recurso inexistente** em update, delete, mudança de status, chave estrangeira | `UPDATE`/`DELETE` sem conferir linhas afetadas; FK usada sem buscar | AP24 (sucesso falso, órfão) |
| 5 | **Transição inválida** (cancelado → aprovado; finalizado → pendente) | Status atualizado sem olhar o atual; efeito da transição só em `print` | AP25 |
| 6 | **Campo privilegiado** no corpo: `role`, `is_admin`, `tipo`, `active`, `price`, `user_id` de outro | Atribuição direta do corpo ao model | AP06 (atribuição em massa, escalada de privilégio) |
| 7 | **Rota administrativa ou destrutiva** chamada sem credencial | `/admin/*`, `DELETE`, reset, relatórios financeiros sem checagem de identidade | AP06 |
| 8 | **Corpo ausente ou malformado** (sem `Content-Type`, JSON quebrado, corpo vazio) | `request.get_json()` seguido de `.get` sem checar `None`; parser padrão do framework sem handler | AP08 (500, HTML com stack trace) |
| 9 | **Identidade por dado público** (e-mail de outra pessoa no checkout ou login) | Busca de usuário por e-mail seguida de ação em nome dele sem senha/token | AP06 |
| 10 | **Data e fuso**: prazo "hoje", data sem hora comparada com agora em UTC, formatos alternativos | `due_date < utcnow()` com data à meia-noite; parse que aceita formatos diferentes do documentado | AP25/AP11 (atrasada antes do prazo) |
| 11 | **Agregação** que conta estados indevidos ou divide por zero | `SUM` sem filtro de status; `x / total` sem guarda | AP25 (relatório errado) |
| 12 | **Injeção**: apóstrofo e `' OR '1'='1` em campo de texto, busca e login | Concatenação de SQL (AP01) | AP01 |

Como registrar no relatório: na linha de evidência do achado, cite a sonda e o resultado do
baseline ("sonda `qtd-negativa`: 201, estoque 10 → 15"). Se a provocação não foi testada por HTTP,
escreva "confirmado por leitura".
