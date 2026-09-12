import React from 'react';
import { createRoot } from 'react-dom/client';
import { CopilotKit, CopilotSidebar, useAgentContext } from '@copilotkit/react-core/v2';
import '@copilotkit/react-core/v2/styles.css';

const key = 'dreamphones-personal-agent-v1';
function Assistant() {
  const [state, setState] = React.useState(() => JSON.parse(localStorage.getItem(key) || '{}'));
  React.useEffect(() => {
    const update = () => setState(JSON.parse(localStorage.getItem(key) || '{}'));
    window.addEventListener('personal-agent:changed', update);
    window.addEventListener('storage', update);
    return () => { window.removeEventListener('personal-agent:changed', update); window.removeEventListener('storage', update); };
  }, []);
  useAgentContext({ description: 'The user personal agent profile, approval policy, five-scenario decisions, platform preferences, and purchase review cards. Use these only to advise. Never claim to change external recommendation feeds or place orders.', value: state });
  return <CopilotSidebar defaultOpen={false} />;
}

function ChatEntry() {
  const [enabled, setEnabled] = React.useState(false);
  React.useEffect(() => { fetch('/api/status').then(response => response.ok ? response.json() : null).then(status => setEnabled(Boolean(status?.copilotEnabled))).catch(() => {}); }, []);
  if (!enabled) return <div className="copilot-offline" title="Set OPENAI_API_KEY on the server to enable CopilotKit chat">AI chat needs an API key</div>;
  return <CopilotKit runtimeUrl="/api/copilotkit" useSingleEndpoint><Assistant /></CopilotKit>;
}
createRoot(document.getElementById('copilot-root')).render(<ChatEntry />);
