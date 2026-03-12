def register(server):
    @server.resource("profile://service")
    def service_profile() -> str:
        return "mcp_server_a profile"
