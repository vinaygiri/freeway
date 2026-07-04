/**
 * @file web/src/components/inspector/RequestInspectorView.jsx
 * @description Request Inspector — glass-box table of recent routing decisions
 * from the Freeway proxy (what was asked, where it routed and why, tokens,
 * fallback, outcome). Reads /api/proxy/requests via useRequestInspector.
 */
import { useRequestInspector } from '../../hooks/useRequestInspector.js'

const cell = {
  textAlign: 'left',
  padding: '4px 10px',
  borderBottom: '1px solid var(--border, #333)',
  fontSize: 13,
  whiteSpace: 'nowrap',
}

export default function RequestInspectorView({ onClose }) {
  const { enabled, requests, loading, error, refresh } = useRequestInspector()

  return (
    <>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <h2 style={{ margin: 0 }}>Request Inspector</h2>
        <div>
          <button type="button" onClick={refresh}>
            Refresh
          </button>
          {onClose && (
            <button type="button" onClick={onClose} style={{ marginLeft: 8 }}>
              Close
            </button>
          )}
        </div>
      </div>

      {loading && <p>Loading…</p>}

      {!loading && !enabled && (
        <p>
          Request inspector is disabled or the Freeway proxy is unreachable
          {error ? ` (${error})` : ''}.
        </p>
      )}

      {!loading && enabled && requests.length === 0 && (
        <p>No requests recorded yet.</p>
      )}

      {!loading && enabled && requests.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={cell}>Model asked</th>
                <th style={cell}>Routed to</th>
                <th style={cell}>Tokens</th>
                <th style={cell}>Fallback</th>
                <th style={cell}>Reason</th>
                <th style={cell}>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.request_id}>
                  <td style={cell}>{request.gateway_model}</td>
                  <td style={cell}>
                    {request.provider_id}
                    {request.provider_model ? `/${request.provider_model}` : ''}
                  </td>
                  <td style={cell}>{request.input_tokens}</td>
                  <td style={cell}>{request.was_fallback ? 'yes' : ''}</td>
                  <td style={cell}>{request.downgrade_reason || ''}</td>
                  <td style={cell}>{request.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
