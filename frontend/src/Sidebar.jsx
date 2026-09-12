const NAV_SECTIONS = [
  {
    label: "Operate",
    items: [
      { key: "command-center", icon: "🧭", title: "Command Center" },
      { key: "timetable", icon: "📅", title: "Timetable Studio" },
      { key: "examinations", icon: "📝", title: "Examinations" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { key: "optimization-lab", icon: "🧪", title: "Optimization Lab" },
      { key: "what-if", icon: "🔀", title: "What-If Simulator" },
      { key: "analytics", icon: "📊", title: "Analytics" },
    ],
  },
  {
    label: "Manage",
    items: [
      { key: "rooms", icon: "🏛️", title: "Rooms & Resources" },
      { key: "faculty", icon: "👤", title: "Faculty Intelligence" },
      { key: "cohort-flow", icon: "👥", title: "Cohort Flow" },
      { key: "modules", icon: "📦", title: "Modules" },
      { key: "allocation", icon: "🎓", title: "Class Allocation" },
    ],
  },
  {
    label: "System",
    items: [
      { key: "rules", icon: "📏", title: "Scheduling Rules" },
      { key: "change-log", icon: "🕓", title: "Change Log" },
      { key: "data-import", icon: "📥", title: "Data Import" },
    ],
  },
];

const ENABLED_KEYS = new Set(["timetable", "allocation"]);

function Sidebar({ activeTab, onSelectTab }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">N</div>
        <div>
          <div className="brand-sub">Islington College</div>
          <div className="brand-name">NEXUS</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div className="nav-section" key={section.label}>
            <div className="nav-section-label">{section.label}</div>
            {section.items.map((item) => {
              const enabled = ENABLED_KEYS.has(item.key);
              const active = enabled && item.key === activeTab;

              return (
                <button
                  key={item.key}
                  className={`nav-item ${active ? "active" : ""} ${enabled ? "" : "inert"}`}
                  onClick={() => enabled && onSelectTab(item.key)}
                  title={enabled ? item.title : `${item.title} (coming soon)`}
                  disabled={!enabled}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.title}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-status">
        <span className="status-dot" /> All systems nominal
      </div>
    </aside>
  );
}

export default Sidebar;
