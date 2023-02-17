import { FC } from "react";
import styled from "styled-components";
import { ITrack } from "../interfaces";

interface TrackProps {
  track: ITrack;
}

const Track: FC<TrackProps> = ({ track }) => {
  return (
    <Container>
      <CoverImage src={track.thumbnail} alt="cover" />
      <InfoContainer>
        <Title>{track.title}</Title>

        {track.album && <Description>{track.album}</Description>}

        <Description>{track.artists.join(", ")}</Description>
      </InfoContainer>
    </Container>
  );
};

const Container = styled.div`
  display: flex;
`;

const CoverImage = styled.img`
  width: 80px;
`;

const InfoContainer = styled.div`
  display: flex;
  flex-direction: column;
`;

const Title = styled.span``;

const Description = styled.span``;

export default Track;
