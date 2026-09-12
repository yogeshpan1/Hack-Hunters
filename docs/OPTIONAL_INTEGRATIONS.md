# Optional AI and email integrations

Adapted from the Groq chatbot and Resend sender in Final.zip. Hack-Hunters' MySQL clash detector was not imported because NEXUS already implements those constraints. No ZIP credentials or bundled dependencies were copied.

## AI-assisted questions

Set `AI_PROVIDER=groq`, `GROQ_API_KEY`, and optionally `GROQ_MODEL` (default `openai/gpt-oss-120b`) in the ignored local `.env`, then restart the backend. The default `AI_PROVIDER=structured` keeps existing behaviour with no external requests.

Groq receives the current user question and up to six prior user questions. It translates phrasing and follow-up references into a standalone question. NEXUS answers through its existing role-aware MongoDB queries and constraint engine. Database records, email addresses from the roster, audit results and credentials are not supplied as model context. Text a user types in a question does go to Groq. Model output is never executed as SQL, Python, MongoDB queries, or a write instruction. Provider errors fall back to the original structured query. This extends wording support, not the assistant's supported data domains.

## Reviewed email delivery

Set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` to a verified sender in local `.env`, then restart. Communications exposes a separate **Send real email** action. Review the draft recipient and message, then confirm. A provider receipt is stored and the status becomes **Accepted by Resend**; this does not claim inbox delivery. Successfully sent messages cannot be edited or sent again.

Existing automatic draft preparation after schedule publication remains intact. Existing demo send/schedule controls remain explicitly simulated. There is no background live sender and enabling Resend does not send queued messages. Generated or derived student addresses must be checked before real delivery.

Provider requests have timeouts and content-specific idempotency keys. Resend deduplicates matching keys for 24 hours. If delivery succeeds but the database commit fails, retry the unchanged draft within that window; after ambiguous errors check Resend before editing or retrying. A distributed outbox worker and delivery webhooks remain future work.

No live requests or real emails are needed for the automated tests: provider calls are mocked.

References: https://console.groq.com/docs/api-reference and https://resend.com/docs/api-reference/emails/send-email and https://resend.com/docs/dashboard/emails/idempotency-keys
