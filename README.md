# iphone-usb-proxy v2 (全通信横流し)
1. pushするとActionsで usbproxy-windows_v2(exe+tun2socks+wintun) と USBProxy_v2.ipa ができる
2. ipaをSideloadly/AltStoreでiPhoneに入れて起動
3. PCにiTunes(or Apple Devices)を入れてUSB接続
4. usbproxy-windows_v2 フォルダごと展開して usbproxy.exe を実行(管理者)
   - 全通信がiPhone経由になる。Ctrl+Cで元に戻る
   - SOCKS5だけ欲しいときは --socks-only
- UDP(QUIC/ゲーム等)は通らない。DNSだけTCPに変換して通してる
