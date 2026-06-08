import { Room } from 'livekit-client'

export const createRoom = () => {
  return new Room({
    adaptiveStream: true,
    dynacast: true,
  })
}