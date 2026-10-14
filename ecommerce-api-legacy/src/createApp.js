const express = require('express');
const { UserModel } = require('./models/user.model');
const { CourseModel } = require('./models/course.model');
const { EnrollmentModel } = require('./models/enrollment.model');
const { PaymentModel } = require('./models/payment.model');
const { AuditLogModel } = require('./models/auditLog.model');
const { PaymentService } = require('./services/payment.service');
const { CheckoutController } = require('./controllers/checkout.controller');
const { ReportController } = require('./controllers/report.controller');
const { UserController } = require('./controllers/user.controller');
const { checkoutRoutes } = require('./routes/checkout.routes');
const { reportRoutes } = require('./routes/report.routes');
const { userRoutes } = require('./routes/user.routes');
const { requireAdmin } = require('./middlewares/requireAdmin');
const { createErrorHandler } = require('./middlewares/errorHandler');

// Composition root: cria as dependências uma vez e injeta em quem precisa.
function createApp({ config, db, logger }) {
    const users = new UserModel(db);
    const courses = new CourseModel(db);
    const enrollments = new EnrollmentModel(db);
    const payments = new PaymentModel(db);
    const auditLogs = new AuditLogModel(db);
    const paymentService = new PaymentService({ apiKey: config.paymentGatewayKey, logger });

    const checkoutController = new CheckoutController({
        db, users, courses, enrollments, payments, auditLogs, paymentService,
    });
    const reportController = new ReportController({ courses });
    const userController = new UserController({ db, users, enrollments, payments, auditLogs });
    const adminOnly = requireAdmin(config.adminToken);

    const app = express();
    app.disable('x-powered-by');
    app.use(express.json());
    app.use('/api', checkoutRoutes(checkoutController));
    app.use('/api', reportRoutes(reportController, adminOnly));
    app.use('/api', userRoutes(userController, adminOnly));
    app.use(createErrorHandler(logger));
    return app;
}

module.exports = { createApp };
