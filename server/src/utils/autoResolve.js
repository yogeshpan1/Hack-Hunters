import TimetableSession from "../models/TimetableSession.js";
import Room from "../models/Room.js";
import TimeSlot from "../models/TimeSlot.js";

function overlaps(a, b) {
  return a.dayId === b.dayId && a.startTime < b.endTime && b.startTime < a.endTime;
}

async function loadWorkingSet() {
  const [sessions, rooms, timeSlots] = await Promise.all([
    TimetableSession.find().lean(),
    Room.find().lean(),
    TimeSlot.find().lean(),
  ]);

  const timeSlotById = new Map(timeSlots.map((t) => [t._id.toString(), t]));

  const working = sessions.map((s) => {
    const slot = timeSlotById.get(s.timeSlot.toString());
    const room = rooms.find((r) => r._id.toString() === s.room.toString());

    return {
      _id: s._id.toString(),
      moduleId: s.module.toString(),
      facultyId: s.faculty.toString(),
      cohortId: s.cohort.toString(),
      roomId: s.room.toString(),
      timeSlotId: s.timeSlot.toString(),
      dayId: slot.dayOfWeek,
      startTime: slot.startTime,
      endTime: slot.endTime,
      roomCapacity: room.capacity,
    };
  });

  return { working, rooms, timeSlots };
}

function hasIssue(session, all, cohortSizeById) {
  for (const other of all) {
    if (other._id === session._id) continue;
    if (!overlaps(session, other)) continue;

    if (
      other.roomId === session.roomId ||
      other.facultyId === session.facultyId ||
      other.cohortId === session.cohortId
    ) {
      return true;
    }
  }

  return cohortSizeById.get(session.cohortId) > session.roomCapacity;
}

function conflictsAt(candidate, all, excludeId) {
  return all.some(
    (other) =>
      other._id !== excludeId &&
      other.dayId === candidate.dayId &&
      other.startTime < candidate.endTime &&
      candidate.startTime < other.endTime &&
      (other.roomId === candidate.roomId ||
        other.facultyId === candidate.facultyId ||
        other.cohortId === candidate.cohortId)
  );
}

/**
 * Tries to fix every unresolved conflict/capacity-warning session on `day`
 * by moving it to a free room (same time slot first), or, failing that, a
 * free room + time slot combination later the same day. Persists any fix
 * it finds. Returns { resolvedCount, resolved: [...], stillUnresolved: [...] }.
 */
export async function autoResolveDay(day, cohortSizeById) {
  const { working, rooms, timeSlots } = await loadWorkingSet();

  const daySlots = timeSlots
    .filter((t) => t.dayOfWeek === day)
    .sort((a, b) => a.startTime.localeCompare(b.startTime));

  const targets = working.filter((s) => s.dayId === day && hasIssue(s, working, cohortSizeById));

  const resolved = [];
  const stillUnresolved = [];

  for (const session of targets) {
    const cohortSize = cohortSizeById.get(session.cohortId) || 0;
    const eligibleRooms = rooms
      .filter((r) => r.capacity >= cohortSize)
      .sort((a, b) => a.capacity - b.capacity); // smallest room that still fits, first

    let fix = null;

    // 1) Same time slot, different room.
    for (const room of eligibleRooms) {
      if (room._id.toString() === session.roomId) continue;

      const candidate = { ...session, roomId: room._id.toString() };
      if (!conflictsAt(candidate, working, session._id)) {
        fix = { roomId: room._id.toString(), timeSlotId: session.timeSlotId, room };
        break;
      }
    }

    // 2) Different time slot the same day, same or different room.
    if (!fix) {
      outer: for (const slot of daySlots) {
        if (slot._id.toString() === session.timeSlotId) continue;

        for (const room of eligibleRooms) {
          const candidate = {
            ...session,
            roomId: room._id.toString(),
            timeSlotId: slot._id.toString(),
            startTime: slot.startTime,
            endTime: slot.endTime,
          };
          if (!conflictsAt(candidate, working, session._id)) {
            fix = { roomId: room._id.toString(), timeSlotId: slot._id.toString(), room, slot };
            break outer;
          }
        }
      }
    }

    if (fix) {
      // Update the in-memory working set too, so later sessions in this
      // same pass see the change and don't double-book the new slot.
      const idx = working.findIndex((s) => s._id === session._id);
      working[idx] = {
        ...working[idx],
        roomId: fix.roomId,
        timeSlotId: fix.timeSlotId,
        startTime: fix.slot ? fix.slot.startTime : session.startTime,
        endTime: fix.slot ? fix.slot.endTime : session.endTime,
        dayId: fix.slot ? fix.slot.dayOfWeek : session.dayId,
      };

      resolved.push({
        session_id: session._id,
        new_room_name: fix.room.roomName,
        new_day: fix.slot ? fix.slot.dayOfWeek : day,
        new_start_time: fix.slot ? fix.slot.startTime : session.startTime,
      });
    } else {
      stillUnresolved.push(session._id);
    }
  }

  if (resolved.length > 0) {
    await TimetableSession.bulkWrite(
      resolved.map((r) => {
        const updated = working.find((s) => s._id === r.session_id);
        return {
          updateOne: {
            filter: { _id: r.session_id },
            update: { room: updated.roomId, timeSlot: updated.timeSlotId },
          },
        };
      })
    );
  }

  return { resolvedCount: resolved.length, resolved, stillUnresolved };
}
