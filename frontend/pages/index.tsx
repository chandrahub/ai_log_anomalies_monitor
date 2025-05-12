import { useEffect, useState } from "react";
import { AlertCircle, Info, Bug, AlertTriangle } from "lucide-react";

const levelStyles = {
  ERROR: {
    border: "border-red-500",
    text: "text-red-700",
    bg: "bg-red-50",
    icon: <AlertCircle className="text-red-500" />,
  },
  WARN: {
    border: "border-yellow-500",
    text: "text-yellow-700",
    bg: "bg-yellow-50",
    icon: <AlertTriangle className="text-yellow-500" />,
  },
  INFO: {
    border: "border-blue-500",
    text: "text-blue-700",
    bg: "bg-blue-50",
    icon: <Info className="text-blue-500" />,
  },
  DEBUG: {
    border: "border-gray-400",
    text: "text-gray-600",
    bg: "bg-gray-50",
    icon: <Bug className="text-gray-400" />,
  }
};

export default function Home() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch("http://localhost:5001/logs");
        const data = await res.json();
        setLogs(data);
      } catch (err) {
        console.error("Failed to fetch logs", err);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const filteredLogs = logs.filter(log => filter === "ALL" || log.level === filter);

  return (
    <main className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold mb-6 text-center">AI Log Monitor Dashboard</h1>

      <div className="flex justify-center mb-6 space-x-4">
        {["ALL", "ERROR", "WARN", "INFO", "DEBUG"].map(lvl => (
          <button
            key={lvl}
            className={`px-4 py-2 rounded font-medium transition ${
              filter === lvl ? 'bg-blue-600 text-white' : 'bg-white text-blue-600 border border-blue-600'
            }`}
            onClick={() => setFilter(lvl)}
          >
            {lvl}
          </button>
        ))}
      </div>

      <div className="grid gap-6">
        {filteredLogs.map((log, index) => {
          const style = levelStyles[log.level] || {};
          return (
            <div
              key={index}
              className={`shadow-md rounded-xl p-6 border-l-4 flex items-start space-x-4 ${style.border} ${style.bg}`}
            >
              <div className="mt-1">{style.icon}</div>
              <div className="flex-1">
                <div className="text-xs text-gray-500 mb-1">
                  {new Date(log.timestamp * 1000).toLocaleString()}
                </div>
                <div className={`text-sm font-bold uppercase tracking-wide ${style.text} mb-1`}>
                  {log.level}
                </div>
                <div className="text-gray-900 font-medium mb-2">{log.message}</div>
                <div className="text-sm text-gray-700 mb-1">
                  <strong>Reason:</strong> {log.reason}
                </div>
                <div className="text-sm text-gray-700">
                  <strong>Suggestion:</strong> {log.suggestion}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}