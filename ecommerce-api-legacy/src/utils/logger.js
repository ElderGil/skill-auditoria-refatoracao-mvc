// Logger mínimo com nível. Nunca receba cartão, senha, token ou chave aqui.
const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;
    const write = (name, stream) => (message) => {
        if (LEVELS[name] > threshold) return;
        stream.write(`${new Date().toISOString()} ${name.toUpperCase()} ${message}\n`);
    };
    return {
        error: write('error', process.stderr),
        warn: write('warn', process.stderr),
        info: write('info', process.stdout),
        debug: write('debug', process.stdout),
    };
}

module.exports = { createLogger };
