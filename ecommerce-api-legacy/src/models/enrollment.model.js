class EnrollmentModel {
    constructor(db) {
        this.db = db;
    }

    async exists(userId, courseId) {
        const row = await this.db.get(
            'SELECT 1 AS found FROM enrollments WHERE user_id = ? AND course_id = ?',
            [userId, courseId],
        );
        return Boolean(row);
    }

    async create(userId, courseId) {
        const { lastID } = await this.db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId],
        );
        return lastID;
    }

    async deleteByUser(userId) {
        await this.db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
    }
}

module.exports = { EnrollmentModel };
