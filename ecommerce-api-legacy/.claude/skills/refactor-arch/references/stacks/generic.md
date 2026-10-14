# Stack: outras (fallback)

Use quando a stack não for Flask nem Express. As regras de `mvc-guidelines.md` valem do mesmo
jeito; aqui está o mapeamento para o vocabulário de cada ecossistema.

| Ecossistema | Views / Routes | Controllers | Models | Config | Error handling central | Entry point |
|---|---|---|---|---|---|---|
| FastAPI | `APIRouter` por recurso | funções de caso de uso chamadas pelos endpoints | SQLAlchemy/SQLModel + repositório | `pydantic-settings` | `@app.exception_handler` | `main.py` com `create_app()` |
| Django / DRF | `urls.py` + views/viewsets finos | `services.py` por app | `models.py` (ORM) | `settings.py` lendo env | middleware / `EXCEPTION_HANDLER` do DRF | `manage.py` / `wsgi.py` |
| Koa / Fastify | router por recurso / plugin | controllers | repositórios | módulo de config | middleware de erro / `setErrorHandler` | `server.js` |
| NestJS | controllers do Nest (são a camada HTTP) | providers/services | entities + repositories | `ConfigModule` | exception filters | `main.ts` |
| Spring Boot | `@RestController` | `@Service` | `@Entity` + `JpaRepository` | `application.yml` + env | `@ControllerAdvice` | classe `@SpringBootApplication` |
| Go (net/http, Gin) | handlers + router | pacote `service` | pacote `repository` + structs | `os.Getenv` num pacote `config` | middleware de recover | `cmd/<app>/main.go` |

Procedimento:
1. Identifique como o framework registra rotas e onde o banco é aberto (inventário + leitura).
2. Escolha a linha da tabela mais próxima. Se nenhuma servir, aplique as camadas de
   `mvc-guidelines.md` com os nomes de pasta genéricos (`config/`, `models/`, `controllers/`,
   `views/` ou `routes/`, `middlewares/`).
3. Descubra o comando para subir a app numa porta escolhida (variável de ambiente ou argumento) e
   monte o plano de fumaça com ele.
4. Se não houver como validar por HTTP (biblioteca, CLI), diga isso na Fase 1 e valide por import /
   compilação e pelos testes existentes; a Fase 3 não pode declarar sucesso sem alguma execução.
