# Guidelines de arquitetura — MVC alvo (Fase 3)

Regras do padrão alvo, válidas para qualquer stack. O desenho concreto (pastas, nomes, comandos)
está em `stacks/<stack>.md`; leia **só** o da stack detectada na Fase 1.

## Camadas e responsabilidades

Numa API, a "View" é a camada HTTP: rota + formato da resposta. Por isso o enunciado chama de
"Views/Routes".

| Camada | Responsabilidade | Pode depender de | Não pode |
|---|---|---|---|
| **Config** | Ler ambiente (porta, banco, segredos, CORS, flags). Valores padrão só para desenvolvimento e nunca para segredo | nada do app | conter segredo literal |
| **Models** | Dados e regra de uma entidade: persistência (queries parametrizadas ou ORM), invariantes (`quantidade > 0`), comportamento de domínio (`is_overdue`, transições de status), serialização segura (`to_dict` sem senha) | banco, config | importar framework web, ler `request`, montar resposta HTTP |
| **Controllers** | Fluxo da aplicação: valida a entrada, orquestra models e serviços, define a fronteira da transação, decide o resultado ou lança erro de aplicação | models, services, validadores | ler `request`/`res` direto, montar HTML/JSON de resposta, ter SQL |
| **Views / Routes** | Mapear método + caminho para o controller, extrair dados da requisição, aplicar autenticação/autorização da rota, transformar o resultado em resposta (status + corpo) | controllers, middlewares | regra de negócio, SQL, laços de cálculo |
| **Services** (opcional) | Integrações externas atrás de uma interface pequena: pagamento, e-mail, notificação | config | regra de domínio; ser chamado direto pela rota |
| **Middlewares** | Tratamento centralizado de erro, autenticação, CORS configurado, log de requisição | config | regra de negócio |
| **Entry point / composition root** | Criar a app, carregar config, inicializar banco, registrar rotas e middlewares, injetar dependências, subir o servidor | tudo | lógica de negócio |

Regras de dependência (setas só para dentro):

```
entry point → views/routes → controllers → models → banco
                     ↓              ↓
               middlewares      services (interfaces)
config é lido por todos; ninguém importa a camada de cima.
```

## Princípios aplicados

- **Uma entidade, um model; um recurso HTTP, um arquivo de rotas e um controller.** Não junte
  domínios num arquivo só (é o que criou o god file).
- **Dependências injetadas, não globais.** Conexão/sessão de banco e serviços externos chegam pelo
  composition root (parâmetro, factory ou extensão do framework), não por variável global mutada.
- **Erros de aplicação tipados.** O controller lança `ValidationError` (400), `NotFoundError`
  (404), `ConflictError` (409), `ForbiddenError` (403); o middleware central converte em JSON. Erro
  inesperado vira 500 com mensagem genérica e o detalhe vai para o log, não para o cliente.
- **Validação na entrada do controller**, com tipo, limite e formato (ver `hostile-inputs.md`).
  Criar e atualizar usam o mesmo validador.
- **Transação na fronteira do caso de uso.** Operação que escreve em várias tabelas roda numa
  transação aberta pelo controller (ou por um método de model que represente o caso de uso).
- **Nada sensível na saída**: senha, hash, segredo e cartão nunca são serializados nem logados.

## Preservar o contrato (o que não pode mudar)

O objetivo é reestruturar e corrigir, não redesenhar a API. Mantenha:
- **Rotas**: mesmo método e caminho, mesmos parâmetros de rota e de query.
- **Nomes de campo** de entrada e saída, inclusive os ruins (`usr`, `eml`, `c_id`). Registre o nome
  ruim como achado; trocar nome de campo quebra cliente.
- **Envelope da resposta** (`{"dados": ..., "sucesso": true}`, lista crua, texto puro) e status
  codes do caminho feliz.
- **Comando de execução** documentado no projeto (`python app.py`, `npm start`) e a porta padrão.
  A porta passa a vir de `PORT`, com o valor original como padrão.
- **Seed** e dados de exemplo continuam carregando do mesmo jeito.

Mudanças permitidas, sempre ligadas a um achado e declaradas no plano de fumaça (`after` + `note`):
entrada inválida passa de 500/201 para 400; campo sensível some da resposta; rota de execução
arbitrária some (404); rota administrativa/destrutiva passa a exigir credencial (401/403 sem ela);
erro passa de HTML para JSON.

## Segurança mínima sem quebrar o contrato

Quando o projeto não tem autenticação, não invente um sistema de login completo (isso muda todos os
clientes). Aplique o mínimo que fecha o risco e registre o resto como melhoria proposta:
- **Rota que executa SQL/código arbitrário:** remover.
- **Rota administrativa ou destrutiva** (reset, relatório financeiro, exclusão de usuário): exigir
  o cabeçalho `X-Admin-Token` igual à variável `ADMIN_TOKEN`. Sem a variável configurada, a rota
  responde 403 (fechada por padrão). Comparação em tempo constante.
- **Campo privilegiado no corpo** (`role`, `tipo`, `is_admin`): ignorado no cadastro público; só
  alterável por requisição administrativa.
- **Login existente com token falso:** emitir token assinado com a chave da config (ex.:
  `itsdangerous` no Flask, `crypto.createHmac` no Node), mantendo o mesmo campo na resposta.
- **Senha:** hash forte com salt usando o que a stack já traz (Werkzeug `generate_password_hash`;
  Node `crypto.scryptSync` + `timingSafeEqual`). Seed passa a gravar hash; login com as mesmas
  senhas continua funcionando.

## Estrutura alvo por grau de organização

- **Grau A (monólito):** criar a árvore completa do `stacks/<stack>.md`, mover o código por
  domínio e apagar os arquivos antigos que ficaram vazios. O ponto de entrada documentado continua
  existindo (fino, chamando a factory).
- **Grau B (camadas parciais):** manter as pastas que já cumprem papel (`models/`, `routes/`),
  criar as que faltam (`controllers/`, `config`, `middlewares/`, factory), mover regra das rotas
  para controllers/models, usar o que existe e estava morto (método de domínio, helper,
  serviço) ou apagar se não tiver uso. Rotas no blueprint/arquivo errado vão para o lugar certo
  mantendo o caminho.
- **Grau C:** correções pontuais por achado; estrutura só muda onde há achado estrutural.

## Checklist da Fase 3 (o que o enunciado valida)

- [ ] Estrutura de diretórios segue o MVC acima
- [ ] Configuração extraída para módulo de config (sem valor sensível no código)
- [ ] Models abstraem os dados (nenhum SQL fora de models)
- [ ] Views/Routes separadas e finas
- [ ] Controllers concentram o fluxo
- [ ] Error handling centralizado
- [ ] Entry point claro (composition root)
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem (smoke `compare` verde)
