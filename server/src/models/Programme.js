import mongoose from "mongoose";

const programmeSchema = new mongoose.Schema({
  programmeCode: { type: String, required: true, unique: true },
  programmeName: { type: String, required: true },
});

export default mongoose.model("Programme", programmeSchema);
