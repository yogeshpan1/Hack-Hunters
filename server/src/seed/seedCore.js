/**
 * Seeds the core demo data (mirrors the old rte_system MySQL dump) into MongoDB:
 * programmes, cohorts, rooms, faculty, modules, time slots, timetable sessions,
 * and the original 5 sample students.
 *
 * Safe to re-run: skips entirely if programmes already exist.
 *
 * Usage: npm run seed:core   (from server/)
 */

import "dotenv/config";
import { connectDB } from "../db.js";
import mongoose from "mongoose";

import Programme from "../models/Programme.js";
import Cohort from "../models/Cohort.js";
import Room from "../models/Room.js";
import Faculty from "../models/Faculty.js";
import Module from "../models/Module.js";
import TimeSlot from "../models/TimeSlot.js";
import TimetableSession from "../models/TimetableSession.js";
import Student from "../models/Student.js";
import ClassAllocation from "../models/ClassAllocation.js";
import { loadRoomList } from "../utils/blockMap.js";

async function seed() {
  await connectDB();

  const existing = await Programme.countDocuments();

  if (existing > 0) {
    console.log("Core data already seeded. Skipping (nothing was changed). Pass --force to wipe and reseed.");

    if (!process.argv.includes("--force")) {
      await mongoose.disconnect();
      return;
    }

    console.log("--force passed: wiping existing core + allocation data...");
    await Promise.all([
      Programme.deleteMany({}),
      Cohort.deleteMany({}),
      Room.deleteMany({}),
      Faculty.deleteMany({}),
      Module.deleteMany({}),
      TimeSlot.deleteMany({}),
      TimetableSession.deleteMany({}),
      ClassAllocation.deleteMany({}),
    ]);
    // The 5 sample students (tied to the real cohorts) are removed and
    // re-inserted below. The 200 DEMO* students' own cohort ("Demo Allocation
    // 2026") was just wiped above too, so they're now orphaned - clear them
    // out; `npm run seed:students` recreates that cohort + students fresh.
    await Student.deleteMany({
      $or: [{ studentNumber: { $regex: /^STU/ } }, { studentNumber: { $regex: /^DEMO/ } }],
    });
  }

  const programmes = await Programme.insertMany([
    { programmeCode: "BSC-COMP", programmeName: "BSc Computing" },
    { programmeCode: "BSC-AI", programmeName: "BSc Artificial Intelligence" },
    { programmeCode: "BSC-CS", programmeName: "BSc Cyber Security" },
  ]);
  const [progComp, progAI, progCS] = programmes;

  const cohorts = await Cohort.insertMany([
    { programme: progComp._id, cohortName: "Computing Year 1", academicYear: "2026", semester: "Semester 1", size: 40 },
    { programme: progComp._id, cohortName: "Computing Year 2", academicYear: "2026", semester: "Semester 1", size: 35 },
    { programme: progComp._id, cohortName: "Computing Year 3", academicYear: "2026", semester: "Semester 1", size: 30 },
    { programme: progAI._id, cohortName: "AI Year 3", academicYear: "2026", semester: "Semester 1", size: 25 },
    { programme: progCS._id, cohortName: "Cyber Security Year 3", academicYear: "2026", semester: "Semester 1", size: 28 },
  ]);
  const [cohortComp1, cohortComp2, cohortComp3, cohortAI3, cohortCS3] = cohorts;

  // Real rooms come straight from Class Details.csv (all 6 blocks: Kumari,
  // London, Alumni, Nepal, Impact, Skill) so every actual campus room shows
  // up as a lane in the Timetable Studio, not just a handful of placeholders.
  const roomList = loadRoomList();
  const rooms = await Room.insertMany(roomList);

  const roomByName = {};
  for (const room of rooms) {
    roomByName[room.roomName] = room;
  }
  const room = (name) => {
    const found = roomByName[name];
    if (!found) throw new Error(`Seed room not found in CSV: ${name}`);
    return found;
  };

  const faculty = await Faculty.insertMany([
    { staffNumber: "FAC001", name: "John Smith", email: "john.smith@islington.edu.np" },
    { staffNumber: "FAC002", name: "Sarah Wilson", email: "sarah.wilson@islington.edu.np" },
    { staffNumber: "FAC003", name: "Michael Brown", email: "michael.brown@islington.edu.np" },
    { staffNumber: "FAC004", name: "David Taylor", email: "david.taylor@islington.edu.np" },
  ]);
  const [facJohn, facSarah, facMichael, facDavid] = faculty;

  const modules = await Module.insertMany([
    { moduleCode: "CS101", moduleName: "Programming", credits: 15 },
    { moduleCode: "CS102", moduleName: "Database Systems", credits: 15 },
    { moduleCode: "CS201", moduleName: "Web Development", credits: 15 },
    { moduleCode: "CS301", moduleName: "Artificial Intelligence", credits: 15 },
    { moduleCode: "CS302", moduleName: "Cyber Security", credits: 15 },
  ]);
  const [modProgramming, modDatabase, modWebDev, modAI, modCyber] = modules;

  const timeSlotDefs = [
    ["Monday", "08:00", "10:00"],
    ["Monday", "10:00", "12:00"],
    ["Monday", "13:00", "15:00"],
    ["Monday", "15:00", "17:00"],
    ["Tuesday", "08:00", "10:00"],
    ["Tuesday", "10:00", "12:00"],
    ["Tuesday", "13:00", "15:00"],
    ["Tuesday", "15:00", "17:00"],
    ["Wednesday", "08:00", "10:00"],
    ["Wednesday", "10:00", "12:00"],
    ["Wednesday", "13:00", "15:00"],
    ["Wednesday", "15:00", "17:00"],
    ["Thursday", "08:00", "10:00"],
    ["Thursday", "10:00", "12:00"],
    ["Thursday", "13:00", "15:00"],
    ["Thursday", "15:00", "17:00"],
    ["Friday", "08:00", "10:00"],
    ["Friday", "10:00", "12:00"],
    ["Friday", "13:00", "15:00"],
    ["Friday", "15:00", "17:00"],
  ];

  const timeSlots = await TimeSlot.insertMany(
    timeSlotDefs.map(([dayOfWeek, startTime, endTime]) => ({ dayOfWeek, startTime, endTime }))
  );
  const ts = (n) => timeSlots[n - 1]; // ts(1)..ts(20), matching the old SQL time_slot_id numbering

  await TimetableSession.insertMany([
    // ---- Original 8 sessions: reproduce the same intentional clashes as before,
    // now placed in real rooms instead of the old "Room A/B/C/Lab 1" placeholders.
    { module: modProgramming._id, faculty: facJohn._id, cohort: cohortComp3._id, room: room("Buckingham Palace")._id, timeSlot: ts(1)._id, sessionType: "LECTURE" },
    { module: modDatabase._id, faculty: facSarah._id, cohort: cohortComp3._id, room: room("Kensington Palace")._id, timeSlot: ts(2)._id, sessionType: "LECTURE" },
    { module: modWebDev._id, faculty: facMichael._id, cohort: cohortComp3._id, room: room("Innovate Tech")._id, timeSlot: ts(3)._id, sessionType: "LAB" },
    { module: modAI._id, faculty: facJohn._id, cohort: cohortAI3._id, room: room("Westminster Palace")._id, timeSlot: ts(6)._id, sessionType: "LECTURE" },
    { module: modCyber._id, faculty: facDavid._id, cohort: cohortCS3._id, room: room("Kensington Palace")._id, timeSlot: ts(5)._id, sessionType: "LECTURE" },
    { module: modDatabase._id, faculty: facSarah._id, cohort: cohortAI3._id, room: room("Buckingham Palace")._id, timeSlot: ts(1)._id, sessionType: "LECTURE" },
    { module: modWebDev._id, faculty: facJohn._id, cohort: cohortAI3._id, room: room("Kensington Palace")._id, timeSlot: ts(1)._id, sessionType: "LECTURE" },
    { module: modAI._id, faculty: facDavid._id, cohort: cohortComp3._id, room: room("Westminster Palace")._id, timeSlot: ts(1)._id, sessionType: "LECTURE" },

    // ---- Extra clash-free sessions spread across the rest of the week and
    // every block, so the Timetable Studio's room lanes aren't nearly empty.
    { module: modProgramming._id, faculty: facSarah._id, cohort: cohortComp1._id, room: room("Kumari Hall 1")._id, timeSlot: ts(4)._id, sessionType: "LECTURE" },
    { module: modCyber._id, faculty: facMichael._id, cohort: cohortComp2._id, room: room("Tridev Gurung")._id, timeSlot: ts(7)._id, sessionType: "LECTURE" },
    { module: modDatabase._id, faculty: facDavid._id, cohort: cohortCS3._id, room: room("Tower Bridge")._id, timeSlot: ts(8)._id, sessionType: "LECTURE" },
    { module: modWebDev._id, faculty: facJohn._id, cohort: cohortComp1._id, room: room("Kantipur")._id, timeSlot: ts(9)._id, sessionType: "LECTURE" },
    { module: modAI._id, faculty: facSarah._id, cohort: cohortAI3._id, room: room("mySecondTeacher")._id, timeSlot: ts(10)._id, sessionType: "LAB" },
    { module: modProgramming._id, faculty: facMichael._id, cohort: cohortComp2._id, room: room("Prashraya Thapa")._id, timeSlot: ts(11)._id, sessionType: "LECTURE" },
    { module: modCyber._id, faculty: facDavid._id, cohort: cohortComp1._id, room: room("Sarad Paudel")._id, timeSlot: ts(12)._id, sessionType: "LECTURE" },
    { module: modDatabase._id, faculty: facJohn._id, cohort: cohortCS3._id, room: room("Naresh Lamgade")._id, timeSlot: ts(13)._id, sessionType: "LECTURE" },
    { module: modWebDev._id, faculty: facSarah._id, cohort: cohortComp3._id, room: room("Piccadilly Circus")._id, timeSlot: ts(14)._id, sessionType: "LAB" },
    { module: modAI._id, faculty: facMichael._id, cohort: cohortAI3._id, room: room("Lumbini")._id, timeSlot: ts(15)._id, sessionType: "LECTURE" },
    { module: modProgramming._id, faculty: facDavid._id, cohort: cohortComp2._id, room: room("ING Arc")._id, timeSlot: ts(16)._id, sessionType: "LAB" },
    { module: modCyber._id, faculty: facJohn._id, cohort: cohortCS3._id, room: room("Sushant Hona")._id, timeSlot: ts(17)._id, sessionType: "LAB" },
  ]);

  await Student.insertMany([
    { studentNumber: "STU001", firstName: "John", lastName: "Doe", cohort: cohortComp3._id },
    { studentNumber: "STU002", firstName: "Jane", lastName: "Smith", cohort: cohortComp3._id },
    { studentNumber: "STU003", firstName: "Alex", lastName: "Brown", cohort: cohortComp3._id },
    { studentNumber: "STU004", firstName: "Sam", lastName: "Wilson", cohort: cohortComp3._id },
    { studentNumber: "STU005", firstName: "David", lastName: "Taylor", cohort: cohortAI3._id },
  ]);

  console.log(
    `Core data seeded: 3 programmes, 5 cohorts, ${rooms.length} rooms (from Class Details.csv), ` +
      "4 faculty, 5 modules, 20 time slots, 20 timetable sessions, 5 students."
  );

  await mongoose.disconnect();
}

seed().catch((error) => {
  console.error("Seeding failed:", error);
  process.exit(1);
});
