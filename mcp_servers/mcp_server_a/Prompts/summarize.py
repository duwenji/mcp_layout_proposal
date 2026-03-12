def register(server):
    @server.prompt(name="simple_summary")
    def simple_summary(topic: str) -> str:
        return f"{topic} を3行で要約してください。"
