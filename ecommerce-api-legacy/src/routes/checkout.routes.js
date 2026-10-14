const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function checkoutRoutes(checkoutController) {
    const router = express.Router();

    router.post('/checkout', asyncHandler(async (req, res) => {
        const enrollmentId = await checkoutController.checkout(req.body);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    }));

    return router;
}

module.exports = { checkoutRoutes };
