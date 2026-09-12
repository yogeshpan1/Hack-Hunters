import { useEffect, useState } from "react";
import "./App.css";
import ClassAllocation from "./ClassAllocation.jsx";
import Sidebar from "./Sidebar.jsx";
import TimetableStudio from "./TimetableStudio.jsx";
import TopBar from "./TopBar.jsx";

function App() {
  const [activeTab, setActiveTab] = useState("timetable");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const handleShortcut = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.querySelector(".topbar-search input")?.focus();
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  return (
    <div className="app">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
      <div className="main-column">
        <TopBar
          activeTab={activeTab}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
        />
        <main className="page-body">
          {activeTab === "allocation" ? (
            <ClassAllocation />
          ) : (
            <TimetableStudio searchTerm={searchTerm} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
