import time
import logging
import oreiades
from adapters import EmailAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

email_adapter = EmailAdapter.GmailEmailAdapter()

def process_one(conn):
    msg = oreiades.get_next_queued_message(conn)
    if not msg:
        return False

    logging.info(f"Processing message id={msg['id']} to={msg['to_address']}")

    try:
        # Render template placeholder
        subject = f"Template: {msg['subject']}"
        data = msg['data']

        try:
            email_adapter.send_email(
                to_email=msg["to_address"],
                subject=subject,
                data=data,
                template_name=msg["template"],
            )
        except Exception as e:
            logging.error(f"Error sending email for message {msg['id']}: {e}")
            raise
        else:
            oreiades.mark_sent(conn, msg["id"])
            logging.info(f"Message {msg['id']} sent.")

    except Exception as e:
        logging.exception(f"Failed sending message {msg['id']}")
        attempts = oreiades.increment_attempts(conn, msg["id"], str(e))

        if oreiades.should_give_up(attempts):
            oreiades.mark_failed(conn, msg["id"], str(e))
            logging.warning(f"Message {msg['id']} marked failed.")

    return True


def main():
    with oreiades.get_connection() as conn:
        while True:
            worked = process_one(conn)
            if not worked:
                time.sleep(2)

if __name__ == "__main__":
    main()
