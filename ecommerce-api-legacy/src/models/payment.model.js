const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

class PaymentModel {
    constructor(db) {
        this.db = db;
    }

    static countsAsRevenue(status) {
        return status === PAYMENT_STATUS.PAID;
    }

    async create({ enrollmentId, amount, status }) {
        const { lastID } = await this.db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status],
        );
        return lastID;
    }

    async deleteByUser(userId) {
        await this.db.run(
            'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
            [userId],
        );
    }
}

module.exports = { PaymentModel, PAYMENT_STATUS };
