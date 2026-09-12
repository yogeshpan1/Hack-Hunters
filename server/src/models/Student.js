import mongoose from "mongoose";

const studentSchema = new mongoose.Schema({
  studentNumber: { type: String, required: true, unique: true },
  firstName: { type: String, required: true },
  lastName: { type: String, required: true },
  email: { type: String },
  cohort: { type: mongoose.Schema.Types.ObjectId, ref: "Cohort", required: true },
});

export default mongoose.model("Student", studentSchema);
