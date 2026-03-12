def register(server):
    @server.tool(name="add")
    def add(a: int, b: int) -> int:
        return a + b
