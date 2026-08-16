import { faMagnifyingGlass, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useRef, useState } from "react";
import { Form, useSubmit } from "react-router";

import { Icon } from "~/components/Icon";

/**
 * What the box does with what was typed.
 *
 * The two are genuinely different acts, so the component takes one rather than
 * forcing either: the library narrows a list it is already holding, and the two
 * admin screens ask the server a new question. What they must NOT differ about
 * is whether you can empty the box, which is where the four copies had drifted.
 */
export type SearchAction =
  /** The page filters what it already has. The caller holds the text. */
  | { kind: "filter"; value: string; onChange: (next: string) => void }
  /**
   * A GET navigation on every keystroke.
   *
   * A real form, so Enter still works and so does a browser with no JavaScript.
   * `hidden` is whatever else must ride along or the navigation drops it — the
   * book being provisioned, the filter chip that is lit.
   */
  | {
      kind: "navigate";
      name: string;
      value: string;
      hidden?: Record<string, string>;
    };

/**
 * The one search box.
 *
 * There were four, with three behaviours between them and a clear button on
 * exactly one — so on the library you could empty the box in a press and on both
 * admin screens you selected the text and deleted it, which is the same control
 * failing to be the same control. What varied legitimately was only ever the
 * SUBMISSION; everything the reader touches is now identical by construction.
 */
export function SearchBox({
  id,
  label,
  placeholder,
  size,
  action,
}: {
  id: string;
  /** The label, visually hidden — the magnifier is not a name. */
  label: string;
  placeholder: string;
  /** `pf-search--sm` in a panel, `pf-search--wide` across a table head. */
  size?: "sm" | "wide";
  action: SearchAction;
}) {
  const submit = useSubmit();
  const input = useRef<HTMLInputElement>(null);
  /**
   * What is in the box right now, in `navigate` mode only.
   *
   * The input stays UNCONTROLLED there — `defaultValue`, exactly as before — so
   * a navigation landing mid-word cannot reset what someone is typing. But the
   * clear button has to know whether there is anything to clear, and the URL's
   * copy of the text lags a keystroke behind the box. This is that answer, and
   * it is never the source of what gets submitted.
   */
  const [typed, setTyped] = useState(
    action.kind === "navigate" ? action.value : "",
  );
  const showClear = (action.kind === "filter" ? action.value : typed) !== "";

  function clear() {
    if (action.kind === "filter") {
      action.onChange("");
      input.current?.focus();
      return;
    }

    const element = input.current;
    if (element === null) return;
    // Written to the DOM before submitting, not through state: the submission
    // reads the form as it stands, and React has not committed a re-render yet
    // — so clearing through state alone would send the old text.
    element.value = "";
    setTyped("");
    element.focus();
    if (element.form !== null) void submit(element.form);
  }

  const guts = (
    <>
      <Icon icon={faMagnifyingGlass} className="pf-search__icon" />
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        ref={input}
        id={id}
        type="search"
        placeholder={placeholder}
        // A search box is not a field with a remembered value; the browser's
        // own dropdown over it covers the results it is filtering.
        autoComplete="off"
        className="pf-search__input"
        {...(action.kind === "filter"
          ? {
              value: action.value,
              onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
                action.onChange(event.target.value),
            }
          : {
              name: action.name,
              defaultValue: action.value,
              // The submission itself is the FORM's `onChange` below, which this
              // event goes on to reach. This only keeps the clear button honest.
              onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
                setTyped(event.target.value),
            })}
      />
      {showClear ? (
        <button
          type="button"
          onClick={clear}
          aria-label="Clear the search"
          className="pf-search__clear"
        >
          <Icon icon={faXmark} />
        </button>
      ) : null}
    </>
  );

  if (action.kind === "filter") {
    return (
      <search
        className={`pf-search${size === "sm" ? " pf-search--sm" : size === "wide" ? " pf-search--wide" : ""}`}
      >
        {guts}
      </search>
    );
  }

  return (
    <Form
      method="get"
      role="search"
      onChange={(event) => void submit(event.currentTarget)}
      className={`pf-search${size === "sm" ? " pf-search--sm" : size === "wide" ? " pf-search--wide" : ""}`}
    >
      {Object.entries(action.hidden ?? {}).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      {guts}
    </Form>
  );
}
