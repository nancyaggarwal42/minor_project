// importing express to make routes
const express = require("express");

// Importing controller(logic part)
const {checkGrammar} = require("../controllers/grammarController");

// small router that decides what happens when
const router = express.Router();

// when frontend sends POST request to /api/grammar/check the checkGrammar function will run
router.post("/check", checkGrammar)

module.exports = router