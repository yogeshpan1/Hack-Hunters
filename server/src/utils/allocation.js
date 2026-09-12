import Room from "../models/Room.js";
import Student from "../models/Student.js";
import ClassAllocation from "../models/ClassAllocation.js";

export async function getBlockRooms(blockName) {
  const rooms = await Room.find({ block: blockName }).sort({ roomCode: 1 }).lean();

  return rooms.map((room) => ({
    ...room,
    block_name: room.block,
    room_code: room.roomCode,
  }));
}

export async function getStudentsPool() {
  return Student.find({ email: { $exists: true, $ne: null, $ne: "" } }).lean();
}

function shuffle(array) {
  const result = [...array];

  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }

  return result;
}

function validationError(message) {
  const error = new Error(message);
  error.isValidation = true;
  return error;
}

export async function generateAllocation(numClasses = 7, blockName = "Skill") {
  const students = await getStudentsPool();

  if (students.length === 0) {
    throw validationError("No students with an email address were found to allocate.");
  }

  const blockRooms = await getBlockRooms(blockName);

  if (blockRooms.length < numClasses) {
    throw validationError(
      `The '${blockName}' block only has ${blockRooms.length} room(s), need at least ${numClasses}.`
    );
  }

  const chosenRooms = blockRooms.slice(0, numClasses);

  const shuffled = shuffle(students);
  const total = shuffled.length;
  const base = Math.floor(total / numClasses);
  const remainder = total % numClasses;

  const chunks = [];
  let cursor = 0;

  for (let i = 0; i < numClasses; i++) {
    const size = base + (i < remainder ? 1 : 0);
    chunks.push(shuffled.slice(cursor, cursor + size));
    cursor += size;
  }

  chosenRooms.forEach((room, index) => {
    const chunk = chunks[index];

    if (chunk.length > room.capacity) {
      throw validationError(
        `Room '${room.roomName}' has capacity ${room.capacity}, but ${chunk.length} students were assigned to it. ` +
          "Add more/larger rooms to the block, or reduce the student pool."
      );
    }
  });

  // Wipe any previous allocation so this action is safe to re-run.
  await ClassAllocation.deleteMany({});

  const docs = chosenRooms.map((room, index) => ({
    className: `Class ${index + 1}`,
    room: room._id,
    students: chunks[index].map((student) => ({
      student: student._id,
      emailSent: false,
      emailSentAt: null,
    })),
  }));

  await ClassAllocation.insertMany(docs);

  return getClassesWithStudents();
}

export async function getClassesWithStudents() {
  const classes = await ClassAllocation.find()
    .sort({ createdAt: 1 })
    .populate("room")
    .populate("students.student")
    .lean();

  return classes.map((classInfo) => {
    const students = classInfo.students
      .filter((entry) => entry.student) // guard against a deleted student
      .map((entry) => ({
        student_id: entry.student._id.toString(),
        student_number: entry.student.studentNumber,
        first_name: entry.student.firstName,
        last_name: entry.student.lastName,
        email: entry.student.email,
        email_sent: entry.emailSent,
        email_sent_at: entry.emailSentAt,
      }));

    return {
      allocation_id: classInfo._id.toString(),
      class_name: classInfo.className,
      room_id: classInfo.room._id.toString(),
      room_name: classInfo.room.roomName,
      room_capacity: classInfo.room.capacity,
      block_name: classInfo.room.block || null,
      room_code: classInfo.room.roomCode || null,
      students,
      student_count: students.length,
    };
  });
}

export async function getAllRooms() {
  const rooms = await Room.find().sort({ block: 1, roomCode: 1 }).lean();

  return rooms.map((room) => ({
    room_id: room._id.toString(),
    room_name: room.roomName,
    room_code: room.roomCode,
    block_name: room.block,
    capacity: room.capacity,
  }));
}

export async function markEmailSent(allocationId, studentId) {
  await ClassAllocation.updateOne(
    { _id: allocationId, "students.student": studentId },
    {
      $set: {
        "students.$.emailSent": true,
        "students.$.emailSentAt": new Date(),
      },
    }
  );
}
