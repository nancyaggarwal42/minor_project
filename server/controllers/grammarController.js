// main function
exports.checkGrammar = async(req, res) => {
    try{
        // basically req.data is frontend text
        const {text} = req.body;

        // if empty text
        if(!text || text.trim() === '') {
            return res.json({
                message: "Please type anything",
                wrongTexts: [],
                correctText: "",
            });
        }

        // variable for wrong text
        let wrongTexts = [];

        // variable for correct version of text
        let corrected = text;

        // ex 1
        if(text.includes("teh")){
            wrongTexts.push("wrong text - teaching: 'teh' should be 'the'");
            corrected = text.replace(/teh/g, "the");
        }

        // ex 2
        if(text.includes("dont")){
            wrongTexts.push("wrong text - teaching: 'dont' should be 'don't'");
             corrected = text.replace(/dont/g, "don't");
        }

        // no wrong words
        if(wrongTexts.length === 0){
            return res.json({
                message: 'All good!',
                wrongTexts: [],
                correctText: text,
            })
        }

        return res.json({
            message: 'Corrections found',
            wrongTexts,
            correctText: corrected
        })
    }
    catch(error){
        console.log("Error checking grammar:", error);
        res.status(500).json({message: "Server error"})
    }
}