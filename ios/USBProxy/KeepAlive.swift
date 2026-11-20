import AVFoundation

// 無音を流してバックグラウンドで生きたままにする
final class KeepAlive {
    static let shared = KeepAlive()
    let engine = AVAudioEngine()
    let player = AVAudioPlayerNode()
    func start() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, options: [.mixWithOthers])
            try AVAudioSession.sharedInstance().setActive(true)
            let fmt = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 1)!
            engine.attach(player)
            engine.connect(player, to: engine.mainMixerNode, format: fmt)
            let buf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: 44100)!
            buf.frameLength = 44100
            try engine.start()
            player.scheduleBuffer(buf, at: nil, options: .loops)
            player.play()
        } catch { print("keepalive err", error) }
    }
}
