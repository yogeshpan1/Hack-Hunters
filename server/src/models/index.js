// Importing every model here (for its side effect of calling mongoose.model(...))
// guarantees all schemas are registered before any `.populate()` call runs,
// regardless of which route/util happens to import which model directly.

import "./Programme.js";
import "./Cohort.js";
import "./Room.js";
import "./Faculty.js";
import "./Module.js";
import "./TimeSlot.js";
import "./TimetableSession.js";
import "./Student.js";
import "./ClassAllocation.js";
