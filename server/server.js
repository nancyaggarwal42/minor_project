import express from "express";
import bodyParser from "body-parser";
import dotenv from "dotenv";
import cors from "cors";
import fetch from "node-fetch";

dotenv.config();

const app = express();
app.use(bodyParser.json());
app.use(cors());

app.post("/api/grammar", async (req, res) => {
  const { text, language } = req.body || {};
  if (!text) return res.status(400).json({ error: "text required" });

  try {
    // LanguageTool API call
    const apiRes = await fetch(process.env.LT_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.LT_API_KEY}`,
      },
      body: JSON.stringify({
        text,
        language: language === "hindi" ? "hi" : "en",
      }),
    });

    const data = await apiRes.json();

    // Map LanguageTool matches to your format
    const issues = data.matches?.map((m) => ({
      wrong: m.context.text,
      reason: m.message,
    })) || [];

    // For corrected text, apply first replacement or fallback to original text
    const corrected =
      data.matches?.reduce((acc, m) => {
        if (m.replacements?.length) {
          const start = m.offset;
          const end = m.offset + m.length;
          return acc.slice(0, start) + m.replacements[0].value + acc.slice(end);
        }
        return acc;
      }, text) || text;

    res.json({ issues, corrected });
  } catch (err) {
    console.log("Grammar API error:", err);
    res.json({ issues: [], corrected: text });
  }
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () =>
  console.log(`GRAMMAR SERVER RUNNING → http://localhost:${PORT}`)
);