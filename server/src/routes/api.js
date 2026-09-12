import { Router } from "express";

import { getTimetableForClashDetection } from "../utils/timetable.js";
import { detectClashes, detectCapacityClashes } from "../utils/clashDetector.js";
import { autoResolveDay } from "../utils/autoResolve.js";
import Cohort from "../models/Cohort.js";
import {
  generateAllocation,
  getClassesWithStudents,
  markEmailSent,
  getAllRooms,
} from "../utils/allocation.js";
import { sendClassAssignmentEmail } from "../services/emailService.js";

const router = Router();

router.get("/", (req, res) => {
  res.json({ message: "RTE Clash Detection API is running" });
});

router.get("/timetable", async (req, res, next) => {
  try {
    const entries = await getTimetableForClashDetection();
    res.json(entries);
  } catch (error) {
    next(error);
  }
});

router.get("/check-clashes", async (req, res, next) => {
  try {
    const entries = await getTimetableForClashDetection();

    const clashes = detectClashes(entries);
    const capacityClashes = detectCapacityClashes(entries);
    const allClashes = [...clashes, ...capacityClashes];

    res.json({
      has_clashes: allClashes.length > 0,
      total_clashes: allClashes.length,
      clashes: allClashes,
    });
  } catch (error) {
    next(error);
  }
});

router.post("/timetable/auto-resolve", async (req, res, next) => {
  try {
    const { day } = req.body || {};

    if (!day) {
      return res.status(400).json({ detail: "Missing 'day' (e.g. 'Tuesday')." });
    }

    const cohorts = await Cohort.find().lean();
    const cohortSizeById = new Map(cohorts.map((c) => [c._id.toString(), c.size]));

    const result = await autoResolveDay(day, cohortSizeById);

    res.json(result);
  } catch (error) {
    next(error);
  }
});

router.get("/rooms", async (req, res, next) => {
  try {
    const rooms = await getAllRooms();
    res.json({ rooms });
  } catch (error) {
    next(error);
  }
});

// ============================================================
// CLASS ALLOCATION
// ============================================================

router.post("/allocate-classes", async (req, res, next) => {
  try {
    const classes = await generateAllocation(7, "Skill");

    res.json({
      message: "Students allocated into 7 classes.",
      classes,
    });
  } catch (error) {
    if (error.isValidation) {
      return res.status(400).json({ detail: error.message });
    }

    next(error);
  }
});

router.get("/classes", async (req, res, next) => {
  try {
    const classes = await getClassesWithStudents();
    res.json({ classes });
  } catch (error) {
    next(error);
  }
});

router.post("/send-test-email", async (req, res) => {
  const { to } = req.body || {};

  if (!to) {
    return res.status(400).json({ detail: "Missing 'to' email address." });
  }

  try {
    await sendClassAssignmentEmail(to, "Test Student", "Class 1", "Prashidika Tiwari", 30);
    res.json({ message: `Test email sent to ${to}` });
  } catch (error) {
    res.status(502).json({ detail: error.message });
  }
});

router.post("/send-emails", async (req, res, next) => {
  try {
    const limit = req.query.limit ? parseInt(req.query.limit, 10) : null;
    const onlyUnsent = req.query.only_unsent !== "false";

    const classes = await getClassesWithStudents();

    if (classes.length === 0) {
      return res.status(400).json({ detail: "No class allocation exists yet. Generate one first." });
    }

    const results = [];

    outer: for (const classInfo of classes) {
      for (const student of classInfo.students) {
        if (onlyUnsent && student.email_sent) {
          continue;
        }

        if (limit !== null && results.length >= limit) {
          break outer;
        }

        const studentName = `${student.first_name} ${student.last_name}`;

        try {
          await sendClassAssignmentEmail(
            student.email,
            studentName,
            classInfo.class_name,
            classInfo.room_name,
            classInfo.room_capacity
          );

          await markEmailSent(classInfo.allocation_id, student.student_id);

          results.push({
            student_id: student.student_id,
            email: student.email,
            class_name: classInfo.class_name,
            status: "sent",
          });
        } catch (error) {
          results.push({
            student_id: student.student_id,
            email: student.email,
            class_name: classInfo.class_name,
            status: "failed",
            error: error.message,
          });
        }
      }
    }

    const sentCount = results.filter((r) => r.status === "sent").length;
    const failedCount = results.length - sentCount;

    res.json({
      total: results.length,
      sent: sentCount,
      failed: failedCount,
      results,
    });
  } catch (error) {
    next(error);
  }
});

export default router;
