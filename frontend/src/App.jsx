
import { useState } from "react";
import "./App.css";
import ClassAllocation from "./ClassAllocation.jsx";
import TimetableStudio from "./TimetableStudio.jsx";
import Sidebar from "./Sidebar.jsx";
import TopBar from "./TopBar.jsx";

function App() {
  const [activeTab, setActiveTab] = useState("timetable");
  const [searchTerm, setSearchTerm] = useState("");

  return (
    <div className="app">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />

      <div className="main-column">
        <TopBar activeTab={activeTab} searchTerm={searchTerm} onSearchChange={setSearchTerm} />

        <div className="page-body">
          {activeTab === "timetable" && <TimetableStudio searchTerm={searchTerm} />}
          {activeTab === "allocation" && <ClassAllocation />}
        </div>
      </div>
    </div>
  );
}

export default App;
