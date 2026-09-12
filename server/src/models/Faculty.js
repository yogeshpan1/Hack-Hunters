import mongoose from "mongoose";

const facultySchema = new mongoose.Schema({
  staffNumber: { type: String },
  name: { type: String, required: true },
  email: { type: String },
});

export default mongoose.model("Faculty", facultySchema);
