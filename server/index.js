import "dotenv/config";
import express from "express";
import cors from "cors";

import "./src/models/index.js";
import { connectDB } from "./src/db.js";
import apiRouter from "./src/routes/api.js";

const app = express();

app.use(
  cors({
    origin: ["http://localhost:5173", "http://127.0.0.1:5173"],
    credentials: true,
  })
);
app.use(express.json());

app.use("/", apiRouter);

app.use((error, req, res, next) => {
  console.error(error);
  res.status(500).json({ detail: "Internal server error", message: error.message });
});

const PORT = process.env.PORT || 8000;

connectDB()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Nexus RTE API listening on http://127.0.0.1:${PORT}`);
    });
  })
  .catch((error) => {
    console.error("Failed to connect to MongoDB:", error.message);
    process.exit(1);
  });
