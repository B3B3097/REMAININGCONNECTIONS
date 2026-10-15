function FindProxyForURL(url, host) {
    // Proxy list
    var proxies = [
        "PROXY 47.94.205.252:8080",
    ];
    
    // Round-robin selection
    var proxy = proxies[Math.floor(Math.random() * proxies.length)];
    return proxy + "; DIRECT";
}
