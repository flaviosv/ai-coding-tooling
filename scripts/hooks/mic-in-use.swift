// Exits 0 when any process is capturing audio input (a call, dictation, a
// recording), 1 otherwise. Asks per process rather than per device, so audio
// playing through a headset does not count. Core Audio process objects need
// macOS 14+.
import CoreAudio

let system = AudioObjectID(kAudioObjectSystemObject)
var address = AudioObjectPropertyAddress(
  mSelector: kAudioHardwarePropertyProcessObjectList,
  mScope: kAudioObjectPropertyScopeGlobal,
  mElement: kAudioObjectPropertyElementMain)

var size: UInt32 = 0
guard AudioObjectGetPropertyDataSize(system, &address, 0, nil, &size) == noErr else { exit(1) }
var processes = [AudioObjectID](repeating: 0, count: Int(size) / MemoryLayout<AudioObjectID>.size)
guard AudioObjectGetPropertyData(system, &address, 0, nil, &size, &processes) == noErr else { exit(1) }

address.mSelector = kAudioProcessPropertyIsRunningInput
for process in processes {
  var running: UInt32 = 0
  var runningSize = UInt32(MemoryLayout<UInt32>.size)
  if AudioObjectGetPropertyData(process, &address, 0, nil, &runningSize, &running) == noErr, running != 0 {
    exit(0)
  }
}
exit(1)
