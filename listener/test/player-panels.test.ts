import { describe, expect, it } from "vitest";

import {
  playerPanelModel,
  type NowPlaying,
} from "../app/components/player/Player";

const EPISODE: NowPlaying = {
  kind: "episode",
  slug: "the-master-and-the-disciple",
  bookTitle: "The Master and the Disciple",
  number: 1,
  title: "The Persian Who Was Dead and Revived",
  src: "/media/episode.mp3",
  durationS: 381,
  transcriptSrc: "/media/episode.vtt",
};

const CHAPTER: NowPlaying = {
  ...EPISODE,
  kind: "chapter",
  src: "/media/chapter.mp3",
  transcriptSrc: null,
  cues: [
    { startS: 0, endS: 10, text: "It has been transmitted.", speaker: null },
  ],
};

describe("the persistent player panels", () => {
  it("keeps transcript available alongside notes for chapter read-aloud", () => {
    const model = playerPanelModel(CHAPTER, []);

    expect(model.showTranscript).toBe(true);
    expect(model.notesLabel).toBe("Notes");
    expect(model.noteScope).toBe("chapter");
  });

  it("keeps transcripts available for podcast episodes", () => {
    const model = playerPanelModel(EPISODE, [{ number: 1 }, { number: 2 }]);

    expect(model.showTranscript).toBe(true);
    expect(model.notesLabel).toBe("Notes, 1 in this episode");
    expect(model.noteScope).toBe("episode");
  });
});
