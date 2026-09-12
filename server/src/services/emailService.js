import { Resend } from "resend";

const FROM_EMAIL = process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev";

function getResendClient() {
  if (!process.env.RESEND_API_KEY) {
    throw new Error("RESEND_API_KEY is not configured.");
  }

  return new Resend(process.env.RESEND_API_KEY);
}

function buildEmailHtml(studentName, className, roomName, roomCapacity) {
  return `
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;
                background: #111827; color: #f3f4f6; border-radius: 12px; overflow: hidden;">
      <div style="background: #2563eb; padding: 20px 24px;">
        <h1 style="margin: 0; font-size: 20px; color: #ffffff;">Nexus</h1>
        <p style="margin: 4px 0 0; color: #dbeafe; font-size: 13px;">Class Allocation Notice</p>
      </div>
      <div style="padding: 24px;">
        <p style="font-size: 15px;">Hi ${studentName},</p>
        <p style="font-size: 15px; line-height: 1.5;">
          You have been assigned to a class for the upcoming term. Details below:
        </p>
        <div style="background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 16px; margin: 16px 0;">
          <p style="margin: 6px 0;"><strong style="color: #60a5fa;">Class:</strong> ${className}</p>
          <p style="margin: 6px 0;"><strong style="color: #60a5fa;">Room:</strong> ${roomName}</p>
          <p style="margin: 6px 0;"><strong style="color: #60a5fa;">Capacity:</strong> ${roomCapacity} students</p>
        </div>
        <p style="font-size: 14px; color: #9ca3af;">
          Please make a note of your room for the start of term. If you believe this is a mistake,
          contact the administration office.
        </p>
      </div>
      <div style="background: #0b0f19; padding: 14px 24px; font-size: 12px; color: #6b7280;">
        Sent automatically by the Nexus Class Allocation system.
      </div>
    </div>
  `;
}

/**
 * Sends one class-assignment email via Resend.
 * Throws if Resend reports an error.
 */
export async function sendClassAssignmentEmail(toEmail, studentName, className, roomName, roomCapacity) {
  const resend = getResendClient();
  const { data, error } = await resend.emails.send({
    from: FROM_EMAIL,
    to: toEmail,
    subject: `Your Class Assignment - ${className}`,
    html: buildEmailHtml(studentName, className, roomName, roomCapacity),
  });

  if (error) {
    throw new Error(error.message || "Resend failed to send the email.");
  }

  return data;
}
