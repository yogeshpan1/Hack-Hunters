import mongoose from "mongoose";

const timetableSessionSchema = new mongoose.Schema({
  module: { type: mongoose.Schema.Types.ObjectId, ref: "Module", required: true },
  faculty: { type: mongoose.Schema.Types.ObjectId, ref: "Faculty", required: true },
  cohort: { type: mongoose.Schema.Types.ObjectId, ref: "Cohort", required: true },
  room: { type: mongoose.Schema.Types.ObjectId, ref: "Room", required: true },
  timeSlot: { type: mongoose.Schema.Types.ObjectId, ref: "TimeSlot", required: true },
  sessionType: { type: String, default: "LECTURE" },
});

export default mongoose.model("TimetableSession", timetableSessionSchema);
