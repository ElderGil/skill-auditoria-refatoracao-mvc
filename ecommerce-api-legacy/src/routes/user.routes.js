const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function userRoutes(userController, requireAdmin) {
    const router = express.Router();

    router.delete('/users/:id', requireAdmin, asyncHandler(async (req, res) => {
        await userController.remove(req.params.id);
        res.send('Usuário deletado, junto com suas matrículas e pagamentos.');
    }));

    return router;
}

module.exports = { userRoutes };
