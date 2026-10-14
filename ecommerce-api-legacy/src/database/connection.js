const sqlite3 = require('sqlite3');

// Expõe o sqlite3 com Promise. Com uma conexão só, as transações entram numa fila
// para que duas operações de escrita nunca se intercalem.
function openDatabase(filename) {
    const db = new sqlite3.Database(filename);

    const run = (sql, params = []) => new Promise((resolve, reject) => {
        db.run(sql, params, function onRun(error) {
            if (error) return reject(error);
            return resolve({ lastID: this.lastID, changes: this.changes });
        });
    });

    const get = (sql, params = []) => new Promise((resolve, reject) => {
        db.get(sql, params, (error, row) => (error ? reject(error) : resolve(row)));
    });

    const all = (sql, params = []) => new Promise((resolve, reject) => {
        db.all(sql, params, (error, rows) => (error ? reject(error) : resolve(rows)));
    });

    let queue = Promise.resolve();
    const transaction = (work) => {
        const result = queue.then(async () => {
            await run('BEGIN');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (error) {
                await run('ROLLBACK');
                throw error;
            }
        });
        queue = result.catch(() => {});
        return result;
    };

    const close = () => new Promise((resolve, reject) => {
        db.close((error) => (error ? reject(error) : resolve()));
    });

    return { run, get, all, transaction, close };
}

module.exports = { openDatabase };
