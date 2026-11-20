import Foundation
import Network

final class Socks5Server {
    static let shared = Socks5Server()
    var listener: NWListener?
    let q = DispatchQueue(label: "socks", attributes: .concurrent)

    func start() {
        guard let l = try? NWListener(using: .tcp, on: 9000) else { return }
        l.newConnectionHandler = { c in Session(c, self.q).start() }
        l.start(queue: q)
        listener = l
    }
}

final class Session {
    let c: NWConnection
    var r: NWConnection?
    let q: DispatchQueue
    var closed = false
    init(_ c: NWConnection, _ q: DispatchQueue) { self.c = c; self.q = q }

    func start() {
        c.start(queue: q)
        // greeting
        c.receive(minimumIncompleteLength: 2, maximumLength: 512) { d, _, _, e in
            guard let d = d, d.count >= 2, d[0] == 5 else { return self.close() }
            self.c.send(content: Data([5, 0]), completion: .contentProcessed { _ in self.readRequest() })
        }
    }

    func readRequest() {
        c.receive(minimumIncompleteLength: 7, maximumLength: 1024) { d, _, _, e in
            guard let d = d, d.count >= 7, d[0] == 5, d[1] == 1 else { return self.close() }
            var host = ""
            var idx = 4
            switch d[3] {
            case 1:
                guard d.count >= 10 else { return self.close() }
                host = (4..<8).map { String(d[$0]) }.joined(separator: ".")
                idx = 8
            case 3:
                let n = Int(d[4])
                guard d.count >= 5 + n + 2 else { return self.close() }
                host = String(decoding: d[5..<(5 + n)], as: UTF8.self)
                idx = 5 + n
            case 4:
                guard d.count >= 22 else { return self.close() }
                var parts: [String] = []
                for i in stride(from: 4, to: 20, by: 2) {
                    parts.append(String(format: "%02x%02x", d[i], d[i + 1]))
                }
                host = parts.joined(separator: ":")
                idx = 20
            default:
                return self.close()
            }
            let port = UInt16(d[idx]) << 8 | UInt16(d[idx + 1])
            let rest = d.count > idx + 2 ? d.subdata(in: (idx + 2)..<d.count) : Data()
            self.connect(host, port, rest)
        }
    }

    func connect(_ host: String, _ port: UInt16, _ rest: Data) {
        let rc = NWConnection(host: NWEndpoint.Host(host), port: NWEndpoint.Port(rawValue: port)!, using: .tcp)
        r = rc
        rc.stateUpdateHandler = { st in
            switch st {
            case .ready:
                rc.stateUpdateHandler = nil
                let ok = Data([5, 0, 0, 1, 0, 0, 0, 0, 0, 0])
                self.c.send(content: ok, completion: .contentProcessed { _ in
                    if !rest.isEmpty { rc.send(content: rest, completion: .contentProcessed { _ in }) }
                    self.pipe(self.c, rc)
                    self.pipe(rc, self.c)
                })
            case .failed, .cancelled:
                if !self.closed {
                    self.c.send(content: Data([5, 5, 0, 1, 0, 0, 0, 0, 0, 0]), completion: .contentProcessed { _ in self.close() })
                }
            default: break
            }
        }
        rc.start(queue: q)
    }

    func pipe(_ a: NWConnection, _ b: NWConnection) {
        a.receive(minimumIncompleteLength: 1, maximumLength: 65536) { d, _, done, e in
            if let d = d, !d.isEmpty {
                b.send(content: d, completion: .contentProcessed { err in
                    if err != nil || done { self.close() } else { self.pipe(a, b) }
                })
            } else if done || e != nil {
                self.close()
            } else {
                self.pipe(a, b)
            }
        }
    }

    func close() {
        if closed { return }
        closed = true
        c.cancel(); r?.cancel()
    }
}
