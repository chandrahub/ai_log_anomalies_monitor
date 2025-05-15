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
  },
};

type Log = {
  timestamp: number;
  level: string;
  message: string;
  reason?: string;
  suggestion?: string;
};

type ChatMessage = {
  from: "user" | "agent";
  text: string;
};

export default function Home() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<"inject" | "query">("inject");
  const [loading, setLoading] = useState(false);

  // Fetch anomalies regularly
  useEffect(() => {
    if (mode === "inject") {
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
    }
  }, [mode]);

  // Filter logs by level
  const filteredLogs = logs.filter(
    (log) => filter === "ALL" || log.level === filter
  );

  // Handle chat submit
  const handleSubmit = async () => {
    if (!input.trim()) return;
    const userMessage: ChatMessage = { from: "user", text: input };
    setChatMessages((msgs) => [...msgs, userMessage]);
    setLoading(true);

    try {
      if (mode === "inject") {
        // Inject log via /chat endpoint
        const res = await fetch("http://localhost:5001/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: input }),
        });
        const data = await res.json();
        const agentMessage: ChatMessage = {
          from: "agent",
          text: data.reply || "Log injected successfully",
        };
        setChatMessages((msgs) => [...msgs, agentMessage]);
      } else {
        // Query logs via /chat-query endpoint
        const res = await fetch("http://localhost:5001/chat-query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: input }),
        });
        const data: Log[] = await res.json();
        // Show results in chat
        const agentText =
          data.length > 0
            ? `Found ${data.length} logs:\n` +
              data
                .map(
                  (log) =>
                    `[${log.level}] ${new Date(
                      log.timestamp * 1000
                    ).toLocaleString()}: ${log.message}`
                )
                .join("\n")
            : "No logs found matching your query.";
        const agentMessage: ChatMessage = { from: "agent", text: agentText };
        setChatMessages((msgs) => [...msgs, agentMessage]);
        // Also update logs shown below to queried logs
        setLogs(data);
        setFilter("ALL");
      }
    } catch (err) {
      const agentMessage: ChatMessage = {
        from: "agent",
        text: "Error: Could not process your request.",
      };
      setChatMessages((msgs) => [...msgs, agentMessage]);
    } finally {
      setInput("");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-center">AI Log Monitor Dashboard</h1>

      {/* Mode selector */}
      <div className="flex justify-center mb-4 space-x-4">
        <button
          className={`px-4 py-2 rounded font-medium transition ${
            mode === "inject"
              ? "bg-blue-600 text-white"
              : "bg-white text-blue-600 border border-blue-600"
          }`}
          onClick={() => setMode("inject")}
        >
          Inject Log (Chat)
        </button>
        <button
          className={`px-4 py-2 rounded font-medium transition ${
            mode === "query"
              ? "bg-green-600 text-white"
              : "bg-white text-green-600 border border-green-600"
          }`}
          onClick={() => setMode("query")}
        >
          Query Logs (Chat)
        </button>
      </div>

      {/* Chat box */}
      <div className="bg-white rounded shadow-md p-4 mb-6 max-h-72 overflow-y-auto space-y-3 border border-gray-300">
        {chatMessages.length === 0 && (
          <p className="text-gray-400 italic text-center">Start typing below...</p>
        )}
        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`px-4 py-2 rounded max-w-[75%] whitespace-pre-line ${
                msg.from === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-900"
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className="flex space-x-2 mb-6">
        <input
          type="text"
          className="flex-grow px-4 py-2 rounded border border-gray-300"
          placeholder={
            mode === "inject"
              ? "Type a log message to inject"
              : "Type a query like 'Show all error messages in last 24 hours'"
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !loading) {
              handleSubmit();
            }
          }}
          disabled={loading}
        />
        <button
          onClick={handleSubmit}
          disabled={loading || !input.trim()}
          className={`px-4 py-2 rounded font-medium ${
            loading
              ? "bg-gray-400 cursor-not-allowed"
              : mode === "inject"
              ? "bg-blue-600 text-white"
              : "bg-green-600 text-white"
          }`}
        >
          {loading ? "Processing..." : mode === "inject" ? "Inject" : "Query"}
        </button>
      </div>

      {/* Filter buttons only in inject mode */}
      {mode === "inject" && (
        <>
          <div className="flex justify-center mb-6 space-x-4">
            {["ALL", "ERROR", "WARN", "INFO", "DEBUG"].map((lvl) => (
              <button
                key={lvl}
                className={`px-4 py-2 rounded font-medium transition ${
                  filter === lvl
                    ? "bg-blue-600 text-white"
                    : "bg-white text-blue-600 border border-blue-600"
                }`}
                onClick={() => setFilter(lvl)}
              >
                {lvl}
              </button>
            ))}
          </div>

          {/* Logs display */}
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
                    <div
                      className={`text-sm font-bold uppercase tracking-wide ${style.text} mb-1`}
                    >
                      {log.level}
                    </div>
                    <div className="text-gray-900 font-medium mb-2">{log.message}</div>
                    <div className="text-sm text-gray-700 mb-1">
                      <strong>Reason:</strong> {log.reason || "N/A"}
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Suggestion:</strong> {log.suggestion || "N/A"}
                    </div>
                  </div>
                </div>
              );
            })}
            {filteredLogs.length === 0 && (
              <p className="text-center text-gray-500">No logs to display.</p>
            )}
          </div>
        </>
      )}
    </main>
  );
}