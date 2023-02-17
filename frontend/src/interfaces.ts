export interface ITrack {
  id: string;
  title: string;
  artists: string[];
  thumbnail: string;

  album?: string;
  lyrics?: string;
}
