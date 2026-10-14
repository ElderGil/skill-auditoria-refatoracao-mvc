const { AppError } = require('../middlewares/errorHandler');
const { parsePositiveInteger } = require('../utils/validators');

class UserController {
    constructor({ db, users, enrollments, payments, auditLogs }) {
        Object.assign(this, { db, users, enrollments, payments, auditLogs });
    }

    // Remove o usuário com matrículas e pagamentos, sem deixar registros órfãos.
    async remove(idParam) {
        const userId = parsePositiveInteger(idParam);
        if (userId === null) throw new AppError('Usuário não encontrado', 404);

        await this.db.transaction(async () => {
            await this.payments.deleteByUser(userId);
            await this.enrollments.deleteByUser(userId);
            const deleted = await this.users.delete(userId);
            if (!deleted) throw new AppError('Usuário não encontrado', 404);
            await this.auditLogs.record(`Usuário ${userId} removido com matrículas e pagamentos`);
        });
    }
}

module.exports = { UserController };
