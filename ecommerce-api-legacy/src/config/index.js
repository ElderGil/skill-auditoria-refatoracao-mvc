// Toda configuração vem do ambiente. Segredos não têm valor padrão.
module.exports = {
    port: Number(process.env.PORT) || 3000,
    dbFile: process.env.DB_FILE || ':memory:',
    adminToken: process.env.ADMIN_TOKEN || '',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    logLevel: process.env.LOG_LEVEL || 'info',
};
