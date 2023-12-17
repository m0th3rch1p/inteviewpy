import asyncio
import aio_msgpack_rpc

class NewMailService:
    def on_new_mail(self, mail_title : str, mail_body : str) -> None:
        print(f"I have been notified of: {mail_title}")
        print(mail_body)
        print("")

async def main():
    try:
        server = await asyncio.start_server(aio_msgpack_rpc.Server(NewMailService()), host="localhost", port=18000)

        print("listening for notifications")
        while True:
            await asyncio.sleep(0.1)
    finally:
        server.close()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass