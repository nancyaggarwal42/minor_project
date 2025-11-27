// import express from "express";
// import bodyParser from "body-parser";
// import dotenv from "dotenv";
// import cors from "cors";
// import fetch from "node-fetch";

// dotenv.config();

// const app = express();
// app.use(bodyParser.json());
// app.use(cors());

// app.post("/api/grammar", async (req, res) => {
//   const { text, language } = req.body || {};
//   if (!text) return res.status(400).json({ error: "text required" });

//   try {
//     // LanguageTool API call
//     const apiRes = await fetch(process.env.LT_API_URL, {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//         "Authorization": `Bearer ${process.env.LT_API_KEY}`,
//       },
//       body: JSON.stringify({
//         text,
//         language: language === "hindi" ? "hi" : "en",
//       }),
//     });

//     const data = await apiRes.json();

//     // Map LanguageTool matches to your format
//     const issues = data.matches?.map((m) => ({
//       wrong: m.context.text,
//       reason: m.message,
//     })) || [];

//     // For corrected text, apply first replacement or fallback to original text
//     const corrected =
//       data.matches?.reduce((acc, m) => {
//         if (m.replacements?.length) {
//           const start = m.offset;
//           const end = m.offset + m.length;
//           return acc.slice(0, start) + m.replacements[0].value + acc.slice(end);
//         }
//         return acc;
//       }, text) || text;

//     res.json({ issues, corrected });
//   } catch (err) {
//     console.log("Grammar API error:", err);
//     res.json({ issues: [], corrected: text });
//   }
// });

// const PORT = process.env.PORT || 4000;
// app.listen(PORT, () =>
//   console.log(`GRAMMAR SERVER RUNNING → http://localhost:${PORT}`)
// );

import express from "express";
import bodyParser from "body-parser";
import dotenv from "dotenv";
import cors from "cors";
import { GoogleGenerativeAI } from "@google/generative-ai";

dotenv.config();

const app = express();
app.use(bodyParser.json());
app.use(cors());

// --- DEBUG: Check API Key Status ---
const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
    console.error("CRITICAL ERROR: GEMINI_API_KEY is not defined. Please check your .env file.");
} else {
    // Note: Do not log the full key. Just confirmation of loading.
    console.log("INFO: GEMINI_API_KEY loaded successfully.");
}
// -----------------------------------

const genAI = new GoogleGenerativeAI(apiKey);

app.post("/api/grammar", async (req, res) => {
  const { text } = req.body;

  if (!text) return res.status(400).json({ error: "Text required" });

  // 1. Define the required JSON structure (Response Schema)
  const responseSchema = {
    type: "OBJECT",
    properties: {
      corrected: { type: "STRING", description: "The corrected version of the input text." },
      issues: {
        type: "ARRAY",
        description: "A list of grammar mistakes found in the original text.",
        items: {
          type: "OBJECT",
          properties: {
            wrong: { type: "STRING", description: "The incorrect part of the original text." },
            reason: { type: "STRING", description: "The grammatical reason for the mistake." }
          }
        }
      }
    },
    required: ["corrected", "issues"]
  };

  try {
    // Model name is correct: gemini-2.5-flash
    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

    // 2. Define a simple, concise prompt
    const prompt = `You are a grammar correction assistant. Correct the following text and list the grammar mistakes according to the provided JSON schema. Text to correct: "${text}"`;

    // 3. Use the correct SDK structure: prompt in contents array, config under generationConfig
    const result = await model.generateContent({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: responseSchema,
      },
    });
    
    // 4. FIX: Use robust optional chaining to safely extract the text property.
    // This prevents the "trim is not a function" error if the text property is missing.
    const responseText = result.response.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!responseText) {
        // If the model returned no text (e.g., due to safety settings), throw an error 
        // to fall into the catch block and use the robust error handling there.
        throw new Error("Model returned empty or malformed text content (responseText is null).");
    }

    let json;
    
    try {
      json = JSON.parse(responseText.trim()); 
    } catch (e) {
      console.error("Could not parse JSON from API:", responseText);
      json = { corrected: text, issues: [{ wrong: "N/A", reason: "API response parsing failed. Check model output in logs." }] };
    }

    res.json(json);
    
  } catch (err) {
    console.error("--- GEMINI API FAILURE ---");
    // This often contains the HTTP 401/429 status and the full error message
    console.error("Error Message:", err.message);
    // Attempt to extract the status code if possible for easier diagnosis
    const statusCodeMatch = err.message.match(/\[(\d+) [A-Za-z ]+\]/);
    const statusCode = statusCodeMatch ? statusCodeMatch[1] : 'Unknown';
    console.error("Likely HTTP Status Code:", statusCode);
    console.error("Full Error Stack:", err);
    console.error("----------------------------");

    // Send a more informative error message back to the client
    res.status(500).json({ 
        corrected: text, 
        issues: [{ 
            wrong: "N/A", 
            reason: `Gemini API call failed. Status: ${statusCode}. See server console for details.` 
        }] 
    });
  }
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`SERVER RUNNING → http://localhost:${PORT}`));