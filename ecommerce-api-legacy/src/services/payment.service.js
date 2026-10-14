const { PAYMENT_STATUS } = require('../models/payment.model');

// Gateway simulado: mantém a regra do original (cartão iniciado em 4 é aprovado).
// Uma integração real usaria apiKey; ela nunca é logada.
const APPROVED_CARD_PREFIX = '4';

class PaymentService {
    constructor({ apiKey, logger }) {
        this.apiKey = apiKey;
        this.logger = logger;
    }

    charge({ card, amount }) {
        const status = card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        this.logger.info(`[payment] cobrança de ${amount} no cartão final ${card.slice(-4)}: ${status}`);
        return status;
    }
}

module.exports = { PaymentService };
