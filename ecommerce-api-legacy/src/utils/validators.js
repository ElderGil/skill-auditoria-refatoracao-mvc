const { AppError } = require('../middlewares/errorHandler');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_PATTERN = /^\d{13,19}$/;

const isPresent = (value) => value !== undefined && value !== null && value !== '';

function requireText(value, field, maxLength) {
    if (typeof value !== 'string' || value.trim() === '') {
        throw new AppError(`${field} deve ser um texto não vazio`, 400);
    }
    const text = value.trim();
    if (text.length > maxLength) {
        throw new AppError(`${field} deve ter no máximo ${maxLength} caracteres`, 400);
    }
    return text;
}

// Aceita número ou texto numérico, como o contrato original aceitava.
function parsePositiveInteger(value) {
    if (typeof value !== 'number' && typeof value !== 'string') return null;
    const text = String(value).trim();
    if (!/^\d+$/.test(text)) return null;
    const number = Number(text);
    return Number.isSafeInteger(number) && number > 0 ? number : null;
}

// Campos do contrato: usr, eml, pwd, c_id, card.
function validateCheckout(body = {}) {
    const { usr, eml, pwd, c_id: courseIdInput, card } = body;
    if (![usr, eml, pwd, courseIdInput, card].every(isPresent)) {
        throw new AppError('Bad Request', 400);
    }

    const name = requireText(usr, 'usr', 120);
    const email = requireText(eml, 'eml', 254).toLowerCase();
    if (!EMAIL_PATTERN.test(email)) throw new AppError('eml deve ser um e-mail válido', 400);
    const password = requireText(pwd, 'pwd', 128);

    const courseId = parsePositiveInteger(courseIdInput);
    if (courseId === null) throw new AppError('c_id deve ser um inteiro positivo', 400);

    if (typeof card !== 'string' || !CARD_PATTERN.test(card.replace(/[\s-]/g, ''))) {
        throw new AppError('card deve ter de 13 a 19 dígitos', 400);
    }

    return { name, email, password, courseId, card: card.replace(/[\s-]/g, '') };
}

module.exports = { validateCheckout, parsePositiveInteger };
