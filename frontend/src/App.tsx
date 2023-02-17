import { FC, useState } from "react";
import styled from "styled-components";
import Track from "./components/Track";
import { ITrack } from "./interfaces";

interface AppProps {}

const BASE_URL = "http://localhost:8000";

const YOUTUBE_REGEX =
  /(youtu.*be.*)\/(watch\?v=|embed\/|v|shorts|)(.*?((?=[&#?])|$))/;

const App: FC<AppProps> = () => {
  const [query, setQuery] = useState<string>("");
  const [tracks, setTracks] = useState<ITrack[]>([]);

  const search = async () => {
    if (!query) return;

    if (YOUTUBE_REGEX.test(query)) {
      const id = query.match(YOUTUBE_REGEX)?.[3];

      const res = await fetch(`${BASE_URL}/track/${id}`);
      const data = await res.json();

      setTracks([data]);
      return;
    }

    const res = await fetch(`${BASE_URL}/search?query=${query}`);
    const data = await res.json();

    setTracks(data);
  };

  return (
    <Container>
      <div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={search}>Submit</button>
      </div>

      <div>
        {tracks.map((track) => (
          <Track key={track.id} track={track} />
        ))}
      </div>
    </Container>
  );
};

const Container = styled.div``;

export default App;
