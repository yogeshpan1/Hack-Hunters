import mongoose from "mongoose";

const allocatedStudentSchema = new mongoose.Schema(
  {
    student: { type: mongoose.Schema.Types.ObjectId, ref: "Student", required: true },
    emailSent: { type: Boolean, default: false },
    emailSentAt: { type: Date, default: null },
  },
  { _id: false }
);

const classAllocationSchema = new mongoose.Schema({
  className: { type: String, required: true },
  room: { type: mongoose.Schema.Types.ObjectId, ref: "Room", required: true },
  students: [allocatedStudentSchema],
  createdAt: { type: Date, default: Date.now },
});

export default mongoose.model("ClassAllocation", classAllocationSchema);
