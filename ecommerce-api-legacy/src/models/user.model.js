const { hashPassword, verifyPassword } = require('../utils/password');

class UserModel {
    constructor(db) {
        this.db = db;
    }

    static passwordMatches(user, plainPassword) {
        return verifyPassword(plainPassword, user.pass);
    }

    findByEmail(email) {
        return this.db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
    }

    async create({ name, email, password }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, hashPassword(password)],
        );
        return lastID;
    }

    async delete(id) {
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return changes > 0;
    }
}

module.exports = { UserModel };
