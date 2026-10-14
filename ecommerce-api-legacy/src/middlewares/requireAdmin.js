const crypto = require('crypto');
const { AppError } = require('./errorHandler');

const digest = (value) => crypto.createHash('sha256').update(value).digest();

// Exige "Authorization: Bearer <ADMIN_TOKEN>". Sem ADMIN_TOKEN configurado, a rota fica fechada.
function requireAdmin(adminToken) {
    return (req, res, next) => {
        if (!adminToken) return next(new AppError('Acesso negado', 403));
        const header = req.get('Authorization') || '';
        const given = header.startsWith('Bearer ') ? header.slice('Bearer '.length) : '';
        if (!crypto.timingSafeEqual(digest(given), digest(adminToken))) {
            return next(new AppError('Não autorizado', 401));
        }
        return next();
    };
}

module.exports = { requireAdmin };
