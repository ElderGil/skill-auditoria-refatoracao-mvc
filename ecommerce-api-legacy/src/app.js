const config = require('./config');
const { openDatabase } = require('./database/connection');
const { initializeDatabase } = require('./database/seed');
const { createApp } = require('./createApp');
const { createLogger } = require('./utils/logger');

async function main() {
    const logger = createLogger(config.logLevel);
    const db = openDatabase(config.dbFile);
    await initializeDatabase(db);

    if (!config.adminToken) logger.warn('ADMIN_TOKEN não definido: rotas administrativas responderão 403.');
    if (!config.paymentGatewayKey) logger.warn('PAYMENT_GATEWAY_KEY não definido: gateway em modo simulado.');

    const app = createApp({ config, db, logger });
    app.listen(config.port, () => {
        logger.info(`LMS API rodando na porta ${config.port}`);
    });
}

main().catch((error) => {
    process.stderr.write(`Falha ao iniciar: ${error.message}\n`);
    process.exit(1);
});
