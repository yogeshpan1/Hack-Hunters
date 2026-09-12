import TimetableSession from "../models/TimetableSession.js";

const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

export async function getTimetableForClashDetection() {
  const sessions = await TimetableSession.find()
    .populate("module")
    .populate("faculty")
    .populate("cohort")
    .populate("room")
    .populate("timeSlot")
    .lean();

  const entries = sessions.map((session) => ({
    session_id: session._id.toString(),

    module_id: session.module._id.toString(),
    module_code: session.module.moduleCode,
    module_name: session.module.moduleName,

    faculty_id: session.faculty._id.toString(),
    faculty_name: session.faculty.name,

    cohort_id: session.cohort._id.toString(),
    cohort_name: session.cohort.cohortName,
    cohort_size: session.cohort.size,

    room_id: session.room._id.toString(),
    room_name: session.room.roomName,
    room_code: session.room.roomCode,
    block_name: session.room.block,
    room_capacity: session.room.capacity,

    time_slot_id: session.timeSlot._id.toString(),
    day_of_week: session.timeSlot.dayOfWeek,
    start_time: session.timeSlot.startTime,
    end_time: session.timeSlot.endTime,

    session_type: session.sessionType,
  }));

  entries.sort((a, b) => {
    const dayDiff = DAY_ORDER.indexOf(a.day_of_week) - DAY_ORDER.indexOf(b.day_of_week);

    if (dayDiff !== 0) {
      return dayDiff;
    }

    return a.start_time.localeCompare(b.start_time);
  });

  return entries;
}
