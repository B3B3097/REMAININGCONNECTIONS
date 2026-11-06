function FindProxyForURL(url, host) {
    // Proxy list
    var proxies = [
        "PROXY 1.1.189.58:8080",
    ];
    
    // Round-robin selection
    var proxy = proxies[Math.floor(Math.random() * proxies.length)];
    return proxy + "; DIRECT";
}
