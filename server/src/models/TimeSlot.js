import mongoose from "mongoose";

const timeSlotSchema = new mongoose.Schema({
  dayOfWeek: { type: String, required: true },
  startTime: { type: String, required: true }, // "HH:MM"
  endTime: { type: String, required: true },   // "HH:MM"
});

export default mongoose.model("TimeSlot", timeSlotSchema);
