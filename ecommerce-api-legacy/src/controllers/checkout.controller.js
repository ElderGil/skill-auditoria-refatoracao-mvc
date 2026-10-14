const { AppError } = require('../middlewares/errorHandler');
const { UserModel } = require('../models/user.model');
const { PAYMENT_STATUS } = require('../models/payment.model');
const { validateCheckout } = require('../utils/validators');

class CheckoutController {
    constructor({ db, users, courses, enrollments, payments, auditLogs, paymentService }) {
        Object.assign(this, { db, users, courses, enrollments, payments, auditLogs, paymentService });
    }

    // Recebe o corpo cru da requisição e devolve o id da matrícula criada.
    async checkout(body) {
        const { name, email, password, courseId, card } = validateCheckout(body);

        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new AppError('Curso não encontrado', 404);

        // Conta, matrícula, pagamento e auditoria entram juntos ou nada entra.
        return this.db.transaction(async () => {
            const existingUser = await this.users.findByEmail(email);
            if (existingUser && !UserModel.passwordMatches(existingUser, password)) {
                throw new AppError('Credenciais inválidas', 401);
            }
            if (existingUser && await this.enrollments.exists(existingUser.id, course.id)) {
                throw new AppError('Usuário já matriculado neste curso', 409);
            }

            const status = this.paymentService.charge({ card, amount: course.price });
            if (status !== PAYMENT_STATUS.PAID) throw new AppError('Pagamento recusado', 400);

            const userId = existingUser ? existingUser.id : await this.users.create({ name, email, password });
            const enrollmentId = await this.enrollments.create(userId, course.id);
            await this.payments.create({ enrollmentId, amount: course.price, status });
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);
            return enrollmentId;
        });
    }
}

module.exports = { CheckoutController };
