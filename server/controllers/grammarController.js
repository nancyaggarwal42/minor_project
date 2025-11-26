import fetch from "node-fetch";
import dotenv from "dotenv";

dotenv.config();

export const checkGrammar = async (req, res) => {
  try {
    const { text, language } = req.body;

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

    const issues = data.matches.map((m) => ({
      wrong: m.context.text,
      reason: m.message,
    }));

    const corrected = data?.replacements?.[0]?.value || "";

    res.json({ issues, corrected });
  } catch (error) {
    console.log(error);
    res.status(500).json({ error: "Grammar API failed" });
  }
};
