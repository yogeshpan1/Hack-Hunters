import mongoose from "mongoose";

const roomSchema = new mongoose.Schema({
  roomName: { type: String, required: true },
  roomCode: { type: String },   // e.g. "TR-14", "LAB-01", from Class Details.csv
  block: { type: String },      // e.g. "Skill", "London", "Kumari", from Class Details.csv
  building: { type: String },
  capacity: { type: Number, required: true },
  roomType: { type: String },
});

export default mongoose.model("Room", roomSchema);
