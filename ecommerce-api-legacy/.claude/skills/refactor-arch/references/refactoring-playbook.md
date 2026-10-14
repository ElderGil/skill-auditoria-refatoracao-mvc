# Playbook de refatoração (Fase 3)

Padrões concretos de transformação, cada um com antes/depois. Os exemplos alternam Python e
JavaScript; a ideia vale para qualquer stack (ver `stacks/<stack>.md` para o idioma exato). Cada
anti-pattern do catálogo aponta para um padrão daqui.

## Índice

| ID | Transformação | Resolve |
|---|---|---|
| T1 | [SQL concatenado → query parametrizada](#t1) | AP01 |
| T2 | [Valor fixo no código → módulo de config](#t2) | AP03, AP04, AP10 |
| T3 | [Senha insegura → hash forte e fora da resposta](#t3) | AP05 |
| T4 | [God file → camadas MVC com composition root](#t4) | AP21, AP14 |
| T5 | [Regra no handler → controller e model](#t5) | AP22, AP19, AP12 |
| T6 | [Várias escritas soltas → transação](#t6) | AP23, AP24 |
| T7 | [Entrada crua → validação com 400](#t7) | AP11, AP24 |
| T8 | [try/except espalhado → error handler central](#t8) | AP08 |
| T9 | [Callback hell → async/await](#t9) | AP15 |
| T10 | [N+1 → JOIN ou carregamento antecipado](#t10) | AP17 |
| T11 | [Estado global → dependência injetada](#t11) | AP09 |
| T12 | [API deprecated → equivalente moderno](#t12) | AP16 |
| T13 | [Rota perigosa → removida ou protegida](#t13) | AP02, AP06 |
| T14 | [print e dado sensível → log estruturado e mascarado](#t14) | AP07, AP13 |
| T15 | [Status livre → máquina de estados](#t15) | AP25 |

Ordem de aplicação recomendada: T2 (config) → T4 (esqueleto e composition root) → T11 → T1/T6/T10
(models) → T7/T5 (controllers) → T8 → T13/T3 → T12/T14/T15 → limpeza (AP18/AP20/AP26). Rode o
import/boot da aplicação depois de cada passo grande.

---

## T1 — SQL concatenado → query parametrizada <a id="t1"></a>

```python
# antes
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"

# depois
row = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
rows = db.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params).fetchall()
```
```js
// antes
db.get(`SELECT * FROM users WHERE email = '${email}'`, cb);
// depois
const user = await db.get('SELECT * FROM users WHERE email = ?', [email]);
```
Só o **texto fixo** da query pode ser montado (lista de cláusulas conhecidas); valor do usuário vai
sempre em parâmetro. Nome de coluna/ordenação vindo do cliente passa por lista branca.

## T2 — Valor fixo no código → módulo de config <a id="t2"></a>

```python
# antes
app.config["SECRET_KEY"] = "valor-fixo-no-codigo"
app.config["DEBUG"] = True
CORS(app)
app.run(host="0.0.0.0", port=5000, debug=True)

# depois — src/config/settings.py
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    CORS_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
# src/app.py
app.config.from_object(Config)
if app.config["CORS_ORIGINS"]:
    CORS(app, origins=app.config["CORS_ORIGINS"])
```
```js
// antes
const config = { dbPass: "senha_prod", paymentGatewayKey: "pk_live_...", port: 3000 };
// depois — src/config/index.js
module.exports = {
  port: Number(process.env.PORT) || 3000,
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
};
```
Crie `.env.example` com os nomes das variáveis e valores vazios ou de exemplo inofensivo. Segredo
nunca tem valor padrão literal. Endpoint que devolvia segredo/config (`/health` com `secret_key`)
passa a devolver só o status.

## T3 — Senha insegura → hash forte e fora da resposta <a id="t3"></a>

```python
# antes
self.password = hashlib.md5(pwd.encode()).hexdigest()
def to_dict(self): return {"id": self.id, "email": self.email, "password": self.password}

# depois
from werkzeug.security import generate_password_hash, check_password_hash
def set_password(self, pwd): self.password = generate_password_hash(pwd)
def check_password(self, pwd): return check_password_hash(self.password, pwd)
def to_dict(self): return {"id": self.id, "email": self.email}
```
```js
// antes
function badCrypto(pwd) { /* base64 repetido e truncado */ }
// depois
const { hashPassword, verifyPassword } = require('../utils/password'); // scrypt + salt (stacks/express.md)
```
Login com SQL de senha (`... AND senha = ?`) vira: buscar por e-mail, depois `check_password`. O
seed passa a gravar hash; as senhas de exemplo continuam valendo para login.

## T4 — God file → camadas MVC com composition root <a id="t4"></a>

```js
// antes — AppManager.js: abre o banco, faz seed, registra rotas e implementa a regra
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + INSERT */ }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { /* 50 linhas aninhadas */ }); }
}

// depois — src/createApp.js (composition root)
function createApp({ config, db }) {
  const users = new UserModel(db);
  const courses = new CourseModel(db);
  const enrollments = new EnrollmentModel(db);
  const payment = new PaymentService(config);
  const checkout = new CheckoutController({ db, users, courses, enrollments, payment });

  const app = express();
  app.use(express.json());
  app.use('/api', checkoutRoutes(checkout));
  app.use('/api', adminRoutes(new ReportController({ courses, enrollments }), config));
  app.use(errorHandler);
  return app;
}
```
```python
# antes — app.py com rotas, SQL inline e config; controllers.py e models.py com 4 domínios cada
# depois — src/app.py
def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    database.init_app(app)
    for bp in (produto_routes.bp, usuario_routes.bp, pedido_routes.bp, relatorio_routes.bp):
        app.register_blueprint(bp)
    register_error_handlers(app)
    return app
```
Um arquivo por entidade em models, por recurso em controllers e views. Apague os arquivos antigos
quando ficarem vazios; não deixe "módulo de compatibilidade" importando tudo.

## T5 — Regra no handler → controller e model <a id="t5"></a>

```python
# antes — a mesma regra copiada em 5 rotas
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
# ...

# depois — no model, uma vez
class Task(db.Model):
    def is_overdue(self, now=None):
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        return bool(self.due_date and self.due_date < now and self.status not in ("done", "cancelled"))
# na serialização
data["overdue"] = task.is_overdue()
```
```python
# antes — controller faz tudo e "notifica" com print
resultado = models.criar_pedido(usuario_id, itens)
print("ENVIANDO EMAIL: Pedido criado")
# depois — controller orquestra; notificação é serviço injetado
pedido = self.pedidos.criar(usuario_id, itens)        # model valida e grava (T6)
self.notifier.pedido_criado(pedido)                  # services/notification_service.py
return pedido
```
Helper que já existia e era ignorado (ex.: `calculate_percentage`, `process_task_data`) passa a ser
usado ou é apagado; não deixe duas versões.

## T6 — Várias escritas soltas → transação <a id="t6"></a>

```python
# antes — pedido, itens e estoque em comandos soltos; checagem item a item
for item in itens:
    if produto["estoque"] < item["quantidade"]: return {"erro": "..."}
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("UPDATE produtos SET estoque = estoque - " + str(item["quantidade"]) + ...)
db.commit()

# depois — soma por produto e tudo numa transação
from collections import Counter
qtd = Counter()
for item in itens:
    qtd[item["produto_id"]] += item["quantidade"]
with db:  # sqlite3: commit no fim, rollback em exceção
    for produto_id, total in qtd.items():
        cur = db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                         (total, produto_id, total))
        if cur.rowcount == 0:
            raise AppError(f"Estoque insuficiente para o produto {produto_id}")
    pedido_id = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
                           (usuario_id, total_pedido)).lastrowid
    db.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", linhas)
```
```js
// depois — Node, com o helper transaction (stacks/express.md)
const enrollmentId = await db.transaction(async () => {
  const { lastID } = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
  await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [lastID, price, 'PAID']);
  await db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [`checkout ${courseId}`]);
  return lastID;
});
```
O `UPDATE ... AND estoque >= ?` também fecha a corrida entre duas compras simultâneas. Exclusão com
dependentes: apague os dependentes na mesma transação ou recuse com 409; responda 404 quando nada
foi afetado.

## T7 — Entrada crua → validação com 400 <a id="t7"></a>

```python
# antes
preco = dados["preco"]
if preco < 0: ...                       # "abc" < 0 → TypeError → 500
if data['priority'] < 1 or data['priority'] > 5: ...

# depois — utils/validators.py, usado por criar e atualizar
def require_number(data, field, *, minimum=None, integer=False, required=True):
    value = data.get(field)
    if value is None:
        if required:
            raise AppError(f"{field} é obrigatório")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and not float(value).is_integer()):
        raise AppError(f"{field} deve ser {'inteiro' if integer else 'numérico'}")
    if minimum is not None and value < minimum:
        raise AppError(f"{field} deve ser >= {minimum}")
    return int(value) if integer else value

def require_text(data, field, *, min_len=1, max_len=200, required=True):
    value = data.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AppError(f"{field} é obrigatório")
    value = value.strip()
    if not (min_len <= len(value) <= max_len):
        raise AppError(f"{field} deve ter entre {min_len} e {max_len} caracteres")
    return value
```
```js
// antes
if (!u || !e || !cid || !cc) return res.status(400).send('Bad Request');
let status = cc.startsWith('4') ? 'PAID' : 'DENIED';  // cc numérico → TypeError → processo cai
// depois
const isText = (v) => typeof v === 'string' && v.trim() !== '';
if (![usr, eml, card].every(isText) || !Number.isInteger(Number(c_id))) throw new AppError('Bad Request', 400);
```
Quantidade: inteiro > 0. Valores monetários: número ≥ 0. Listas: tipo de cada item. Mensagem e
status de validação seguem o padrão que o projeto já usa.

## T8 — try/except espalhado → error handler central <a id="t8"></a>

```python
# antes — repetido em 17 funções
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500

# depois — controller lança, middleware traduz (stacks/flask.md)
def buscar_produto(id):
    produto = Produto.buscar(id)
    if produto is None:
        raise AppError("Produto não encontrado", 404)
    return produto
```
```js
// antes — erro em callback derruba o processo; err ignorado
db.all(sql, [], (err, rows) => { rows.forEach(...) });
// depois
router.get('/admin/financial-report', asyncHandler(async (req, res) => {
  res.json(await reportController.financial());
}));
app.use(errorHandler); // depois de todas as rotas
```
O cliente recebe mensagem genérica para erro inesperado; o detalhe vai para o log.

## T9 — Callback hell → async/await <a id="t9"></a>

```js
// antes
this.db.get(sqlCurso, [cid], (err, course) => {
  this.db.get(sqlUser, [e], (err, user) => {
    this.db.run(sqlEnroll, [userId, cid], function (err) {
      self.db.run(sqlPay, [this.lastID, course.price], function (err) { /* ... */ });
    });
  });
});

// depois
async checkout({ name, email, password, courseId, card }) {
  const course = await this.courses.findActive(courseId);
  if (!course) throw new AppError('Curso não encontrado', 404);
  const user = await this.users.findOrCreate({ name, email, password });
  if (!this.payment.charge({ card, amount: course.price })) throw new AppError('Pagamento recusado', 400);
  return this.enrollments.enrollWithPayment(user.id, course); // transação (T6)
}
```

## T10 — N+1 → JOIN ou carregamento antecipado <a id="t10"></a>

```python
# antes — uma query por pedido e outra por item
for row in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()

# depois — uma query para todos os itens
rows = db.execute("""
    SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario,
           COALESCE(p.nome, 'Desconhecido') AS produto_nome
    FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id
    WHERE i.pedido_id IN (SELECT id FROM pedidos)""").fetchall()
```
```python
# ORM: antes — User.query.get(t.user_id) dentro do laço
# depois
from sqlalchemy.orm import selectinload
tasks = db.session.execute(
    db.select(Task).options(selectinload(Task.user), selectinload(Task.category))).scalars().all()
```
Contagens por grupo usam `GROUP BY` em vez de uma `count()` por status/usuário.

## T11 — Estado global → dependência injetada <a id="t11"></a>

```python
# antes
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)

# depois — conexão por requisição no contexto da app (stacks/flask.md)
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
    return g.db
```
```js
// antes — utils.js exporta objetos mutáveis
let globalCache = {}; let totalRevenue = 0;
// depois — quem precisa recebe pelo construtor (composition root); cache, se necessário, tem limite
class CheckoutController { constructor({ db, users, courses, payment }) { /* ... */ } }
```

## T12 — API deprecated → equivalente moderno <a id="t12"></a>

```python
# antes
from datetime import datetime
created_at = db.Column(db.DateTime, default=datetime.utcnow)
task = Task.query.get(task_id)
tasks = Task.query.filter_by(status="done").all()

# depois
from datetime import datetime, timezone
def utcnow():  # naive em UTC, compatível com as colunas existentes
    return datetime.now(timezone.utc).replace(tzinfo=None)
created_at = db.Column(db.DateTime, default=utcnow)
task = db.session.get(Task, task_id)
tasks = db.session.execute(db.select(Task).filter_by(status="done")).scalars().all()
```
```js
// antes
const buf = new Buffer(data); app.del('/x', h); res.send(404);
// depois
const buf = Buffer.from(data); app.delete('/x', h); res.sendStatus(404);
```
Mantenha o formato de data que a API já devolve (ex.: `str(datetime)` sem fuso) para não quebrar o
contrato. Consulte a tabela do AP16 e, se disponível, a documentação via Context7.

## T13 — Rota perigosa → removida ou protegida <a id="t13"></a>

```python
# antes
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])

# depois — removida (não há versão segura de "execute este SQL")

# antes
@app.route("/admin/reset-db", methods=["POST"])
def reset_database(): ...

# depois — src/middlewares/auth.py
def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        given = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(given, expected):
            raise AppError("Acesso negado", 403)
        return view(*args, **kwargs)
    return wrapper
```
```python
# antes — atribuição em massa
user.role = data.get("role", "user")
# depois — cadastro público sempre cria papel padrão; troca de papel só via rota administrativa
user.role = "user"
```
Ver `mvc-guidelines.md`, seção "Segurança mínima sem quebrar o contrato".

## T14 — print e dado sensível → log estruturado e mascarado <a id="t14"></a>

```python
# antes
print("Login bem-sucedido: " + email)
# depois
logger = logging.getLogger(__name__)
logger.info("login ok user_id=%s", usuario["id"])
```
```js
// antes
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
// depois
const masked = `**** ${String(card).slice(-4)}`;
console.info(`[payment] cobrança iniciada cartão=${masked}`);   // chave nunca é logada
```

## T15 — Status livre → máquina de estados <a id="t15"></a>

```python
# antes
if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]:
    return erro
db.execute("UPDATE pedidos SET status = '" + novo_status + "' WHERE id = " + str(pedido_id))
print("Pedido cancelado. Devolver estoque.")

# depois — no model do pedido
TRANSICOES = {
    "pendente": {"aprovado", "cancelado"},
    "aprovado": {"enviado", "cancelado"},
    "enviado": {"entregue"},
    "entregue": set(),
    "cancelado": set(),
}
def mudar_status(self, pedido_id, novo):
    pedido = self.buscar(pedido_id)
    if pedido is None:
        raise AppError("Pedido não encontrado", 404)
    if novo not in TRANSICOES.get(pedido["status"], set()):
        raise AppError(f"Transição inválida: {pedido['status']} -> {novo}")
    with self.db:
        self.db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo, pedido_id))
        if novo == "cancelado":
            self.devolver_estoque(pedido_id)
```
Relatórios que somam valores filtram pelos estados que contam (ex.: excluir `cancelado` do
faturamento) e registram a regra no relatório da Fase 2 como mudança intencional.
