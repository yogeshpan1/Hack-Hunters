import mongoose from "mongoose";

const moduleSchema = new mongoose.Schema({
  moduleCode: { type: String, required: true, unique: true },
  moduleName: { type: String, required: true },
  credits: { type: Number },
});

export default mongoose.model("Module", moduleSchema);
