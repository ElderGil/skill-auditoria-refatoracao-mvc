const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function reportRoutes(reportController, requireAdmin) {
    const router = express.Router();

    router.get('/admin/financial-report', requireAdmin, asyncHandler(async (req, res) => {
        res.json(await reportController.financial());
    }));

    return router;
}

module.exports = { reportRoutes };
