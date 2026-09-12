/**
 * Seeds 200 demo students (with placeholder emails) under a dedicated
 * "Demo Allocation 2026" cohort, so the Class Allocation feature has a
 * pool of 200 students to split into 7 classes.
 *
 * Safe to re-run: skips if that cohort already has 200+ students.
 *
 * Usage: npm run seed:students   (from server/)
 */

import "dotenv/config";
import mongoose from "mongoose";
import { connectDB } from "../db.js";

import Programme from "../models/Programme.js";
import Cohort from "../models/Cohort.js";
import Student from "../models/Student.js";

const DEMO_COHORT_NAME = "Demo Allocation 2026";
const NUM_STUDENTS = 200;

async function getOrCreateDemoCohort() {
  let cohort = await Cohort.findOne({ cohortName: DEMO_COHORT_NAME });

  if (cohort) {
    return cohort;
  }

  const programme = await Programme.findOne();

  if (!programme) {
    throw new Error("No programme found. Run `npm run seed:core` first.");
  }

  cohort = await Cohort.create({
    programme: programme._id,
    cohortName: DEMO_COHORT_NAME,
    academicYear: "2026",
    semester: "Semester 1",
    size: NUM_STUDENTS,
  });

  return cohort;
}

async function seed() {
  await connectDB();

  const cohort = await getOrCreateDemoCohort();

  const existingCount = await Student.countDocuments({ cohort: cohort._id });

  if (existingCount >= NUM_STUDENTS) {
    console.log(`Demo cohort already has ${existingCount} students. Skipping.`);
    await mongoose.disconnect();
    return;
  }

  // A prior `seed:core --force` may have deleted the cohort these DEMO*
  // students pointed at, leaving them orphaned but still holding their
  // studentNumber (unique). Clear those out before reinserting, otherwise
  // insertMany collides on studentNumber.
  const orphanCleanup = await Student.deleteMany({
    studentNumber: { $regex: /^DEMO/ },
    cohort: { $ne: cohort._id },
  });
  if (orphanCleanup.deletedCount > 0) {
    console.log(`Cleared ${orphanCleanup.deletedCount} orphaned demo students from a previous cohort.`);
  }

  const docs = [];

  for (let i = existingCount + 1; i <= NUM_STUDENTS; i++) {
    docs.push({
      studentNumber: `DEMO${String(i).padStart(4, "0")}`,
      firstName: "Student",
      lastName: String(i),
      email: `student${i}@example.com`,
      cohort: cohort._id,
    });
  }

  await Student.insertMany(docs);

  console.log(`Seeded ${docs.length} demo students into cohort '${DEMO_COHORT_NAME}'.`);

  await mongoose.disconnect();
}

seed().catch((error) => {
  console.error("Seeding failed:", error);
  process.exit(1);
});
