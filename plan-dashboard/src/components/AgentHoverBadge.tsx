import * as HoverCard from '@radix-ui/react-hover-card';
import AgentCard from './AgentCard';

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

interface Props { agent: Agent; }

export default function AgentHoverBadge({ agent }: Props) {
  const toneClass = `tone-${agent.tone}`;
  return (
    <HoverCard.Root openDelay={120} closeDelay={80}>
      <HoverCard.Trigger asChild>
        <button type="button" className={`agent-pin ${toneClass}`} aria-label={`Agent: ${agent.name}`}>
          <i className={`fa-solid fa-${agent.icon}`} aria-hidden="true"></i>
          <span className="agent-pin-name">{agent.name}</span>
          <i className="fa-solid fa-arrow-up-right-from-square agent-pin-hint" aria-hidden="true"></i>
        </button>
      </HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content className="agent-popover" side="right" sideOffset={12} collisionPadding={16}>
          <AgentCard agent={agent} />
          <HoverCard.Arrow className="agent-popover-arrow" />
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}
