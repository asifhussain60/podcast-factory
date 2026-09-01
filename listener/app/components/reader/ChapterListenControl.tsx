import { faHeadphones } from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";

export function ChapterListenControl({
  active,
  playing,
  onToggle,
}: {
  active: boolean;
  playing: boolean;
  onToggle: () => void;
}) {
  const paused = active && playing;
  const label = paused ? "Pause chapter audio" : "Listen to this chapter";

  return (
    <div className="pf-reader-listen" data-active={active ? "true" : "false"}>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={paused}
        title={label}
        className="pf-reader-listen__button"
      >
        <span
          className="pf-reader-listen__orbit pf-reader-listen__orbit--outer"
          aria-hidden="true"
        />
        <span
          className="pf-reader-listen__orbit pf-reader-listen__orbit--inner"
          aria-hidden="true"
        />
        <span className="pf-reader-listen__aura" aria-hidden="true" />
        <span className="pf-reader-listen__icon" aria-hidden="true">
          <Icon icon={faHeadphones} title="" />
          <span className="pf-reader-listen__state" />
        </span>
        <span className="pf-reader-listen__copy" aria-hidden="true">
          <span className="pf-reader-listen__label">
            {paused ? "Pause" : "Listen"}
          </span>
        </span>
        <span className="sr-only">{label}</span>
      </button>
    </div>
  );
}
