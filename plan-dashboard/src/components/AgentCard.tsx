interface Agent {
  id: string;
  name: string;
  role: string;
  icon: string;
  tone: string;
  plain: string;
  what_it_knows: string;
  boundary_in: string;
  boundary_out: string;
  does_not: string;
  cost_profile: string;
  failure_mode: string;
}

interface Props {
  agent: Agent;
}

export default function AgentCard({ agent }: Props) {
  const toneClass = `tone-${agent.tone}`;
  const iconClass = `fa-solid fa-${agent.icon}`;
  return (
    <div className={`agent-card ${toneClass}`}>
      <div className="agent-executor">
        <i className="fa-solid fa-robot" aria-hidden="true" />
        <span>Claude agent</span>
        <span className="agent-executor-model">· claude-3-5-sonnet</span>
      </div>
      <header className="agent-head">
        <div className="agent-icon"><i className={iconClass} aria-hidden="true"></i></div>
        <div className="agent-title">
          <span className="agent-name">{agent.name}</span>
          <span className="agent-role">{agent.role}</span>
        </div>
      </header>

      <p className="agent-lede">{agent.plain}</p>

      <div className="agent-attrs">
        <div className="agent-attr">
          <span className="k">What it knows</span>
          <span className="v">{agent.what_it_knows}</span>
        </div>
        <div className="agent-attr">
          <span className="k">Takes in</span>
          <span className="v">{agent.boundary_in}</span>
        </div>
        <div className="agent-attr">
          <span className="k">Hands back</span>
          <span className="v">{agent.boundary_out}</span>
        </div>
        <div className="agent-attr">
          <span className="k">Does not</span>
          <span className="v">{agent.does_not}</span>
        </div>
      </div>

      <div className="agent-cost-row">
        <span className="pill-cost"><i className="fa-solid fa-coins" aria-hidden="true"></i> {agent.cost_profile}</span>
        <span className="pill-fail"><i className="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> {agent.failure_mode}</span>
      </div>
    </div>
  );
}
