// it is usewd to create backend server
const express = require("express");
// with the help of cors we can talk with our frontend
const cors = require("cors");
// helps backend in reading json data sent by frontend
const bodyparser = require("body-parser");
// will import routes
const grammarRoutes = require('./routes/grammarRoutes')

const app = express();

const PORT = 5000;

// we will enable cors and json parsing in our backend
app.use(cors());
app.use(bodyparser.json());

// by this we tell express - to use grammar routes for all urls starting with the route
app.use("/app/grammar", grammarRoutes);

// start's backend
app.listen(PORT, () => {
    console.log('server running ${PORT}')
})