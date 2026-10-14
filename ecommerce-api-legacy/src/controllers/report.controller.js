const { PaymentModel } = require('../models/payment.model');

const UNKNOWN_STUDENT = 'Unknown';

class ReportController {
    constructor({ courses }) {
        this.courses = courses;
    }

    // Mesmo formato do original: [{ course, revenue, students: [{ student, paid }] }], em ordem de curso.
    async financial() {
        const rows = await this.courses.listWithEnrollmentsAndPayments();
        const byCourse = new Map();

        for (const row of rows) {
            if (!byCourse.has(row.course_id)) {
                byCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
            }
            if (row.enrollment_id === null) continue;

            const entry = byCourse.get(row.course_id);
            if (PaymentModel.countsAsRevenue(row.payment_status)) entry.revenue += row.payment_amount;
            entry.students.push({
                student: row.student_name ?? UNKNOWN_STUDENT,
                paid: row.payment_amount ?? 0,
            });
        }

        return [...byCourse.values()];
    }
}

module.exports = { ReportController };
