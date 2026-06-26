import { Room } from 'livekit-client'

export const createRoom = () => {
  return new Room({
    adaptiveStream: true,
    dynacast: true,
    // Apply echo/noise cancellation to every mic track created by this room
    // (including when the user clicks Unmute / setMicrophoneEnabled(true)).
    audioCaptureDefaults: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
    audioOutput: {
      deviceId: 'default',
    },
  })
}
