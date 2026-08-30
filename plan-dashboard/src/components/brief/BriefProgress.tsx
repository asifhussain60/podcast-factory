/**
 * BriefProgress — how far through the commission you are, at the top of the page.
 *
 * A segment per step, filled once that step's answers are complete. It reports
 * COMPLETION, not merely position: walking forward does not fill a segment on
 * its own, and going back to empty a required field un-fills it. That is the
 * honest reading, and it matches what the wizard will actually let you do —
 * the same blocker list drives this bar and the rail's forward gate.
 */
import { STEPS, type StepId } from "../../lib/brief/fields";

interface Props {
  current: StepId;
  /** The furthest step reached, so an unseen step is never called complete. */
  furthest: StepId;
  /** Steps still missing a required answer, from the wizard's own check. */
  blockedSteps: StepId[];
}

export default function BriefProgress({
  current,
  furthest,
  blockedSteps,
}: Props) {
  // Complete = walked past it with nothing missing. Steps 2-5 carry no required
  // field, so "not blocked" alone would mark them done before they were seen.
  const isDone = (id: StepId) => id < furthest && !blockedSteps.includes(id);
  const done = STEPS.filter((s) => isDone(s.id)).length;
  const pct = Math.round((done / STEPS.length) * 100);
  const currentStep = STEPS.find((s) => s.id === current);

  return (
    <section className="bf-progress" aria-label="Progress">
      <div className="bf-progress-head">
        <p className="bf-progress-now">
          <span className="bf-progress-step">
            Step {current} of {STEPS.length}
          </span>
          <span className="bf-progress-sep" aria-hidden="true">
            ·
          </span>
          <span className="bf-progress-name">{currentStep?.title}</span>
        </p>
        <p className="bf-progress-count">
          {done} of {STEPS.length} complete
        </p>
      </div>

      <ol
        className="bf-progress-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={`${done} of ${STEPS.length} steps complete`}
      >
        {STEPS.map((s) => {
          const state = isDone(s.id)
            ? "done"
            : s.id === current
              ? "current"
              : "todo";
          return (
            <li className={`bf-progress-seg is-${state}`} key={s.id}>
              <span className="bf-progress-seg-label">{s.title}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
