export default function Transcript({ turns, highlightTurnIds }) {
  return (
    <div className="transcript">
      {turns.map((turn) => {
        const isEvidence = highlightTurnIds.includes(turn.turn_id);
        return (
          <div key={turn.turn_id} className={`turn ${isEvidence ? "highlighted" : ""}`}>
            <div className="turn-header">
              <span className="turn-role">{turn.role}</span>
              <span className="turn-id">turn {turn.turn_id}</span>
            </div>
            <p className="turn-text">{turn.text}</p>
            {turn.tool_call && (
              <pre className="tool-call">
{`tool: ${turn.tool_call.tool_name}
parameters: ${JSON.stringify(turn.tool_call.parameters)}
response: ${JSON.stringify(turn.tool_call.response)}
error_code: ${turn.tool_call.error_code}   latency_ms: ${turn.tool_call.latency_ms}`}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
}
