function FindProxyForURL(url, host) {
    // Proxy list
    var proxies = [
        "PROXY 5.104.174.199:23500",
        "PROXY 1.0.171.213:8080",
    ];
    
    // Round-robin selection
    var proxy = proxies[Math.floor(Math.random() * proxies.length)];
    return proxy + "; DIRECT";
}
