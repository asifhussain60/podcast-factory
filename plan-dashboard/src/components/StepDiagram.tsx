interface StepDiagramProps {
  stepId: string;
}

export default function StepDiagram({ stepId }: StepDiagramProps) {
  // Lightweight fallback renderer so plan rows always have a stable diagram slot.
  return (
    <div className="step-diagram" data-step-id={stepId} aria-label={`Step ${stepId} diagram`}>
      <div className="step-diagram-node is-current">{stepId}</div>
    </div>
  );
}
