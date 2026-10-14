// Express 4 não repassa rejeição de handler async; sem isso, um erro derruba o processo.
module.exports = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
