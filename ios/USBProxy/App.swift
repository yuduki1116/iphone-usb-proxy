import SwiftUI

@main
struct USBProxyApp: App {
    init() {
        KeepAlive.shared.start()
        Socks5Server.shared.start()
    }
    var body: some Scene {
        WindowGroup {
            VStack(spacing: 12) {
                Text("USBProxy").font(.largeTitle).bold()
                Text("SOCKS5 待ち受け中 :9000")
                Text("PC側のusbproxy.exeを起動してね").font(.footnote).foregroundColor(.secondary)
            }
        }
    }
}
