const PAGE_TITLES = {
  timetable: "Timetable Studio",
  allocation: "Class Allocation",
};

function TopBar({ activeTab, searchTerm, onSearchChange }) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        Islington Campus <span className="crumb-sep">/</span>{" "}
        <strong>{PAGE_TITLES[activeTab] || "Timetable Studio"}</strong>
      </div>

      <div className="topbar-spacer" />

      <div className="topbar-search">
        <span className="search-icon">⌕</span>
        <input
          type="text"
          placeholder="Search people, rooms, modules..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <kbd>⌘K</kbd>
      </div>

      <div className="ay-badge">AY 2026/27</div>

      <div className="topbar-icons">
        <span title="History">🕘</span>
        <span title="Notifications">🔔</span>
        <span title="Help">❔</span>
      </div>

      <div className="avatar-block">
        <div className="avatar-circle">N</div>
        <div className="avatar-text">
          <div className="avatar-name">Nexus Admin</div>
          <div className="avatar-role">Registrar</div>
        </div>
      </div>
    </header>
  );
}

export default TopBar;
