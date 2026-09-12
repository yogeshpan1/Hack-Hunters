import mongoose from "mongoose";

const cohortSchema = new mongoose.Schema({
  programme: { type: mongoose.Schema.Types.ObjectId, ref: "Programme", required: true },
  cohortName: { type: String, required: true },
  academicYear: { type: String },
  semester: { type: String },
  size: { type: Number, required: true },
});

export default mongoose.model("Cohort", cohortSchema);
