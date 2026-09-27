import "./Transcript.css";

function ToolCall({ call }) {
  return (
    <div className="tool-call">
      <div className="tool-call-head">
        <span className="tool-call-name">{call.tool_name}</span>
        {call.error_code && <span className="tool-call-error">{call.error_code}</span>}
        {typeof call.latency_ms === "number" && (
          <span className="tool-call-latency">{call.latency_ms} ms</span>
        )}
      </div>
      <pre className="tool-call-body">{`parameters: ${JSON.stringify(call.parameters ?? null, null, 2)}
response: ${JSON.stringify(call.response ?? null, null, 2)}`}</pre>
    </div>
  );
}

export default function Transcript({ turns, highlightTurnIds }) {
  return (
    <div className="transcript">
      {turns.map((turn) => {
        const isUser = turn.role === "user";
        const isEvidence = highlightTurnIds.includes(turn.turn_id);

        return (
          <div
            key={turn.turn_id}
            className={`turn-row ${isUser ? "turn-row--user" : "turn-row--agent"}${
              isEvidence ? " is-evidence" : ""
            }`}
          >
            <div className="turn-head">
              <span className="turn-role">{isUser ? "User" : "Agent"}</span>
              <span className="turn-id">turn {turn.turn_id}</span>
              {isEvidence && <span className="turn-flag">Failure evidence</span>}
            </div>

            <div className="turn-bubble">{turn.text}</div>

            {turn.tool_call && <ToolCall call={turn.tool_call} />}
          </div>
        );
      })}
    </div>
  );
}
