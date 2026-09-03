from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from src.config import configure

body = (
    """
        <html>
            <body>
                <h2>Welcome to Knowra </h2>

                <p>
                    Your Knowra account has been successfully created.
                </p>

                <p>
                    We're excited to have you with us.
                </p>

                <p>
                    You can now start building your business knowledge
                    base and use Knowra AI to work with it.
                </p>

                <br>

                <p>
                    — Team Knowra
                </p>
            </body>
        </html>
        """,
)

mail_config = ConnectionConfig(
    MAIL_USERNAME=configure.MAIL_USERNAME,
    MAIL_PASSWORD=configure.MAIL_PASSWORD,
    MAIL_FROM=configure.MAIL_FROM,
    MAIL_PORT=configure.MAIL_PORT,
    MAIL_SERVER=configure.MAIL_SERVER,
    MAIL_FROM_NAME=configure.MAIL_FROM_NAME,
    MAIL_STARTTLS=configure.MAIL_STARTTLS,
    MAIL_SSL_TLS=configure.MAIL_SSL_TLS,
    USE_CREDENTIALS=configure.USE_CREDENTIALS,
    VALIDATE_CERTS=configure.VALIDATE_CERTS,
)

send_mail = FastMail(mail_config)


def create_message(recipents: list[str], subject: str, body: str):
    message = MessageSchema(
        recipients=recipents, subject=subject, body=body, subtype=MessageType.html
    )
    return message
