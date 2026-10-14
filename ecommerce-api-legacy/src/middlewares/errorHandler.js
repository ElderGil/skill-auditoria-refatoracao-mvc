class AppError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.status = status;
    }
}

// O contrato original responde erros em texto puro; o handler mantém esse formato.
function createErrorHandler(logger) {
    // eslint-disable-next-line no-unused-vars
    return function errorHandler(error, req, res, next) {
        if (error.type === 'entity.parse.failed') return res.status(400).send('Bad Request');
        if (error instanceof AppError) return res.status(error.status).send(error.message);
        if (error.status >= 400 && error.status < 500) return res.status(error.status).send('Bad Request');
        logger.error(`${req.method} ${req.path} falhou: ${error.message}`);
        return res.status(500).send('Erro interno');
    };
}

module.exports = { AppError, createErrorHandler };
