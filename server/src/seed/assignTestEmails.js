/**
 * Reassigns the demo students' placeholder emails to a small set of real,
 * user-supplied test addresses (round-robin), so the class allocation
 * emails can actually be sent and tested via Resend.
 *
 * Usage: node src/seed/assignTestEmails.js   (from server/)
 */

import "dotenv/config";
import mongoose from "mongoose";
import { connectDB } from "../db.js";

import Cohort from "../models/Cohort.js";
import Student from "../models/Student.js";

const DEMO_COHORT_NAME = "Demo Allocation 2026";

const TEST_EMAILS = [
  "bhusalasim84@gmail.com",
  "arjanregmi2006@gmail.com",
  "jsnmhrjn@gmail.com",
];

async function run() {
  await connectDB();

  const cohort = await Cohort.findOne({ cohortName: DEMO_COHORT_NAME });

  if (!cohort) {
    throw new Error(`Cohort '${DEMO_COHORT_NAME}' not found. Run seed:core and seed:students first.`);
  }

  const students = await Student.find({ cohort: cohort._id }).sort({ studentNumber: 1 });

  if (students.length === 0) {
    console.log("No demo students found - nothing to update.");
    await mongoose.disconnect();
    return;
  }

  const counts = Object.fromEntries(TEST_EMAILS.map((e) => [e, 0]));

  const ops = students.map((student, index) => {
    const email = TEST_EMAILS[index % TEST_EMAILS.length];
    counts[email] += 1;

    return {
      updateOne: {
        filter: { _id: student._id },
        update: { $set: { email } },
      },
    };
  });

  await Student.bulkWrite(ops);

  console.log(`Reassigned ${students.length} demo students across ${TEST_EMAILS.length} real test addresses:`);
  for (const [email, count] of Object.entries(counts)) {
    console.log(`  ${email}: ${count} students`);
  }

  await mongoose.disconnect();
}

run().catch((error) => {
  console.error("Failed to reassign emails:", error);
  process.exit(1);
});
